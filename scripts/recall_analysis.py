"""
Quick analysis: GT deduplication and source domain breakdown.
Helps interpret recall test results.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent

load_dotenv(REPO_ROOT / ".env")
load_dotenv(WORKSPACE_ROOT / ".env", override=False)

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL") or os.getenv("SUPABASE_URL")
if SUPABASE_URL and not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = None
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

cutoff = (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d")
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/funding_discoveries"
    f"?select=company_name,company_domain,discovered_date,source_url,round_type"
    f"&round_type=eq.Series A"
    f"&discovered_date=gte.{cutoff}"
    f"&order=discovered_date.desc"
    f"&limit=500",
    headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
    timeout=30,
)
rows = resp.json()
print(f"Total GT rows: {len(rows)}")

# Deduplicate by company name
_SUFFIX_RE = re.compile(
    r"\s*[,.]?\s*\b(Inc|Ltd|Corp|LLC|GmbH|Co|PLC|SA|AG|BV|Pty|SAS|SRL)\b\.?\s*$",
    re.IGNORECASE,
)
seen = {}
for r in rows:
    name = r.get("company_name", "").strip()
    name = _SUFFIX_RE.sub("", name)
    name = name.lower().strip()
    if name not in seen:
        seen[name] = r

print(f"Unique companies (after name dedup): {len(seen)}")

# Analyze source domains in GT
domain_counts = {}
for r in rows:
    url = r.get("source_url", "")
    if url:
        d = urlparse(url).netloc.replace("www.", "")
        domain_counts[d] = domain_counts.get(d, 0) + 1

print("\nGT source domain distribution (top 25):")
for d, cnt in sorted(domain_counts.items(), key=lambda x: -x[1])[:25]:
    print(f"  {cnt:3d}  {d}")

# Check how many GT rows come from sources the pipeline doesn't query
pipeline_domains = {
    "thesaasnews.com", "finsmes.com", "alleywatch.com", "techcrunch.com",
    "eu-startups.com", "tech.eu", "techround.co.uk",
    "businesswire.com", "prnewswire.com", "einpresswire.com",
}
covered = sum(1 for r in rows if any(pd in r.get("source_url", "") for pd in pipeline_domains))
print(f"\nGT rows from pipeline-covered sources: {covered}/{len(rows)} ({100*covered/len(rows):.1f}%)")

uncovered = [r for r in rows if not any(pd in r.get("source_url", "") for pd in pipeline_domains)]
print(f"GT rows from other sources: {len(uncovered)}")
print("\nSample uncovered source URLs:")
for r in uncovered[:10]:
    print(f"  {r.get('company_name','?')} <- {r.get('source_url','')[:80]}")

# Stage1 results summary
stage1_path = REPO_ROOT / "output" / "stages" / "stage1-2026-04-29.json"
if stage1_path.exists():
    with open(stage1_path, encoding="utf-8") as f:
        s1 = json.load(f)
    results = s1 if isinstance(s1, list) else s1.get("results", [])
    print(f"\nStage1 total results: {len(results)}")
    qs_counts = {}
    for r in results:
        q = r.get("query_source", "?")
        qs_counts[q] = qs_counts.get(q, 0) + 1
    for q, cnt in sorted(qs_counts.items()):
        print(f"  {q}: {cnt} results")
