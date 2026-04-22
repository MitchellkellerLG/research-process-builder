"""
Test domain extraction from PR article text.
Uses Spider API (same as pipeline) to get clean markdown, then tests extraction.
"""
import json
import os
import re
import sys
import requests
from pathlib import Path

SPIDER_API_KEY = os.environ.get("SPIDER_API_KEY", "")

SUSPECT_PATTERNS = [
    r'newswire|businesswire|prnewswire|einpresswire|globenewswire',
    r'techcrunch|thesaasnews|finsmes|alleywatch|vcnewsdaily',
    r'yahoo|reuters|bloomberg|forbes|fortune|cnbc|wsj',
    r'linkedin|crunchbase|pitchbook|wikipedia|facebook',
    r'eu-startups|tech\.eu|venturebeat|siliconangle',
    r'finanzwire|therecursive|netinfluencer|biospace',
    r'kitsapsun|cincinnati|bandt\.com',
    r'google\.com|bing\.com|finance\.biggo|gobiernu',
    r'googletagmanager|googleapis|gstatic|cloudfront|cloudflare',
    r'wistia|cision|adobedtm|doubleclick|googlesyndication',
    r'cdn\.|analytics\.|tracker\.|pixel\.|tag\.',
    r'fonts\.|static\.|assets\.|media\.|images\.',
    r'licdn|fbcdn|twimg|ytimg|akamai|yimg|oath',
    r'gravatar|wordpress\.com|wp\.com|disqus',
    r'newrelic|segment\.io|mixpanel|hotjar|intercom',
    r'yoast|schema\.org|w3\.org',
    r'xpr-gannett|gannett|dataroid',
    r'digitaltoday\.co',
]

def is_suspect(domain: str, source_url: str) -> bool:
    for p in SUSPECT_PATTERNS:
        if re.search(p, domain, re.I):
            return True
    try:
        from urllib.parse import urlparse
        source_domain = urlparse(source_url).hostname.replace("www.", "")
        if domain == source_domain:
            return True
    except:
        pass
    return False


def extract_domain_from_article(text: str, company_name: str, source_url: str) -> dict:
    from urllib.parse import urlparse
    source_domain = ""
    try:
        source_domain = urlparse(source_url).hostname.replace("www.", "")
    except:
        pass

    norm_company = re.sub(r'[^a-z0-9]', '', company_name.lower())

    patterns = [
        # "visit us at", "learn more at", "about" sections
        r'(?:visit|learn more|more (?:info|information|at)|about us|website|web)\s*(?:at\s*)?[:.]?\s*(?:https?://)?(?:www\.)?([a-z0-9][-a-z0-9]*\.[a-z]{2,}(?:\.[a-z]{2,})?)',
        # Markdown links [text](url) — common in Spider markdown output
        r'\[.*?\]\((?:https?://)?(?:www\.)?([a-z0-9][-a-z0-9]*\.(?:com|io|ai|co|dev|app|tech|health|bio))[/)\s]',
        # Direct URLs in text
        r'(?:https?://)?(?:www\.)?([a-z0-9][-a-z0-9]*\.(?:com|io|ai|co|dev|app|tech|health|bio))\b',
        # Email domains
        r'[\w.+-]+@([a-z0-9][-a-z0-9]*\.[a-z]{2,}(?:\.[a-z]{2,})?)',
    ]

    candidates = {}
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            domain = match.group(1).lower().replace("www.", "")
            if is_suspect(domain, source_url):
                continue
            if domain == source_domain:
                continue
            if len(domain) < 4:
                continue

            norm_domain = re.sub(r'[^a-z0-9]', '', domain.split(".")[0])
            score = candidates.get(domain, 0)
            if norm_domain and norm_company and (norm_domain in norm_company or norm_company in norm_domain):
                score += 10
            score += 1
            candidates[domain] = score

    if not candidates:
        return {"domain": None, "candidates": {}, "method": "none"}

    sorted_c = sorted(candidates.items(), key=lambda x: -x[1])
    best_domain, best_score = sorted_c[0]

    if best_score >= 10:
        return {"domain": best_domain, "score": best_score, "candidates": dict(sorted_c[:5]), "method": "name_match"}
    if len(sorted_c) == 1 and best_score >= 2:
        return {"domain": best_domain, "score": best_score, "candidates": dict(sorted_c[:5]), "method": "sole_candidate"}

    return {"domain": None, "score": best_score, "candidates": dict(sorted_c[:5]), "method": "low_confidence"}


