"""
Continuous Ground-Truth Validation

Samples production rows from Supabase `funding_discoveries`, runs each through
the verify-agent (`resolve_domain_agent`), and promotes confirmed (company,
domain) pairs into KNOWN_GOOD_DOMAINS in eval_pipeline.py. Replaces the manual
re-harvest cycle the handoff said to do every 2-3 weeks.

State file (`data/gt_validation_state.json`) tracks every (name, stored_domain)
pair we've already processed so reruns don't burn agent calls re-verifying
known-good entries. Result: cost amortizes to near-zero after the first ~30
production runs.

Verdict logic per row:
  agent_domain == stored_domain                 -> confirmed (promote)
  agent says not_found / low confidence         -> skip (no signal)
  agent_domain != stored_domain                 -> conflict (log, do not promote)

Usage:
    py scripts/gt_validation.py --sample 10 --days 14            # dry-run
    py scripts/gt_validation.py --sample 10 --days 14 --apply    # write to eval_pipeline.py
    py scripts/gt_validation.py --show                           # print state stats
    py scripts/gt_validation.py --reset-conflicts                # re-verify previous conflicts only

Cost: each agent call ~$0.02. Default --sample 10 = ~$0.20 per run.
Set --max-cost to hard-cap (default $0.50).
"""

import argparse
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

# Load workspace-root dotenv (primary key store) — same pattern as domain_resolver.
load_dotenv(_SCRIPT_DIR.parent / ".env")
load_dotenv(_SCRIPT_DIR.parent.parent / ".env", override=False)
load_dotenv(Path.home() / ".env", override=False)

from domain_resolver import resolve_domain_agent, normalize_domain  # noqa: E402

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL") or os.getenv("SUPABASE_URL")
if SUPABASE_URL and not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = None
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)
SUPABASE_TABLE = "funding_discoveries"

STATE_PATH = _SCRIPT_DIR.parent / "data" / "gt_validation_state.json"
EVAL_PATH = _SCRIPT_DIR / "eval_pipeline.py"

PROMOTE_BEGIN = "    # === AUTO-PROMOTED BY gt_validation.py BEGIN ==="
PROMOTE_END = "    # === AUTO-PROMOTED BY gt_validation.py END ==="

AGENT_COST_PER_CALL = 0.02  # gpt-4o-mini agent + Serper, rough


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"validated": {}}
    return {"validated": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_PATH)


def state_key(company_name: str, stored_domain: str) -> str:
    return f"{company_name.strip().lower()}|{normalize_domain(stored_domain)}"


# ---------------------------------------------------------------------------
# Supabase fetch
# ---------------------------------------------------------------------------

def fetch_recent_rows(days: int) -> list[dict]:
    if not (SUPABASE_URL and SUPABASE_KEY):
        print("ERROR: SUPABASE_URL / SUPABASE_KEY not set — cannot fetch")
        return []
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    url = (
        f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
        f"?select=id,company_name,company_domain,source_url,discovered_date"
        f"&discovered_date=gte.{cutoff}"
        f"&company_domain=not.is.null"
    )
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"ERROR: Supabase fetch {resp.status_code}: {resp.text[:200]}")
            return []
        return resp.json()
    except Exception as e:
        print(f"ERROR: Supabase fetch exception: {e}")
        return []


# ---------------------------------------------------------------------------
# eval_pipeline.py KNOWN_GOOD_DOMAINS surface
# ---------------------------------------------------------------------------

_ENTRY_RE = re.compile(r'\{"company":\s*"([^"]+)",\s*"domain":\s*"([^"]+)"\}')


def existing_known_good_pairs() -> set[tuple[str, str]]:
    """Parse current KNOWN_GOOD_DOMAINS pairs to avoid duplicate inserts."""
    text = EVAL_PATH.read_text(encoding="utf-8")
    pairs: set[tuple[str, str]] = set()
    in_block = False
    for line in text.splitlines():
        if line.startswith("KNOWN_GOOD_DOMAINS"):
            in_block = True
            continue
        if in_block and line.startswith("]"):
            break
        if in_block:
            m = _ENTRY_RE.search(line)
            if m:
                pairs.add((m.group(1).strip().lower(), normalize_domain(m.group(2))))
    return pairs


