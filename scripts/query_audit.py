"""
Query Audit Script — Series A Pipeline
Tests all 10 current queries against /search and /news endpoints.
Writes report to data/query-audit-2026-04-29.md
"""

import os
import re
import sys
import time
import json
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Load API key from .env (try repo root first, then workspace root)
# ---------------------------------------------------------------------------

def load_env(path: str):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent

load_env(str(REPO_ROOT / ".env"))
load_env(str(WORKSPACE_ROOT / ".env"))

SERPER_KEY = os.environ.get("SERPER_API_KEY") or os.environ.get("SERPER_KEY", "")
if not SERPER_KEY:
    print("ERROR: SERPER_API_KEY not found in .env files. Checked:")
    print(f"  {REPO_ROOT / '.env'}")
    print(f"  {WORKSPACE_ROOT / '.env'}")
    sys.exit(1)

print(f"[OK] Serper key loaded (first 6 chars: {SERPER_KEY[:6]}...)")

# ---------------------------------------------------------------------------
# Filter patterns (from series_a_pipeline.py)
# ---------------------------------------------------------------------------

NON_SERIES_A = re.compile(
    r'\b(Series\s+[B-Z]|Pre-Seed|pre-seed|Pre-IPO|IPO|Debt|Grant|'
    r'acquisition|acquires|acquired|merger|SPAC|refinanc)',
    re.IGNORECASE
)
SERIES_A_PATTERN = re.compile(r'\bSeries\s+A\b', re.IGNORECASE)
NOISE_PATTERNS = re.compile(
    r'(?:Series A activity|weekly recap|funding recap|venture market|job search|'
    r'quarterly.*dividend|financial results|earnings|stock|preferred stock|'
    r'broadband|announces common|\bTag\b\s*[-|]|\bTag\s*$)',
    re.IGNORECASE
)
AMOUNT_PATTERN = re.compile(
    r'[\$€£¥]\s*[\d,.]+\s*[MBmb](?:illion)?|\d+\s*(?:million|billion)',
    re.IGNORECASE
)

def passes_filter(title: str, snippet: str) -> tuple[bool, str]:
    """Returns (passes, reject_reason)."""
    combined = f"{title} {snippet}"
    if NOISE_PATTERNS.search(title):
        return False, "noise pattern in title"
    if NON_SERIES_A.search(title):
        return False, "non-Series A in title"
    has_series_a = bool(SERIES_A_PATTERN.search(combined))
    has_non_a = bool(NON_SERIES_A.search(combined))
    if has_non_a and not has_series_a:
        return False, "non-Series A round, no Series A mention"
    has_amount = bool(AMOUNT_PATTERN.search(combined))
    if not has_series_a and not has_amount:
        return False, "no Series A mention and no funding amount"
    return True, ""

# ---------------------------------------------------------------------------
# Query definitions
# ---------------------------------------------------------------------------

AGENT_A_QUERIES = [
    {"id": "q3",  "query": "site:thesaasnews.com Series A",                         "num": 30, "desc": "TheSaaSNews"},
    {"id": "q4",  "query": "site:finsmes.com Series A",                             "num": 30, "desc": "FinSMEs"},
    {"id": "q5",  "query": "site:alleywatch.com funding report",                    "num": 10, "desc": "AlleyWatch"},
    {"id": "q9",  "query": "site:vcnewsdaily.com Series A",                         "num": 10, "desc": "VCNewsDaily"},
    {"id": "q10", "query": "site:infotechlead.com venture capital funding",         "num": 10, "desc": "InfotechLead"},
]

AGENT_B_QUERIES = [
    {"id": "q1",  "query": '"Series A" raises OR raised OR funding OR round million', "num": 30, "desc": "broad sweep"},
    {"id": "q2",  "query": '"Series A" announces OR secures OR closes OR completes funding', "num": 20, "desc": "announcement language"},
    {"id": "q6",  "query": '"Series A" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com', "num": 10, "desc": "press wires"},
    {"id": "q7",  "query": '"led the round" OR "led the Series A" OR "led a" Series A investment startup', "num": 20, "desc": "VC language"},
    {"id": "q8",  "query": '"Series A" startup funding site:eu-startups.com OR site:tech.eu OR site:techround.co.uk', "num": 10, "desc": "European"},
]