def fetch_via_spider(url: str) -> str | None:
    """Fetch article via Spider API (same as pipeline) to get clean markdown."""
    if SPIDER_API_KEY:
        try:
            resp = requests.post(
                "https://api.spider.cloud/crawl",
                headers={
                    "Authorization": f"Bearer {SPIDER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"url": url, "limit": 1, "return_format": "markdown"},
                timeout=20,
            )
            if resp.ok:
                data = resp.json()
                content = ""
                if isinstance(data, list) and data:
                    content = data[0].get("content", "")
                elif isinstance(data, dict):
                    content = data.get("content", "")
                if len(content) > 200:
                    return content[:15000]
        except Exception as e:
            print(f"      Spider error: {e}")

    # Fallback to direct fetch
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; LeadGrow/1.0)"}, timeout=10)
        if resp.ok and len(resp.text) > 200:
            return resp.text[:15000]
    except:
        pass
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--spider-key", type=str, help="Spider API key")
    parser.add_argument("--env-file", type=str, help="Path to .env file to load SPIDER_API_KEY from")
    args = parser.parse_args()

    global SPIDER_API_KEY
    if args.spider_key:
        SPIDER_API_KEY = args.spider_key
    elif args.env_file:
        with open(args.env_file) as f:
            for line in f:
                if line.startswith("SPIDER_API_KEY="):
                    SPIDER_API_KEY = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break

    output_file = Path(__file__).parent.parent / "output" / "series-a-2026-04-21.json"
    with open(output_file) as f:
        data = json.load(f)

    companies = data.get("companies", [])

    spider_status = "Spider API" if SPIDER_API_KEY else "direct HTTP (set SPIDER_API_KEY for better results)"
    print(f"\n{'='*90}")
    print(f"  DOMAIN EXTRACTION TEST -- {len(companies)} companies")
    print(f"  Fetch method: {spider_status}")
    print(f"{'='*90}\n")

    correct = 0
    wrong = 0
    not_found = 0
    improved = 0
    unfetchable = 0

    for c in companies:
        name = c["company_name"]
        expected = c.get("company_domain", "not_found")
        source_url = c.get("source_url", "")

        print(f"\n  {name}")
        print(f"    Current domain: {expected}")
        print(f"    Source: {source_url[:80]}")

        article = fetch_via_spider(source_url)
        if not article:
            print(f"    ! Could not fetch article")
            unfetchable += 1
            continue

        print(f"    Article length: {len(article)} chars")
        result = extract_domain_from_article(article, name, source_url)
        extracted = result.get("domain")

        if extracted:
            exp_clean = expected.replace("www.", "").lower() if expected else ""
            if extracted == exp_clean:
                print(f"    OK Extracted: {extracted} (MATCHES)")
                correct += 1
            elif expected in ("not_found", "not_stated", "") or is_suspect(expected, source_url):
                print(f"    ++ Extracted: {extracted} (IMPROVEMENT over '{expected}')")
                improved += 1
            else:
                print(f"    XX Extracted: {extracted} (expected {expected})")
                wrong += 1
        else:
            candidates = result.get("candidates", {})
            if candidates:
                top3 = dict(list(candidates.items())[:3])
                print(f"    -- No confident match. Candidates: {top3}")
            else:
                print(f"    -- No domains found in article")
            not_found += 1

    total = correct + wrong + not_found + improved
    print(f"\n{'='*90}")
    print(f"  RESULTS (excludes {unfetchable} unfetchable articles)")
    print(f"{'='*90}")
    print(f"  Correct matches:  {correct}/{total}")
    print(f"  Improvements:     {improved}/{total}")
    print(f"  Wrong:            {wrong}/{total}")
    print(f"  Not found:        {not_found}/{total}")
    if total > 0:
        print(f"  Hit rate:         {(correct + improved) / total * 100:.0f}%")


if __name__ == "__main__":
    main()