def insert_promotions(new_entries: list[dict]) -> int:
    """Insert promotions between marker lines. Returns count actually inserted."""
    if not new_entries:
        return 0
    text = EVAL_PATH.read_text(encoding="utf-8")
    if PROMOTE_BEGIN not in text or PROMOTE_END not in text:
        print(f"ERROR: promotion markers not found in {EVAL_PATH.name} — aborting")
        return 0

    existing = existing_known_good_pairs()

    pre, rest = text.split(PROMOTE_BEGIN, 1)
    middle, post = rest.split(PROMOTE_END, 1)

    existing_lines = [
        line for line in middle.splitlines()
        if line.strip() and line.strip().startswith("{")
    ]

    added_lines: list[str] = []
    added = 0
    for entry in new_entries:
        key = (entry["company"].strip().lower(), normalize_domain(entry["domain"]))
        if key in existing:
            continue
        added_lines.append(
            f'    {{"company": "{entry["company"]}", "domain": "{entry["domain"]}"}},'
        )
        existing.add(key)
        added += 1

    new_middle_lines = existing_lines + added_lines
    if new_middle_lines:
        new_middle = "\n" + "\n".join(new_middle_lines) + "\n"
    else:
        new_middle = "\n"
    new_text = pre + PROMOTE_BEGIN + new_middle + PROMOTE_END + post

    EVAL_PATH.write_text(new_text, encoding="utf-8")
    return added


# ---------------------------------------------------------------------------
# Validation loop
# ---------------------------------------------------------------------------

def validate_row(row: dict) -> dict:
    """Run agent on (company_name, source_url). Returns verdict dict."""
    company = (row.get("company_name") or "").strip()
    stored = normalize_domain(row.get("company_domain") or "")
    source_url = row.get("source_url") or ""

    if not company or not stored:
        return {"verdict": "skipped", "reason": "missing company or stored domain"}

    # source_domain hint from source_url so agent doesn't return article host.
    from urllib.parse import urlparse
    src_host = ""
    try:
        src_host = urlparse(source_url).hostname or ""
    except Exception:
        pass
    src_host = (src_host or "").replace("www.", "")

    result = resolve_domain_agent(company_name=company, source_domain=src_host)
    agent_domain = normalize_domain(result.get("domain") or "")
    confidence = result.get("confidence", "low")

    if not agent_domain or agent_domain in ("not_found", "not_stated"):
        return {
            "verdict": "skipped",
            "reason": "agent returned not_found",
            "agent_domain": "",
            "stored_domain": stored,
            "confidence": confidence,
        }

    if agent_domain == stored:
        return {
            "verdict": "confirmed" if confidence in ("high", "medium") else "skipped",
            "reason": f"agent matches stored ({confidence})",
            "agent_domain": agent_domain,
            "stored_domain": stored,
            "confidence": confidence,
        }

    return {
        "verdict": "conflict",
        "reason": f"agent={agent_domain} stored={stored} ({confidence})",
        "agent_domain": agent_domain,
        "stored_domain": stored,
        "confidence": confidence,
    }


