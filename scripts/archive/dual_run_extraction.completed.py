"""
Dual-run name extraction comparison.

Loads cached stage1 data, applies the Stage 2 funnel filter (noise/non-Series-A)
identically to both paths, then runs:
  A) Current regex extractor: extract_company_name_from_title(title)
  B) New GPT batch extractor: gpt-4o-mini on title + snippet

Writes diff report to output/extraction-diff-<date>.json with side-by-side results
so we can judge whether GPT actually beats regex before refactoring.

Usage:
    py scripts/dual_run_extraction.py --date 2026-04-26
    py scripts/dual_run_extraction.py --date 2026-04-26 --no-gpt   # regex only
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Workspace-root dotenv (same pattern as domain_resolver.py)
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[1]
for env_path in (WORKSPACE_ROOT / ".env", Path.home() / ".env", SCRIPT_DIR.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path)

sys.path.insert(0, str(SCRIPT_DIR))
from series_a_pipeline import (
    NOISE_PATTERNS,
    NON_SERIES_A,
    SERIES_A_PATTERN,
    SOFT_NON_A,
    extract_company_name_from_title,
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STAGE_DIR = SCRIPT_DIR.parent / "output" / "stages"
OUT_DIR = SCRIPT_DIR.parent / "output"


def survives_funnel(item: dict) -> tuple[bool, str]:
    """Apply the same Stage 2 funnel filter that wraps name extraction in production."""
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    combined = f"{title} {snippet}"

    if NOISE_PATTERNS.search(title):
        return False, "noise"
    title_has_a = bool(SERIES_A_PATTERN.search(title))
    title_has_hard = bool(NON_SERIES_A.search(title))
    title_has_soft = bool(SOFT_NON_A.search(title))
    has_a = bool(SERIES_A_PATTERN.search(combined))
    has_hard = bool(NON_SERIES_A.search(combined))

    if title_has_hard:
        return False, "title hard non-A"
    if title_has_soft and not title_has_a:
        return False, "soft non-A in title, no A"
    if has_hard and not has_a:
        return False, "hard non-A overall"
    if not has_a and not re.search(
        r"(?:raises?|raised|secures?|closes?)\s+[\$€£]", combined, re.IGNORECASE
    ):
        return False, "no series A and no funding amount"
    return True, ""


def gpt_batch_extract(items: list[dict]) -> list[dict]:
    """
    Single GPT call: given a batch of {idx, title, snippet}, return
    [{idx, company_name|null, is_funding_event}].

    Cost: ~$0.0005 per 30-item batch on gpt-4o-mini.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not loaded — workspace-root dotenv missing")

    payload_lines = []
    for it in items:
        # Snippets capped to keep token budget tight; 280 chars carries the company.
        snippet = (it.get("snippet") or "")[:280].replace("\n", " ").strip()
        title = (it.get("title") or "").replace("\n", " ").strip()
        payload_lines.append(f'[{it["idx"]}] TITLE: {title} | SNIPPET: {snippet}')

    user_msg = (
        "For each numbered news item, identify the COMPANY THAT RAISED FUNDING.\n"
        "The company is usually the subject of a verb like raises/secures/closes/announces/eyes/snags.\n"
        "Read both TITLE and SNIPPET — the snippet often names the company when the title is generic\n"
        '(e.g. title "TechCrunch Mobility: Elon\'s admission" but snippet starts "A&K Robotics raised $8M").\n'
        "NEVER return the investor / VC firm. NEVER return a publication name (TechCrunch, AI Market Watch).\n"
        "If the item is a roundup / column / multi-company piece with no single subject, return null.\n"
        "If it isn't a funding announcement at all, return null and is_funding=false.\n\n"
        "Return STRICT JSON: "
        '{"results":[{"idx":1,"company":"Auth0","is_funding":true},...]}\n\n'
        "Items:\n" + "\n".join(payload_lines)
    )

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o-mini",
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": 2000,
            "messages": [
                {"role": "system", "content": "You extract structured data. Output strict JSON."},
                {"role": "user", "content": user_msg},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    body = json.loads(resp.json()["choices"][0]["message"]["content"])
    return body.get("results", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD of cached stage1 file")
    ap.add_argument("--no-gpt", action="store_true", help="Skip GPT call (regex only)")
    args = ap.parse_args()

    src = STAGE_DIR / f"stage1-{args.date}.json"
    if not src.exists():
        sys.exit(f"Missing {src}")

    with open(src, "rb") as f:
        raw = json.loads(f.read().decode("utf-8"))

    print(f"Loaded {len(raw)} raw stage-1 items from {src.name}")

    survivors = []
    funnel_drops = []
    for i, item in enumerate(raw):
        ok, reason = survives_funnel(item)
        if ok:
            survivors.append({"idx": i, **item})
        else:
            funnel_drops.append({"idx": i, "title": item.get("title", "")[:80], "reason": reason})

    print(f"Funnel survivors: {len(survivors)}  (dropped {len(funnel_drops)})")

    # Path A: regex
    regex_results = []
    for s in survivors:
        name = extract_company_name_from_title(s["title"])
        regex_results.append({"idx": s["idx"], "company": name or None})

    # Path B: GPT batch
    gpt_results_by_idx: dict[int, dict] = {}
    if not args.no_gpt:
        print("Calling GPT batch extractor...")
        try:
            gpt_results = gpt_batch_extract(survivors)
            for r in gpt_results:
                gpt_results_by_idx[r["idx"]] = r
        except Exception as e:
            print(f"GPT error: {e}")

    # Build diff
    rows = []
    agree = disagree = regex_only = gpt_only = both_null = 0
    for s in survivors:
        rgx = next(r["company"] for r in regex_results if r["idx"] == s["idx"])
        gpt = gpt_results_by_idx.get(s["idx"], {}).get("company") if not args.no_gpt else None
        is_funding = gpt_results_by_idx.get(s["idx"], {}).get("is_funding") if not args.no_gpt else None

        rgx_norm = (rgx or "").strip().lower()
        gpt_norm = (gpt or "").strip().lower()

        if rgx and gpt:
            if rgx_norm == gpt_norm or rgx_norm in gpt_norm or gpt_norm in rgx_norm:
                agree += 1
                status = "AGREE"
            else:
                disagree += 1
                status = "DISAGREE"
        elif rgx and not gpt:
            regex_only += 1
            status = "REGEX_ONLY"
        elif gpt and not rgx:
            gpt_only += 1
            status = "GPT_ONLY"
        else:
            both_null += 1
            status = "BOTH_NULL"

        rows.append({
            "idx": s["idx"],
            "title": s.get("title", ""),
            "snippet": (s.get("snippet") or "")[:200],
            "regex": rgx,
            "gpt": gpt,
            "gpt_is_funding": is_funding,
            "status": status,
        })

    summary = {
        "total_raw": len(raw),
        "funnel_survivors": len(survivors),
        "funnel_dropped": len(funnel_drops),
        "agree": agree,
        "disagree": disagree,
        "regex_only_extracted": regex_only,
        "gpt_only_extracted": gpt_only,
        "both_null": both_null,
    }

    out_path = OUT_DIR / f"extraction-diff-{args.date}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows, "funnel_drops": funnel_drops}, f, indent=2, ensure_ascii=False)

    print(f"\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\nDiff report: {out_path}")
    print(f"\nDISAGREE / GPT_ONLY rows are the interesting ones — review those.")


if __name__ == "__main__":
    main()
