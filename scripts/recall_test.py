"""
Recall Test — Funding Discovery Pipeline
Measures whether the 8-query set surfaces companies previously confirmed via all round types.

Steps:
  1. Pull GT from Supabase (last 14 days, all round types)
  2. Run pipeline Stage 1 with --tbs qdr:w (weekly window)
  3. Match GT companies against Stage 1 results
  4. Write report to data/recall-test-YYYY-MM-DD.md

Usage:
    py scripts/recall_test.py
    py scripts/recall_test.py --skip-stage1   # use existing stage1 JSON
    py scripts/recall_test.py --gt-days 30    # expand GT window
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Env setup — mirrors pipeline_base.py path order
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent

load_dotenv(REPO_ROOT / ".env")
load_dotenv(WORKSPACE_ROOT / ".env", override=False)
load_dotenv(Path.home() / ".env", override=False)

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL") or os.getenv("SUPABASE_URL")
if SUPABASE_URL and not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = None
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

STAGE_DIR = REPO_ROOT / "output" / "stages"
DATA_DIR = REPO_ROOT / "data"
TODAY = datetime.utcnow().strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUFFIX_RE = re.compile(
    r"\s*[,.]?\s*\b(Inc|Ltd|Corp|LLC|GmbH|Co|PLC|SA|AG|BV|Pty|SAS|SRL)\b\.?\s*$",
    re.IGNORECASE,
)


def normalize_name(name: str) -> str:
    """Strip legal suffixes, lowercase, strip whitespace."""
    name = _SUFFIX_RE.sub("", name.strip())
    name = re.sub(r"[\s,.\-:;]+$", "", name)
    return name.lower().strip()


def normalize_domain(domain: str) -> str:
    """Strip www. prefix, lowercase."""
    if not domain:
        return ""
    d = domain.lower().strip().removeprefix("https://").removeprefix("http://")
    d = d.split("/")[0]
    d = d.removeprefix("www.")
    return d


# ---------------------------------------------------------------------------
# Step 1: Ground truth from Supabase
# ---------------------------------------------------------------------------

def fetch_ground_truth(days: int = 14) -> list[dict]:
    """Pull last N days of confirmed funding discoveries (all round types) from Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  [WARN] Supabase env vars not set — will use synthetic GT fallback")
        return []

    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    url = (
        f"{SUPABASE_URL}/rest/v1/funding_discoveries"
        f"?select=company_name,company_domain,discovered_date,source_url,round_type"
        f"&discovered_date=gte.{cutoff}"
        f"&order=discovered_date.desc"
        f"&limit=500"
    )
    try:
        resp = requests.get(
            url,
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
        rows = resp.json()
        if isinstance(rows, list):
            print(f"  Supabase returned {len(rows)} GT rows (last {days} days)")
            return rows
        print(f"  [WARN] Unexpected Supabase response: {str(rows)[:200]}")
        return []
    except Exception as e:
        print(f"  [WARN] Supabase fetch failed: {e}")
        return []


def synthetic_gt_fallback() -> list[dict]:
    """
    Fallback: query Serper for recent Series A from Crunchbase as synthetic GT.
    Returns up to 10 results as GT companies.
    """
    if not SERPER_API_KEY:
        print("  [ERROR] No SERPER_API_KEY — cannot build synthetic GT")
        return []

    print("  Building synthetic GT via Serper (site:crunchbase.com funding 2026)...")
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            json={"q": 'site:crunchbase.com "raises" "funding" 2026', "num": 10},
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json().get("organic", [])
        gt = []
        for r in results:
            title = r.get("title", "")
            # Crunchbase titles look like "CompanyName - Crunchbase" or "CompanyName funding..."
            company = title.split(" - ")[0].strip() if " - " in title else title.split("|")[0].strip()
            gt.append({
                "company_name": company,
                "company_domain": "",
                "discovered_date": TODAY,
                "source_url": r.get("link", ""),
            })
        print(f"  Synthetic GT: {len(gt)} companies from Crunchbase Serper results")
        return gt
    except Exception as e:
        print(f"  [ERROR] Synthetic GT fallback failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Step 2: Run Stage 1
# ---------------------------------------------------------------------------

def run_stage1(tbs: str = "qdr:w") -> Path | None:
    """Run pipeline stage 1 and return path to output JSON."""
    print(f"\n[Stage 1] Running pipeline stage 1 (tbs={tbs})...")
    cmd = [
        sys.executable, str(SCRIPT_DIR / "series_a_pipeline.py"),
        "--stage", "1",
        "--tbs", tbs,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRIPT_DIR),
            capture_output=False,  # let output stream live
            timeout=600,
        )
        if result.returncode != 0:
            print(f"  [WARN] Pipeline exited with code {result.returncode}")
    except subprocess.TimeoutExpired:
        print("  [WARN] Stage 1 timed out after 10 minutes — proceeding with existing output")
    except Exception as e:
        print(f"  [WARN] Stage 1 subprocess error: {e}")

    # Find the most recent stage1 JSON
    stage1_files = sorted(STAGE_DIR.glob("stage1-*.json"), reverse=True)
    if not stage1_files:
        print("  [ERROR] No stage1 JSON found in output/stages/")
        return None
    latest = stage1_files[0]
    print(f"  Stage 1 output: {latest}")
    return latest


def load_stage1(path: Path) -> list[dict]:
    """Load stage1 JSON and return flat list of result dicts."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Stage1 JSON structure: {"results": [...], "query_results": {...}}
    # or just a list, or {"raw_results": [...]}
    if isinstance(data, list):
        return data
    if "results" in data:
        return data["results"]
    if "raw_results" in data:
        return data["raw_results"]
    # Flatten from per-query structure
    flat = []
    for key, val in data.items():
        if isinstance(val, list):
            flat.extend(val)
        elif isinstance(val, dict) and "results" in val:
            flat.extend(val["results"])
    return flat


# ---------------------------------------------------------------------------
# Step 3: Recall matching
# ---------------------------------------------------------------------------

def match_gt_against_stage1(gt_companies: list[dict], stage1_results: list[dict]) -> dict:
    """
    For each GT company, check if stage1 surfaces it.
    Match by: normalized name substring in title/snippet, OR domain match.
    Returns stats + per-GT found/missed info.
    """
    found = []
    missed = []

    for gt in gt_companies:
        gt_name = gt.get("company_name", "").strip()
        gt_domain = normalize_domain(gt.get("company_domain", ""))
        gt_norm = normalize_name(gt_name)

        if not gt_norm and not gt_domain:
            continue

        matched_by = None
        matched_result = None
        matched_query = None

        for r in stage1_results:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            result_url = r.get("link", r.get("source_url", ""))
            query_source = r.get("query_source", r.get("query_id", ""))
            combined = f"{title} {snippet}".lower()

            # Name match: GT company name appears in title or snippet
            name_hit = gt_norm and gt_norm in combined

            # Domain match: GT domain appears in result URL or snippet
            domain_hit = False
            if gt_domain:
                domain_hit = gt_domain in combined or gt_domain in result_url.lower()

            if name_hit or domain_hit:
                matched_by = "name" if name_hit else "domain"
                matched_result = f"{title[:80]}"
                matched_query = query_source
                break

        if matched_result:
            found.append({
                "company_name": gt_name,
                "company_domain": gt.get("company_domain", ""),
                "discovered_date": gt.get("discovered_date", ""),
                "matched_by": matched_by,
                "matched_title": matched_result,
                "query_source": matched_query,
            })
        else:
            missed.append({
                "company_name": gt_name,
                "company_domain": gt.get("company_domain", ""),
                "discovered_date": gt.get("discovered_date", ""),
                "source_url": gt.get("source_url", ""),
            })

    return {"found": found, "missed": missed}


def per_query_attribution(found: list[dict]) -> dict[str, list[str]]:
    """Map query_source -> list of uniquely-attributed companies."""
    # A company is uniquely attributed to the first query that found it
    attribution: dict[str, list[str]] = {}
    for f in found:
        q = f.get("query_source") or "unknown"
        attribution.setdefault(q, []).append(f["company_name"])
    return attribution


# ---------------------------------------------------------------------------
# Step 4: Write report
# ---------------------------------------------------------------------------

def write_report(
    gt_companies: list[dict],
    found: list[dict],
    missed: list[dict],
    stage1_path: Path | None,
    gt_days: int,
    gt_source: str,
) -> Path:
    total = len(gt_companies)
    n_found = len(found)
    n_missed = len(missed)
    recall_pct = (n_found / total * 100) if total > 0 else 0.0

    if recall_pct >= 80:
        verdict = "PASS"
        verdict_note = f"Recall {recall_pct:.0f}% meets the 80% threshold."
    elif recall_pct >= 60:
        verdict = "WARN"
        verdict_note = f"Recall {recall_pct:.0f}% is below 80% but above 60%. Investigate missed companies."
    else:
        verdict = "FAIL"
        verdict_note = f"Recall {recall_pct:.0f}% is below 60%. New query set is missing significant coverage."

    attribution = per_query_attribution(found)

    lines = [
        f"# Recall Test — {TODAY}",
        "",
        f"> GT source: {gt_source} (last {gt_days} days)  ",
        f"> Stage 1 file: `{stage1_path.name if stage1_path else 'N/A'}`",
        "",
        "## Summary",
        f"- GT companies (last {gt_days} days): {total}",
        f"- Found by new query set: {n_found}",
        f"- **Recall rate: {recall_pct:.1f}%**",
        f"- Missed: {n_missed} companies",
        "",
    ]

    # Missed companies table
    lines += ["## Missed Companies", ""]
    if missed:
        lines += [
            "| Company | Domain | Discovered | Source URL |",
            "|---------|--------|------------|------------|",
        ]
        for m in missed:
            lines.append(
                f"| {m['company_name']} | {m['company_domain'] or '-'} | "
                f"{m['discovered_date'] or '-'} | {m['source_url'] or '-'} |"
            )
    else:
        lines.append("_None — all GT companies found._")

    lines += ["", "## Per-Query Hit Attribution", ""]
    if attribution:
        lines += [
            "| Query | Companies Found |",
            "|-------|----------------|",
        ]
        for q, companies in sorted(attribution.items()):
            companies_str = ", ".join(companies[:10])
            if len(companies) > 10:
                companies_str += f" (+{len(companies) - 10} more)"
            lines.append(f"| {q} | {companies_str} |")
    else:
        lines.append("_No matches — 0% recall._")

    lines += [
        "",
        "## Found Companies (detail)",
        "",
    ]
    if found:
        lines += [
            "| Company | Match Type | Query | Matched Title |",
            "|---------|-----------|-------|---------------|",
        ]
        for f in found:
            lines.append(
                f"| {f['company_name']} | {f['matched_by']} | {f['query_source'] or '-'} | "
                f"{f['matched_title'][:60]}... |"
            )
    else:
        lines.append("_None found._")

    lines += [
        "",
        "## Verdict",
        "",
        f"**{verdict}** — {verdict_note}",
        "",
    ]

    if missed and verdict != "PASS":
        lines += [
            "### Action Items",
            "",
        ]
        for m in missed[:5]:
            lines.append(f"- Investigate why `{m['company_name']}` was missed. Source: {m['source_url'] or 'N/A'}")
        if len(missed) > 5:
            lines.append(f"- ... and {len(missed) - 5} more.")

    report_text = "\n".join(lines) + "\n"

    report_path = DATA_DIR / f"recall-test-{TODAY}.md"
    DATA_DIR.mkdir(exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Series A recall test")
    parser.add_argument("--skip-stage1", action="store_true", help="Use existing stage1 JSON, skip running pipeline")
    parser.add_argument("--gt-days", type=int, default=14, help="GT lookback window in days")
    parser.add_argument("--tbs", default="qdr:w", help="Serper tbs parameter for stage 1")
    args = parser.parse_args()

    print("=" * 60)
    print("Funding Discovery Recall Test")
    print(f"Date: {TODAY}")
    print("=" * 60)

    # Step 1: Ground truth
    print(f"\n[Step 1] Fetching ground truth (last {args.gt_days} days)...")
    gt_companies = fetch_ground_truth(days=args.gt_days)
    gt_source = "Supabase funding_discoveries"

    if not gt_companies:
        print("  Supabase returned 0 rows — using synthetic GT fallback (Serper/Crunchbase)")
        gt_companies = synthetic_gt_fallback()
        gt_source = "Synthetic (Serper/Crunchbase fallback)"

    if not gt_companies:
        print("[ERROR] No GT companies available. Cannot run recall test.")
        sys.exit(1)

    print(f"\n  GT set: {len(gt_companies)} companies")
    for g in gt_companies[:5]:
        print(f"    - {g['company_name']} ({g.get('company_domain', 'no domain')})")
    if len(gt_companies) > 5:
        print(f"    ... and {len(gt_companies) - 5} more")

    # Step 2: Stage 1
    if args.skip_stage1:
        stage1_files = sorted(STAGE_DIR.glob("stage1-*.json"), reverse=True)
        stage1_path = stage1_files[0] if stage1_files else None
        if stage1_path:
            print(f"\n[Step 2] Using existing stage1 output: {stage1_path}")
        else:
            print("[ERROR] --skip-stage1 specified but no stage1 JSON found")
            sys.exit(1)
    else:
        stage1_path = run_stage1(tbs=args.tbs)

    if not stage1_path:
        print("[ERROR] No stage1 output available")
        sys.exit(1)

    stage1_results = load_stage1(stage1_path)
    print(f"\n  Stage 1 loaded: {len(stage1_results)} results")

    # Step 3: Match
    print(f"\n[Step 3] Matching {len(gt_companies)} GT companies against {len(stage1_results)} stage1 results...")
    match_result = match_gt_against_stage1(gt_companies, stage1_results)
    found = match_result["found"]
    missed = match_result["missed"]

    total = len(gt_companies)
    recall_pct = len(found) / total * 100 if total > 0 else 0
    print(f"\n  Found: {len(found)}/{total} ({recall_pct:.1f}%)")
    print(f"  Missed: {len(missed)}")

    if missed:
        print("\n  Missed companies:")
        for m in missed:
            print(f"    - {m['company_name']} ({m.get('company_domain', '-')})")

    # Step 4: Report
    print(f"\n[Step 4] Writing report...")
    report_path = write_report(
        gt_companies=gt_companies,
        found=found,
        missed=missed,
        stage1_path=stage1_path,
        gt_days=args.gt_days,
        gt_source=gt_source,
    )

    recall_label = "PASS" if recall_pct >= 80 else ("WARN" if recall_pct >= 60 else "FAIL")
    print(f"\n{'='*60}")
    print(f"RECALL: {len(found)}/{total} = {recall_pct:.1f}% — {recall_label}")
    print(f"Report: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