def run(sample: int, days: int, max_cost: float, apply_promotions: bool, retry_conflicts: bool) -> None:
    state = load_state()
    state.setdefault("validated", {})

    rows = fetch_recent_rows(days=days)
    print(f"Fetched {len(rows)} rows from last {days} days")

    if retry_conflicts:
        retry_keys = {k for k, v in state["validated"].items() if v.get("verdict") == "conflict"}
        rows = [r for r in rows if state_key(r.get("company_name") or "", r.get("company_domain") or "") in retry_keys]
        print(f"Retry-conflicts mode: {len(rows)} prior conflicts to re-verify")
    else:
        # Skip rows already in KNOWN_GOOD (no point re-verifying known-good pairs)
        # AND rows already processed in our state file.
        known_good = existing_known_good_pairs()
        before = len(rows)
        rows = [
            r for r in rows
            if (
                ((r.get("company_name") or "").strip().lower(),
                 normalize_domain(r.get("company_domain") or "")) not in known_good
            )
            and (
                state_key(r.get("company_name") or "", r.get("company_domain") or "") not in state["validated"]
            )
        ]
        print(f"After dedup vs KNOWN_GOOD ({len(known_good)}) + state ({len(state['validated'])}): "
              f"{len(rows)}/{before} rows fresh")

    if not rows:
        print("Nothing to validate.")
        return

    random.shuffle(rows)
    rows = rows[:sample]
    print(f"Sampling {len(rows)} rows (max_cost=${max_cost})")

    spent = 0.0
    confirmed: list[dict] = []
    conflicts: list[dict] = []
    skipped: list[dict] = []

    for i, row in enumerate(rows, 1):
        if spent + AGENT_COST_PER_CALL > max_cost:
            print(f"  [{i}/{len(rows)}] BUDGET HIT (${spent:.2f} spent) — stopping")
            break
        company = row.get("company_name") or "(no name)"
        print(f"  [{i}/{len(rows)}] {company} (stored={normalize_domain(row.get('company_domain') or '')})")
        v = validate_row(row)
        spent += AGENT_COST_PER_CALL

        key = state_key(row.get("company_name") or "", row.get("company_domain") or "")
        state["validated"][key] = {
            **v,
            "row_id": row.get("id"),
            "ts": datetime.now(timezone.utc).isoformat(),
        }

        if v["verdict"] == "confirmed":
            confirmed.append({"company": company, "domain": v["stored_domain"]})
        elif v["verdict"] == "conflict":
            conflicts.append({"company": company, "agent": v["agent_domain"], "stored": v["stored_domain"]})
        else:
            skipped.append(company)
        print(f"      -> {v['verdict']}: {v.get('reason', '')}")

    save_state(state)
    print(f"\nSpent ~${spent:.2f}. State saved -> {STATE_PATH.name}")
    print(f"Confirmed: {len(confirmed)}  Conflicts: {len(conflicts)}  Skipped: {len(skipped)}")

    if conflicts:
        print("\nConflicts (manual review):")
        for c in conflicts:
            print(f"  {c['company']}: agent={c['agent']} vs stored={c['stored']}")

    if confirmed:
        print(f"\nWould promote {len(confirmed)} entries to KNOWN_GOOD_DOMAINS:")
        for c in confirmed:
            print(f"  + {{'company': {c['company']!r}, 'domain': {c['domain']!r}}}")
        if apply_promotions:
            added = insert_promotions(confirmed)
            print(f"\nWrote {added} new entries to {EVAL_PATH.name} (between PROMOTED markers)")
        else:
            print("\n(dry-run — pass --apply to write to eval_pipeline.py)")


def show_stats() -> None:
    state = load_state()
    by_verdict: dict[str, int] = {}
    for v in state.get("validated", {}).values():
        by_verdict[v.get("verdict", "unknown")] = by_verdict.get(v.get("verdict", "unknown"), 0) + 1
    print(f"State entries: {len(state.get('validated', {}))}")
    for k in sorted(by_verdict, key=lambda x: -by_verdict[x]):
        print(f"  {k:12s} {by_verdict[k]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=10, help="rows to verify per run")
    ap.add_argument("--days", type=int, default=14, help="how far back to sample from Supabase")
    ap.add_argument("--max-cost", type=float, default=0.50, help="hard cost cap in USD")
    ap.add_argument("--apply", action="store_true", help="write confirmed promotions to eval_pipeline.py")
    ap.add_argument("--show", action="store_true", help="print state stats and exit")
    ap.add_argument("--reset-conflicts", action="store_true", help="re-verify only prior conflicts")
    args = ap.parse_args()

    if args.show:
        show_stats()
        return

    run(
        sample=args.sample,
        days=args.days,
        max_cost=args.max_cost,
        apply_promotions=args.apply,
        retry_conflicts=args.reset_conflicts,
    )


if __name__ == "__main__":
    main()