ALL_QUERIES = AGENT_A_QUERIES + AGENT_B_QUERIES

# ---------------------------------------------------------------------------
# Serper call
# ---------------------------------------------------------------------------

def serper_search(query: str, endpoint: str = "search", tbs: str = "qdr:d", num: int = 10) -> list[dict]:
    """Fire a Serper query. endpoint = 'search' or 'news'."""
    url = f"https://google.serper.dev/{endpoint}"
    try:
        resp = requests.post(
            url,
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num, "tbs": tbs},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if endpoint == "news":
            return data.get("news", [])
        else:
            return data.get("organic", [])
    except Exception as e:
        print(f"  ERROR calling Serper ({endpoint}): {e}")
        return []

# ---------------------------------------------------------------------------
# Audit a single query
# ---------------------------------------------------------------------------

def audit_query(q: dict, endpoint: str = "search") -> dict:
    results = serper_search(q["query"], endpoint=endpoint, tbs="qdr:d", num=10)
    total = len(results)

    passing = []
    failing = []
    for r in results:
        title = r.get("title", "")
        snippet = r.get("snippet", "") or r.get("body", "")
        ok, reason = passes_filter(title, snippet)
        if ok:
            passing.append({"title": title, "url": r.get("link", r.get("url", ""))})
        else:
            failing.append({"title": title, "reason": reason})

    signal_rate = len(passing) / total if total > 0 else 0.0

    # Sample 3 titles from passing results
    sample_titles = [p["title"][:90] for p in passing[:3]]
    # Sample 2 noise titles
    noise_sample = [f["title"][:70] + f" [{f['reason']}]" for f in failing[:2]]

    return {
        "id": q["id"],
        "desc": q["desc"],
        "query": q["query"],
        "endpoint": endpoint,
        "total": total,
        "passing": len(passing),
        "signal_rate": signal_rate,
        "sample_passing": sample_titles,
        "sample_noise": noise_sample,
    }

# ---------------------------------------------------------------------------
# Status classification
# ---------------------------------------------------------------------------

def classify_status(result: dict) -> str:
    r = result["signal_rate"]
    t = result["total"]
    if t == 0:
        return "DEAD"
    if r < 0.30:
        return "DEAD"
    if r < 0.60:
        return "DEGRADED"
    return "HEALTHY"

# ---------------------------------------------------------------------------
# Main audit loop
# ---------------------------------------------------------------------------

print("\n=== Phase 1: Testing current queries ===\n")

search_results = {}
news_results = {}

for q in ALL_QUERIES:
    print(f"[/search] {q['id']} — {q['desc']}")
    r = audit_query(q, endpoint="search")
    search_results[q["id"]] = r
    print(f"  total={r['total']} passing={r['passing']} signal={r['signal_rate']:.0%}")
    if r["sample_passing"]:
        for t in r["sample_passing"][:2]:
            print(f"    + {t[:80]}".encode("ascii", "replace").decode())
    if r["sample_noise"]:
        for t in r["sample_noise"][:1]:
            print(f"    - {t[:80]}".encode("ascii", "replace").decode())
    time.sleep(1.2)  # rate limit

    print(f"[/news]   {q['id']} — {q['desc']}")
    r2 = audit_query(q, endpoint="news")
    news_results[q["id"]] = r2
    print(f"  total={r2['total']} passing={r2['passing']} signal={r2['signal_rate']:.0%}")
    time.sleep(1.2)

print("\n=== Phase 2: Assessing query health ===\n")

for q in ALL_QUERIES:
    s = classify_status(search_results[q["id"]])
    n = classify_status(news_results[q["id"]])
    print(f"  {q['id']} ({q['desc']}): /search={s}  /news={n}")

# ---------------------------------------------------------------------------
# Phase 3: Test proposed replacement queries
# ---------------------------------------------------------------------------

print("\n=== Phase 3: Testing replacement candidate queries ===\n")

