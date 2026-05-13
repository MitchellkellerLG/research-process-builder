"""
Research Agent — FireCrawl + SerperDev + gpt-4o-mini pipeline.

Combines search, deep scrape, and structured extraction into one deterministic
agent. Validated against ground-truth/*.json for annealable accuracy scoring.

Usage:
    py scripts/agent_research.py --domain stripe.com --category company_profile
    py scripts/agent_research.py --domain stripe.com --category company_profile --gt
    py scripts/agent_research.py --all-gt --category founders_ceo
    py scripts/agent_research.py --all-gt --anneal --rounds 3
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
import requests

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

FIRECRAWL_KEY = os.getenv("FIRECRAWL_API_KEY", "")
SERPER_KEY = os.getenv("SERPER_API_KEY", "")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
GT_DIR = PROJECT_DIR / "ground-truth"
OUTPUT_DIR = PROJECT_DIR / "output" / "agent-research"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FC_BASE = "https://api.firecrawl.dev/v1"
SERPER_URL = "https://google.serper.dev/search"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# ── SerperDev search ──────────────────────────────────────────────────────────
def serper_search(query: str, num: int = 5) -> list[dict]:
    """Google search via SerperDev. Returns [{title, link, snippet}, ...]."""
    if not SERPER_KEY:
        print("  [serper] SERPER_API_KEY not set - skipping search")
        return []
    try:
        resp = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        organic = data.get("organic", [])
        print(f"  [serper] '{query[:60]}...' -> {len(organic)} results")
        return [{"title": r.get("title", ""), "link": r.get("link", ""), "snippet": r.get("snippet", "")} for r in organic]
    except Exception as e:
        print(f"  [serper] error: {e}")
        return []


# ── FireCrawl scrape ──────────────────────────────────────────────────────────
def firecrawl_scrape(url: str, timeout_ms: int = 30_000) -> str | None:
    """Deep scrape a URL via FireCrawl. Returns markdown string."""
    if not FIRECRAWL_KEY:
        print(f"  [firecrawl] FIRECRAWL_API_KEY not set - skipping {url[:60]}")
        return None
    try:
        resp = requests.post(
            f"{FC_BASE}/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"},
            json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
            timeout=timeout_ms / 1000 + 5,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return None
        content = data.get("data", {}).get("markdown", "")
        if len(content) > 200:
            truncated = content[:12_000]
            print(f"  [firecrawl] {url[:60]}... -> {len(truncated)} chars")
            return truncated
        return None
    except Exception as e:
        print(f"  [firecrawl] error on {url[:60]}: {e}")
        return None


# ── gpt-4o-mini extraction ────────────────────────────────────────────────────
EXTRACTION_PROMPTS = {
    "company_profile": """Extract company profile information from the provided content. Return ONLY valid JSON:
{
  "description": "what the company does (one sentence)",
  "employee_count": "approximate count or range (e.g. '50-200')",
  "headquarters": "city and state/country",
  "founded_year": "year founded (YYYY)",
  "business_model": "B2B, B2C, or both",
  "confidence": "high|medium|low"
}
If a field is not found, use null. Do not invent information.""",

    "founders_ceo": """Extract founder and CEO information from the provided content. Return ONLY valid JSON:
{
  "names": ["full name 1", "full name 2"],
  "titles": ["title 1", "title 2"],
  "confidence": "high|medium|low"
}
Include only people explicitly mentioned as founders or CEO. If not found, use empty arrays and "low" confidence.""",

    "funding_financial": """Extract funding and financial information from the provided content. Return ONLY valid JSON:
{
  "total_raised": "total funding amount (e.g. '$50M')",
  "last_round_type": "Seed, Series A, Series B, etc.",
  "last_round_amount": "amount of last round",
  "key_investors": ["investor 1", "investor 2"],
  "valuation": "valuation if available",
  "confidence": "high|medium|low"
}
If a field is not found, use null or empty arrays.""",

    "competitor_identification": """Extract competitor information from the provided content. Return ONLY valid JSON:
{
  "competitors": ["company name 1", "company name 2"],
  "competitive_advantage": "what makes this company different (one sentence)",
  "market_position": "leader, challenger, niche, etc.",
  "confidence": "high|medium|low"
}
If not found, use empty arrays and null for missing fields.""",

    "leadership_people": """Extract leadership team information from the provided content. Return ONLY valid JSON:
{
  "ceo_name": "full name of CEO",
  "other_leaders": ["name 1", "name 2"],
  "confidence": "high|medium|low"
}
Include C-suite and VP-level executives. If not found, use null and empty arrays."""
}


def extract_with_openai(content: str, category: str) -> dict | None:
    """Extract structured data from scraped content using gpt-4o-mini."""
    if not OPENAI_KEY:
        print("  [openai] OPENAI_API_KEY not set")
        return None

    system_prompt = EXTRACTION_PROMPTS.get(category, EXTRACTION_PROMPTS["company_profile"])

    try:
        resp = requests.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 1024,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"].strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        print(f"  [openai] extracted {len(json.dumps(result))} chars")
        return result
    except Exception as e:
        print(f"  [openai] error: {e}")
        return None


# ── Agent pipeline ─────────────────────────────────────────────────────────────
def research_company(domain: str, category: str, company_name: str = "") -> dict:
    """Run the full agent pipeline: search -> scrape -> extract."""
    name = company_name or domain.replace(".com", "").replace("www.", "")
    print(f"\n{'='*60}")
    print(f"Research Agent: {name} ({domain}) - {category}")
    print(f"{'='*60}")

    # Step 1: SerperDev search
    queries = _build_queries(name, domain, category)
    all_urls: list[dict] = []
    seen_urls: set[str] = set()

    for q in queries:
        results = serper_search(q, num=3)
        for r in results:
            if r["link"] and r["link"] not in seen_urls:
                seen_urls.add(r["link"])
                all_urls.append(r)
        time.sleep(0.3)

    print(f"  Total unique URLs: {len(all_urls)}")

    # Step 2: FireCrawl scrape top URLs
    scraped: list[dict] = []
    for url_info in all_urls[:3]:
        content = firecrawl_scrape(url_info["link"])
        if content:
            scraped.append({"url": url_info["link"], "title": url_info["title"], "content": content})
        time.sleep(0.5)

    if not scraped:
        print("  No content scraped - aborting")
        return {"error": "no_content", "domain": domain, "category": category}

    # Step 3: Combine content and extract
    combined = "\n\n---\n\n".join(
        f"Source: {s['title']}\nURL: {s['url']}\n\n{s['content']}" for s in scraped
    )
    combined = combined[:20_000]

    extracted = extract_with_openai(combined, category)

    result = {
        "company": name,
        "domain": domain,
        "category": category,
        "model": "gpt-4o-mini",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": [s["url"] for s in scraped],
        "extracted": extracted,
        "gt_score": None,
    }

    # Step 4: GT validation (if ground truth exists)
    gt = _load_gt(company_name or name)
    if gt:
        result["gt_score"] = _score_against_gt(extracted, gt, category)
        print(f"  GT score: {result['gt_score']:.2f}")

    # Save output
    company_slug = name.lower().replace(" ", "-")
    out_path = OUTPUT_DIR / company_slug
    out_path.mkdir(parents=True, exist_ok=True)
    out_file = out_path / f"{category}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Output: {out_file}")

    return result


def _build_queries(name: str, domain: str, category: str) -> list[str]:
    """Build Serper search queries based on category."""
    templates = {
        "company_profile": [
            f"{name} company overview about",
            f"{name} company size employees headquarters founded",
            f"{name} what does {name} do business model",
        ],
        "founders_ceo": [
            f"{name} founder CEO leadership",
            f"{name} co-founder executive team",
            f"who is the CEO of {name}",
        ],
        "funding_financial": [
            f"{name} funding round total raised investors",
            f"{name} series funding valuation",
            f"{name} {domain} funding crunchbase",
        ],
        "competitor_identification": [
            f"{name} competitors alternatives",
            f"{name} vs competitor comparison",
            f"top alternatives to {name} {domain}",
        ],
        "leadership_people": [
            f"{name} leadership team executives",
            f"{name} CEO CTO CFO management",
            f"{name} executive leadership bios",
        ],
    }
    return templates.get(category, templates["company_profile"])


# ── GT scoring ────────────────────────────────────────────────────────────────
def _load_gt(company: str) -> dict | None:
    """Load ground truth for a company if it exists."""
    gt_path = GT_DIR / f"{company.lower().replace(' ', '_')}.json"
    if not gt_path.exists():
        for f in GT_DIR.glob("*.json"):
            if f.stem.lower() == company.lower().replace(" ", "_"):
                gt_path = f
                break
    if not gt_path.exists():
        return None
    with open(gt_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _score_against_gt(extracted: dict | None, gt: dict, category: str) -> float:
    """Score extracted data against ground truth. Returns 0.0-1.0."""
    if not extracted:
        return 0.0

    gt_cat = gt.get("categories", {}).get(category, {})
    if not gt_cat:
        return None

    scores = []

    text_fields = {
        "company_profile": ["description", "headquarters", "founded_year"],
        "leadership_people": ["ceo_name"],
        "funding_financial": ["total_raised", "last_round_type"],
    }

    for field in text_fields.get(category, []):
        expected = str(gt_cat.get(field, "")).lower()
        found = str(extracted.get(field, "")).lower()
        if expected and found:
            if expected in found or found in expected:
                scores.append(1.0)
            else:
                exp_words = set(expected.split())
                fnd_words = set(found.split())
                overlap = len(exp_words & fnd_words) / max(len(exp_words), 1)
                scores.append(overlap * 0.5)
        elif expected:
            scores.append(0.0)

    name_fields = {
        "founders_ceo": ("names", gt_cat.get("names", [])),
        "leadership_people": ("other_leaders", gt_cat.get("other_leaders", [])),
        "competitor_identification": ("competitors", gt_cat.get("competitors", [])),
    }

    for cat_key, (field, expected_list) in name_fields.items():
        if cat_key != category:
            continue
        found_list = extracted.get(field, [])
        if not expected_list:
            continue
        if not found_list:
            scores.append(0.0)
            continue
        found_lower = {n.lower().strip() for n in found_list}
        expected_lower = {n.lower().strip() for n in expected_list}
        overlap = len(found_lower & expected_lower)
        scores.append(overlap / max(len(expected_lower), 1))

    if not scores:
        return None
    return sum(scores) / len(scores)


# ── Batch / annealing ─────────────────────────────────────────────────────────
def run_all_gt(category: str, anneal: bool = False, rounds: int = 1) -> dict:
    """Run agent against all ground truth companies."""
    gt_companies = []
    for fpath in sorted(GT_DIR.glob("*.json")):
        if fpath.name == "schema.json":
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            gt_companies.append(json.load(f))

    print(f"\nRunning against {len(gt_companies)} GT companies")

    all_results = {}
    best_score = 0.0
    score_history = []

    for round_num in range(1, rounds + 1):
        if rounds > 1:
            print(f"\n{'#'*60}")
            print(f"# ROUND {round_num}/{rounds}")
            print(f"{'#'*60}")

        round_scores = []
        for gt in gt_companies:
            company = gt["company"]
            domain = gt["domain"]
            result = research_company(domain, category, company)
            key = f"{company}/{category}"
            all_results[key] = result
            if result.get("gt_score") is not None:
                round_scores.append(result["gt_score"])

        avg = sum(round_scores) / len(round_scores) if round_scores else 0.0
        score_history.append({"round": round_num, "avg_score": avg, "n": len(round_scores)})
        print(f"\n  Round {round_num} avg GT score: {avg:.3f} ({len(round_scores)} scored)")

        if avg > best_score:
            best_score = avg

        if anneal and round_num < rounds and avg < 0.90:
            print(f"  Score below 0.90 - would adjust queries/prompts here (manual step)")
            break

        if avg >= 0.95:
            print(f"  Score >= 0.95 - stopping early")
            break

    batch_out = OUTPUT_DIR / f"batch-{category}-{time.strftime('%Y%m%dT%H%M%S')}.json"
    with open(batch_out, "w", encoding="utf-8") as f:
        json.dump({
            "category": category,
            "rounds": score_history,
            "best_score": best_score,
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nBatch results: {batch_out}")

    return {"best_score": best_score, "rounds": score_history}


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Research Agent - FC + Serper + 4o-mini")
    parser.add_argument("--domain", help="Company domain (e.g. stripe.com)")
    parser.add_argument("--company", help="Company name (optional, derived from domain if omitted)")
    parser.add_argument("--category", default="company_profile",
                        choices=list(EXTRACTION_PROMPTS.keys()),
                        help="Research category")
    parser.add_argument("--gt", action="store_true", help="Always validate against ground truth")
    parser.add_argument("--all-gt", action="store_true", help="Run against all GT companies")
    parser.add_argument("--anneal", action="store_true", help="Annealing mode: iterate to improve")
    parser.add_argument("--rounds", type=int, default=3, help="Max annealing rounds")
    parser.add_argument("--json", action="store_true", help="Output result as JSON to stdout")

    args = parser.parse_args()

    if args.all_gt:
        result = run_all_gt(args.category, args.anneal, args.rounds)
        if args.json:
            print(json.dumps(result, indent=2))
        return

    if not args.domain:
        parser.error("--domain required (or use --all-gt)")

    result = research_company(args.domain, args.category, args.company or "")
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