REPLACEMENT_CANDIDATES = [
    {"id": "rA1", "query": 'site:techcrunch.com "Series A"',                                    "num": 10, "desc": "TechCrunch Series A"},
    {"id": "rA2", "query": 'site:thesaasnews.com "Series A" 2026',                              "num": 10, "desc": "TheSaaSNews + year anchor"},
    {"id": "rA3", "query": 'site:finsmes.com "Series A" 2026',                                  "num": 10, "desc": "FinSMEs + year anchor"},
    {"id": "rA4", "query": 'site:eu-startups.com OR site:tech.eu "Series A" 2026',              "num": 10, "desc": "EU sources + year anchor"},
    {"id": "rB1", "query": '"Series A" raises OR raised OR funding 2026 million startup',        "num": 10, "desc": "broad sweep + 2026 year anchor"},
    {"id": "rB2", "query": '"Series B" raises OR raised OR funding OR round million',            "num": 10, "desc": "Series B broad sweep"},
    {"id": "rB3", "query": '"led the round" "Series A" 2026',                                   "num": 10, "desc": "VC language + year anchor"},
    {"id": "rB4", "query": '"Series A" site:businesswire.com OR site:prnewswire.com 2026',      "num": 10, "desc": "press wires + year anchor"},
    {"id": "rB5", "query": '"Series A" announces OR secures OR closes funding startup 2026',     "num": 10, "desc": "announcement + 2026"},
    {"id": "rB6", "query": '"Series B" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com', "num": 10, "desc": "Series B press wires"},
]

replacement_results = {}
for q in REPLACEMENT_CANDIDATES:
    print(f"[/search] {q['id']} — {q['desc']}")
    r = audit_query(q, endpoint="search")
    replacement_results[q["id"]] = r
    print(f"  total={r['total']} passing={r['passing']} signal={r['signal_rate']:.0%}")
    if r["sample_passing"]:
        for t in r["sample_passing"][:2]:
            print(f"    + {t[:80]}")
    time.sleep(1.2)

    # Also test news for broad queries
    if q["id"] in ("rB1", "rB2", "rB5", "rB6"):
        print(f"[/news]   {q['id']} — {q['desc']}")
        rn = audit_query(q, endpoint="news")
        replacement_results[q["id"] + "_news"] = rn
        print(f"  total={rn['total']} passing={rn['passing']} signal={rn['signal_rate']:.0%}")
        time.sleep(1.2)

# ---------------------------------------------------------------------------
# Phase 4: Write the report
# ---------------------------------------------------------------------------

print("\n=== Phase 4: Writing report ===\n")

lines = []
lines.append("# Series A Query Audit — 2026-04-29")
lines.append("")
lines.append("> **Purpose:** Systematic audit of the 10 current Serper queries in `series_a_pipeline.py`.")
lines.append("> Tests each against `/search` and `/news` endpoints with `tbs:qdr:d`. Signal rate = results passing all pipeline filters / total results.")
lines.append("> Also tests 10 replacement candidate queries.")
lines.append("")

# --- Current query table ---
lines.append("## Current Query Results")
lines.append("")
lines.append("| ID | Desc | Endpoint | Total | Passing | Signal Rate | Status |")
lines.append("|----|----- |----------|-------|---------|-------------|--------|")

for q in ALL_QUERIES:
    for endpoint, rmap in [("search", search_results), ("news", news_results)]:
        r = rmap[q["id"]]
        status = classify_status(r)
        lines.append(
            f"| {q['id']} | {q['desc']} | /{endpoint} | {r['total']} | {r['passing']} | {r['signal_rate']:.0%} | {status} |"
        )

lines.append("")

# --- Per-query breakdown ---
lines.append("## Per-Query Detail")
lines.append("")

for q in ALL_QUERIES:
    sr = search_results[q["id"]]
    nr = news_results[q["id"]]
    search_status = classify_status(sr)
    news_status = classify_status(nr)

    lines.append(f"### {q['id']} — {q['desc']}")
    lines.append(f"**Query:** `{q['query']}`")
    lines.append("")
    lines.append(f"- **/search:** {sr['total']} results, {sr['passing']} passing, {sr['signal_rate']:.0%} signal — **{search_status}**")
    lines.append(f"- **/news:** {nr['total']} results, {nr['passing']} passing, {nr['signal_rate']:.0%} signal — **{news_status}**")
    lines.append("")

    if sr["sample_passing"]:
        lines.append("**Good results (/search):**")
        for t in sr["sample_passing"]:
            lines.append(f"- {t}")
        lines.append("")

    if sr["sample_noise"]:
        lines.append("**Noise slipping through (/search):**")
        for t in sr["sample_noise"]:
            lines.append(f"- {t}")
        lines.append("")

    # News comparison verdict
    better_endpoint = "search"
    if nr["signal_rate"] > sr["signal_rate"] + 0.10 and nr["total"] >= 3:
        better_endpoint = "news"
        lines.append(f"> **Recommendation:** Switch to `/news` endpoint — higher signal rate ({nr['signal_rate']:.0%} vs {sr['signal_rate']:.0%})")
        lines.append("")
    elif nr["total"] == 0:
        lines.append("> **/news endpoint returns 0 results for this query.**")
        lines.append("")

# --- Replacement candidate table ---
lines.append("## Replacement Candidate Results")
lines.append("")
lines.append("| ID | Desc | Endpoint | Total | Passing | Signal Rate |")
lines.append("|----|------|----------|-------|---------|-------------|")

for q in REPLACEMENT_CANDIDATES:
    r = replacement_results.get(q["id"])
    if r:
        lines.append(f"| {q['id']} | {q['desc']} | /search | {r['total']} | {r['passing']} | {r['signal_rate']:.0%} |")
    rn = replacement_results.get(q["id"] + "_news")
    if rn:
        lines.append(f"| {q['id']}_news | {q['desc']} | /news | {rn['total']} | {rn['passing']} | {rn['signal_rate']:.0%} |")

lines.append("")

# --- Proposed replacement queries ---
lines.append("## Proposed Replacement Query Set")
lines.append("")
lines.append("Based on audit findings. Drop dead/degraded queries, add TechCrunch, add year anchor to broad queries, add Series B signal layer.")
lines.append("")

# Build proposed sets based on findings
def best_status(qid):
    return classify_status(search_results[qid])

# Decide which originals survive
survivors_a = []
survivors_b = []

for q in AGENT_A_QUERIES:
    if best_status(q["id"]) in ("HEALTHY", "DEGRADED"):
        survivors_a.append(q)

for q in AGENT_B_QUERIES:
    if best_status(q["id"]) in ("HEALTHY", "DEGRADED"):
        survivors_b.append(q)

# Build final proposed sets
# Agent A: site-specific, high-quality sources
proposed_a = []
# Always include TechCrunch
proposed_a.append({"id": "q1", "query": 'site:techcrunch.com "Series A"', "num": 20, "desc": "TechCrunch"})

# Include survivors + year-anchored versions based on audit
for q in AGENT_A_QUERIES:
    qid = q["id"]
    sr = search_results[qid]
    nr = news_results[qid]

    # Prefer year-anchored version if original is degraded/dead
    orig_status = classify_status(sr)
    anchored_key = None
    # Find matching replacement candidate
    for rc in REPLACEMENT_CANDIDATES:
        if q["desc"].split()[0].lower() in rc["desc"].lower() and "year" in rc["desc"].lower():
            anchored_key = rc["id"]
            break

    if orig_status == "DEAD":
        # Check if year-anchored replacement exists and is better
        if anchored_key and replacement_results.get(anchored_key):
            rc_r = replacement_results[anchored_key]
            if rc_r["signal_rate"] >= 0.30:
                rc_q = next(c for c in REPLACEMENT_CANDIDATES if c["id"] == anchored_key)
                proposed_a.append({"id": qid, "query": rc_q["query"], "num": 20, "desc": rc_q["desc"]})
                continue
        # If still dead, skip
    elif orig_status == "DEGRADED" and anchored_key and replacement_results.get(anchored_key):
        rc_r = replacement_results[anchored_key]
        if rc_r["signal_rate"] > sr["signal_rate"] + 0.05:
            rc_q = next(c for c in REPLACEMENT_CANDIDATES if c["id"] == anchored_key)
            proposed_a.append({"id": qid, "query": rc_q["query"], "num": 20, "desc": rc_q["desc"]})
            continue
        else:
            proposed_a.append(q)
    else:
        proposed_a.append(q)

# Cap Agent A at 6
proposed_a = proposed_a[:6]

# Agent B: broad sweep
proposed_b = []
# Prefer year-anchored broad sweep
rb1 = replacement_results.get("rB1")
q1_orig = search_results["q1"]
if rb1 and rb1["signal_rate"] > q1_orig["signal_rate"] + 0.05:
    proposed_b.append({"id": "q1b", "query": '"Series A" raises OR raised OR funding 2026 million startup', "num": 30, "desc": "broad sweep 2026"})
else:
    proposed_b.append({"id": "q1b", "query": '"Series A" raises OR raised OR funding OR round million', "num": 30, "desc": "broad sweep"})

# Announcement language — keep or year-anchor
rb5 = replacement_results.get("rB5")
q2_orig = search_results["q2"]
if rb5 and rb5["signal_rate"] > q2_orig["signal_rate"] + 0.05:
    proposed_b.append({"id": "q2b", "query": '"Series A" announces OR secures OR closes funding startup 2026', "num": 20, "desc": "announcement 2026"})
else:
    proposed_b.append({"id": "q2b", "query": '"Series A" announces OR secures OR closes OR completes funding', "num": 20, "desc": "announcement language"})

# Press wires — keep or year-anchor
rb4 = replacement_results.get("rB4")
q6_orig = search_results["q6"]
if rb4 and rb4["signal_rate"] > q6_orig["signal_rate"] + 0.05:
    proposed_b.append({"id": "q6b", "query": '"Series A" site:businesswire.com OR site:prnewswire.com 2026', "num": 10, "desc": "press wires 2026"})
else:
    proposed_b.append({"id": "q6b", "query": '"Series A" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com', "num": 10, "desc": "press wires"})

# VC language with year anchor
rb3 = replacement_results.get("rB3")
q7_orig = search_results["q7"]
if rb3 and rb3["signal_rate"] > q7_orig["signal_rate"] + 0.05:
    proposed_b.append({"id": "q7b", "query": '"led the round" "Series A" 2026', "num": 20, "desc": "VC language 2026"})
else:
    proposed_b.append({"id": "q7b", "query": '"led the round" OR "led the Series A" OR "led a" Series A investment startup', "num": 20, "desc": "VC language"})

# Series B sweep (new)
rb2 = replacement_results.get("rB2")
if rb2 and rb2["signal_rate"] >= 0.40:
    proposed_b.append({"id": "q8b", "query": '"Series B" raises OR raised OR funding OR round million', "num": 20, "desc": "Series B broad sweep"})

# Series B press wires (new)
rb6 = replacement_results.get("rB6")
if rb6 and rb6["signal_rate"] >= 0.40:
    proposed_b.append({"id": "q9b", "query": '"Series B" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com', "num": 10, "desc": "Series B press wires"})

# Cap Agent B at 6
proposed_b = proposed_b[:6]

# Format as Python code
def format_query_list(name: str, queries: list) -> str:
    out = [f"{name} = ["]
    for q in queries:
        out.append(f'    {{"id": "{q["id"]}", "query": {json.dumps(q["query"])}, "num": {q["num"]}, "desc": "{q["desc"]}"}},')
    out.append("]")
    return "\n".join(out)

lines.append("```python")
lines.append(format_query_list("AGENT_A_QUERIES", proposed_a))
lines.append("")
lines.append(format_query_list("AGENT_B_QUERIES", proposed_b))
lines.append("```")
lines.append("")

# --- Endpoint recommendation ---
lines.append("## Endpoint Recommendations")
lines.append("")
lines.append("For each query, whether to use `/search` or `/news`:")
lines.append("")
lines.append("| Query ID | Desc | Recommended Endpoint | Reason |")
lines.append("|----------|------|---------------------|--------|")

all_tested = ALL_QUERIES + REPLACEMENT_CANDIDATES
for q in all_tested:
    qid = q["id"]
    sr = search_results.get(qid) or replacement_results.get(qid)
    nr = news_results.get(qid) or replacement_results.get(qid + "_news")

    if not sr:
        continue

    if nr and nr["total"] > 0 and nr["signal_rate"] > (sr["signal_rate"] if sr else 0) + 0.10:
        rec = "/news"
        reason = f"/news signal {nr['signal_rate']:.0%} vs /search {sr['signal_rate']:.0%}"
    else:
        rec = "/search"
        reason = "/search sufficient" if (not nr or nr["total"] == 0) else f"/search {sr['signal_rate']:.0%} vs /news {nr['signal_rate']:.0%}"

    lines.append(f"| {qid} | {q['desc']} | {rec} | {reason} |")

lines.append("")

# --- Key findings ---
lines.append("## Key Findings")
lines.append("")

dead_qs = [q for q in ALL_QUERIES if classify_status(search_results[q["id"]]) == "DEAD"]
degraded_qs = [q for q in ALL_QUERIES if classify_status(search_results[q["id"]]) == "DEGRADED"]
healthy_qs = [q for q in ALL_QUERIES if classify_status(search_results[q["id"]]) == "HEALTHY"]

lines.append(f"- **DEAD ({len(dead_qs)}):** {', '.join(q['id'] + ' (' + q['desc'] + ')' for q in dead_qs) or 'none'}")
lines.append(f"- **DEGRADED ({len(degraded_qs)}):** {', '.join(q['id'] + ' (' + q['desc'] + ')' for q in degraded_qs) or 'none'}")
lines.append(f"- **HEALTHY ({len(healthy_qs)}):** {', '.join(q['id'] + ' (' + q['desc'] + ')' for q in healthy_qs) or 'none'}")
lines.append("")

# Year anchor effectiveness
year_better = []
year_worse = []
for rc in REPLACEMENT_CANDIDATES:
    if "2026" in rc["query"] and rc["id"] in replacement_results:
        rc_r = replacement_results[rc["id"]]
        # Find original equivalent
        orig_qid = None
        for q in ALL_QUERIES:
            if q["desc"].split()[0].lower() in rc["desc"].lower():
                orig_qid = q["id"]
                break
        if orig_qid and orig_qid in search_results:
            orig_r = search_results[orig_qid]
            diff = rc_r["signal_rate"] - orig_r["signal_rate"]
            if diff > 0.05:
                year_better.append(f"{rc['id']} ({rc['desc']}): +{diff:.0%}")
            elif diff < -0.05:
                year_worse.append(f"{rc['id']} ({rc['desc']}): {diff:.0%}")

if year_better:
    lines.append(f"- **Year anchor (2026) improved signal:** {'; '.join(year_better)}")
else:
    lines.append("- **Year anchor (2026):** No meaningful improvement over unanchored queries — omit to avoid missing edge-of-window results")

series_b_viable = any(
    replacement_results.get(qid, {}).get("signal_rate", 0) >= 0.40
    for qid in ("rB2", "rB6")
)
lines.append(f"- **Series B queries:** {'viable — signal rate >= 40%, adding to AGENT_B' if series_b_viable else 'signal rate too low — not adding'}")

# TechCrunch assessment
tc_r = replacement_results.get("rA1", {})
lines.append(f"- **TechCrunch:** {tc_r.get('total', 0)} results, {tc_r.get('signal_rate', 0):.0%} signal — {'adding to AGENT_A' if tc_r.get('signal_rate', 0) >= 0.50 else 'signal lower than expected'}")
lines.append("")

lines.append("---")
lines.append("*Generated by `scripts/query_audit.py`*")

report = "\n".join(lines)

out_path = REPO_ROOT / "data" / "query-audit-2026-04-29.md"
out_path.parent.mkdir(exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n[DONE] Report written to: {out_path}")
print(report[:2000])
