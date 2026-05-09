"""
Product Launch News Pipeline

Discovers product launches from tech press and Hacker News via hybrid
direct-scrape + Serper approach, classifies them, and scores against GT.

Architecture:
  Stage 1A -> Direct source fetches (free, primary):
    - TechCrunch date pages (today + yesterday)
    - HN Show feed + HN front page
  Stage 1B -> Serper site-specific queries (supplement):
    - site:techcrunch.com, site:venturebeat.com, site:theverge.com, press wires
  Stage 2  -> GPT-4o-mini batch classify & filter
  Stage 3  -> Score against ground truth

Key finding from query testing: direct page scraping hits 100% GT recall;
Serper keyword queries max at 25%. Architecture reflects this -- direct
scrapes are primary, Serper fills gaps.

Usage:
    py scripts/product_launch_news_pipeline.py                    # full run
    py scripts/product_launch_news_pipeline.py --date 2026-05-04  # specific date
    py scripts/product_launch_news_pipeline.py --stage 1          # discovery only
    py scripts/product_launch_news_pipeline.py --skip-serper      # direct scrapes only
    py scripts/product_launch_news_pipeline.py --dry-run          # preview queries
    py scripts/product_launch_news_pipeline.py --score-only       # score stage2 vs GT
"""

import json
import sys
import os
import re
import argparse
import concurrent.futures
from pathlib import Path
from datetime import datetime, timedelta
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Env + path setup -- mirrors pipeline_base.py convention
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(PROJECT_DIR.parent / ".env", override=False)
load_dotenv(Path.home() / ".env", override=False)

_shared = os.environ.get("SHARED_SCRIPTS_PATH")
if not _shared:
    _candidate = PROJECT_DIR.parent / "leadgrow-hq" / "tools" / "shared-scripts"
    _shared = str(_candidate) if _candidate.exists() else str(SCRIPT_DIR)
sys.path.insert(0, _shared)

import serper_search
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OUTPUT_DIR = PROJECT_DIR / "output"
STAGE_DIR = PROJECT_DIR / "output" / "stages"
GT_PATH = PROJECT_DIR / "processes" / "find-product-launches-news" / "ground_truth.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LeadGrow/1.0)"}

# ---------------------------------------------------------------------------
# Serper supplement queries (Tier 2)
# ---------------------------------------------------------------------------

SERPER_QUERIES = [
    {
        "id": "q_tc",
        "query": 'site:techcrunch.com "launches" OR "announces" OR "introduces" OR "debuts"',
        "desc": "TechCrunch launches",
        "num": 20,
    },
    {
        "id": "q_vb",
        "query": "site:venturebeat.com launches OR announces product",
        "desc": "VentureBeat launches",
        "num": 15,
    },
    {
        "id": "q_verge",
        "query": 'site:theverge.com "launches" OR "announces" product',
        "desc": "The Verge launches",
        "num": 15,
    },
    {
        "id": "q_wire",
        "query": '"now available" OR "product launch" site:businesswire.com OR site:prnewswire.com',
        "desc": "Press wire launches",
        "num": 10,
    },
]

# ---------------------------------------------------------------------------
# HTML parsers for TC and HN
# ---------------------------------------------------------------------------


class TCArticleParser(HTMLParser):
    """Extract article titles and URLs from a TechCrunch date-index page."""

    def __init__(self):
        super().__init__()
        self.articles = []
        self._in_article_link = False
        self._current_href = None

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "a":
            href = attrs_d.get("href", "")
            # TC article URLs: /YYYY/MM/DD/slug/
            if re.match(r"https://techcrunch\.com/\d{4}/\d{2}/\d{2}/[^/]+/?$", href):
                self._in_article_link = True
                self._current_href = href

    def handle_data(self, data):
        if self._in_article_link and data.strip():
            title = data.strip()
            if len(title) > 20:  # skip nav labels
                self.articles.append({"title": title, "url": self._current_href})
            self._in_article_link = False
            self._current_href = None

    def handle_endtag(self, tag):
        if tag == "a":
            self._in_article_link = False


class HNShowParser(HTMLParser):
    """Extract Show HN titles and linked URLs from news.ycombinator.com/show or /front."""

    def __init__(self):
        super().__init__()
        self.items = []
        self._in_titleline = False
        self._current_href = None

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        cls = attrs_d.get("class", "")
        if "titleline" in cls:
            self._in_titleline = True
        if self._in_titleline and tag == "a":
            self._current_href = attrs_d.get("href", "")

    def handle_data(self, data):
        if self._in_titleline and data.strip() and self._current_href:
            title = data.strip()
            self.items.append({"title": title, "url": self._current_href})
            self._in_titleline = False
            self._current_href = None

    def handle_endtag(self, tag):
        if tag == "span":
            self._in_titleline = False


# ---------------------------------------------------------------------------
# Stage 1A: Direct source fetches
# ---------------------------------------------------------------------------


def fetch_tc_date_page(date_str: str) -> list[dict]:
    """Fetch TechCrunch date page and return list of {title, url, source}."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    url = f"https://techcrunch.com/{dt.year}/{dt.month:02d}/{dt.day:02d}/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"    TC {date_str}: HTTP {resp.status_code}")
            return []
        parser = TCArticleParser()
        parser.feed(resp.text)
        articles = parser.articles
        # dedup by URL (TC date pages can repeat)
        seen = set()
        deduped = []
        for a in articles:
            if a["url"] not in seen:
                seen.add(a["url"])
                deduped.append(a)
        print(f"    TC {date_str}: {len(deduped)} articles")
        return [
            {
                "title": a["title"],
                "source_url": a["url"],
                "source_domain": "techcrunch.com",
                "snippet": "",
                "query_source": f"tc_direct_{date_str}",
            }
            for a in deduped
        ]
    except Exception as e:
        print(f"    TC {date_str}: error -- {e}")
        return []


def fetch_hn_show_page() -> list[dict]:
    """Fetch HN Show feed and return list of {title, url, source}."""
    url = "https://news.ycombinator.com/show"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"    HN Show: HTTP {resp.status_code}")
            return []
        parser = HNShowParser()
        parser.feed(resp.text)
        items = parser.items
        print(f"    HN Show: {len(items)} items")
        return [
            {
                "title": it["title"],
                "source_url": it["url"],
                "source_domain": it["url"].split("/")[2] if "://" in it["url"] else "news.ycombinator.com",
                "snippet": "",
                "query_source": "hn_show",
            }
            for it in items
        ]
    except Exception as e:
        print(f"    HN Show: error -- {e}")
        return []


def fetch_hn_front_page(date_str: str) -> list[dict]:
    """Fetch HN front page for a specific date."""
    url = f"https://news.ycombinator.com/front?day={date_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"    HN front {date_str}: HTTP {resp.status_code}")
            return []
        parser = HNShowParser()
        parser.feed(resp.text)
        items = parser.items
        print(f"    HN front {date_str}: {len(items)} items")
        return [
            {
                "title": it["title"],
                "source_url": it["url"],
                "source_domain": it["url"].split("/")[2] if "://" in it["url"] else "news.ycombinator.com",
                "snippet": "",
                "query_source": f"hn_front_{date_str}",
            }
            for it in items
        ]
    except Exception as e:
        print(f"    HN front {date_str}: error -- {e}")
        return []


def run_direct_fetches(date_str: str, dry_run: bool = False) -> list[dict]:
    """Stage 1A: fetch TC date pages + HN pages directly."""
    yesterday = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    sources = [
        ("TC today", date_str),
        ("TC yesterday", yesterday),
        ("HN Show", None),
        ("HN front", date_str),
    ]

    if dry_run:
        for label, d in sources:
            if d:
                print(f"  [DRY] {label}: fetching date page for {d}")
            else:
                print(f"  [DRY] {label}: fetching current feed")
        return []

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {}
        futures[ex.submit(fetch_tc_date_page, date_str)] = "TC today"
        futures[ex.submit(fetch_tc_date_page, yesterday)] = "TC yesterday"
        futures[ex.submit(fetch_hn_show_page)] = "HN Show"
        futures[ex.submit(fetch_hn_front_page, date_str)] = "HN front"

        for f in concurrent.futures.as_completed(futures):
            results.extend(f.result())

    return results


# ---------------------------------------------------------------------------
# Stage 1B: Serper supplement
# ---------------------------------------------------------------------------


def run_serper_queries(tbs: str, dry_run: bool = False) -> list[dict]:
    """Stage 1B: run Serper site-specific supplement queries."""
    if dry_run:
        for q in SERPER_QUERIES:
            print(f"  [DRY] {q['id']}: {q['desc']} (num={q['num']})")
        return []

    results = []

    def run_one(qdef):
        orig = serper_search.DEFAULT_NUM_RESULTS
        serper_search.DEFAULT_NUM_RESULTS = qdef["num"]
        try:
            raw = serper_search.search(query=qdef["query"], news=False, tbs=tbs)
        except Exception as e:
            serper_search.DEFAULT_NUM_RESULTS = orig
            print(f"  [{qdef['id']}] {qdef['desc']}: ERROR -- {e}")
            return []
        finally:
            serper_search.DEFAULT_NUM_RESULTS = orig

        items = raw.get("organic", [])
        out = []
        for item in items:
            url = item.get("link", "")
            domain = url.split("/")[2] if "://" in url else ""
            out.append({
                "title": item.get("title", ""),
                "source_url": url,
                "source_domain": domain,
                "snippet": item.get("snippet", "")[:300],
                "query_source": qdef["id"],
            })
        print(f"  [{qdef['id']}] {qdef['desc']}: {len(out)} results")
        return out

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(run_one, q) for q in SERPER_QUERIES]
        for f in concurrent.futures.as_completed(futures):
            results.extend(f.result())

    return results


# ---------------------------------------------------------------------------
# Stage 2: Classify & filter via GPT-4o-mini
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM = "You classify news articles as product launches. Output strict JSON only."

_CLASSIFY_USER_TEMPLATE = """You are given a list of news article titles (and optional snippets) from tech press and Hacker News.

For each item, classify whether it is a PRODUCT LAUNCH or feature announcement.

KEEP (is_launch=true) if:
- Article is about a new product, new feature, new version, or open-source project released for the first time
- Company is real and identifiable
- "Show HN: ..." posts that introduce something new
- Company launches a new service, platform, or initiative (e.g. "Amazon opens logistics network" = new_product)
- Company launches a joint venture or new business unit focused on a product/service
- Company adds new AI tools or features to an existing product

DISCARD (is_launch=false) if:
- Product review (product existed before, this tests/reviews it)
- Funding announcement ONLY (Series A/B/C) -- funding pipeline handles those. But if an article is PRIMARILY about a new product/service and mentions funding secondarily, KEEP it.
- Job posting, acquisition (unless acquiring to launch new product), market analysis, opinion, roundup
- Listicle ("best AI tools 2026")
- Court cases, lawsuits, regulatory actions
- Earnings reports, stock news, market commentary

COMPANY NAME EXTRACTION RULES:
- For "Show HN: ProductName" titles: the company name is the product name or the maker. NEVER return "Show HN" as company_name.
- For "Show HN: ProductName -- description" titles: extract ProductName as both company_name and product_name.
- If title mentions a well-known company (Amazon, DoorDash, Anthropic, OpenAI, etc.), use that as company_name.
- If title says "X launches Y" or "X announces Y", X is the company, Y is the product.
- Never return "Unknown" as company_name -- extract the best guess from the title.

For each KEPT item, also classify:
- launch_type: "new_product" (brand new thing, new service, new platform, new JV) or "new_feature" (extends existing product)
- is_ai: true if the product is AI-powered or AI-related. Flag true if title or snippet contains ANY of:
  "AI", "artificial intelligence", "LLM", "GPT", "Claude", "neural", "embeddings", "fine-tun",
  "machine learning", "ML", "agentic", "MCP" (Model Context Protocol), "RAG", "vector",
  "diffusion", "generative", "copilot", "AI-powered", "AI-native", "AI-driven",
  "context for agents", "context layer for agents", "AI agents", "software agents",
  "dashboard for agents", "tool for agents", "built for agents".
  CRITICAL RULE: If the product NAME contains "Agents" or "Agent" (e.g. "Airbyte Agents",
  "AI Agents", "Agent SDK") it is ALWAYS is_ai=true -- software agents are AI systems.
  Also flag true if the product description implies AI automation (e.g. "turns notes into
  visual mind maps" = auto-generation by AI, "context for agents across data sources" = AI agent
  infrastructure). Flag false only if there is no AI signal at all.
- company_name: the company behind the product (see extraction rules above)
- product_name: the product, service, or feature being launched

Return STRICT JSON:
{
  "results": [
    {
      "idx": 1,
      "is_launch": true,
      "launch_type": "new_product",
      "is_ai": false,
      "company_name": "Acme Corp",
      "product_name": "Acme Widget"
    },
    {
      "idx": 2,
      "is_launch": false,
      "reason": "product review"
    }
  ]
}

Items:
{items}"""


def classify_batch(items: list[dict]) -> list[dict]:
    """
    Run GPT-4o-mini on a batch of raw items. Returns list with is_launch,
    launch_type, is_ai, company_name, product_name appended.
    Items must have 'idx', 'title', 'snippet'.
    """
    if not OPENAI_API_KEY:
        print("    [WARN] OPENAI_API_KEY missing -- classify no-op'd")
        return []

    BATCH_SIZE = 30
    results_map: dict[int, dict] = {}

    for start in range(0, len(items), BATCH_SIZE):
        batch = items[start: start + BATCH_SIZE]
        lines = []
        for local_i, it in enumerate(batch, 1):
            snippet = (it.get("snippet") or "").replace("\n", " ").strip()[:200]
            title = (it.get("title") or "").replace("\n", " ").strip()
            line = f"[{local_i}] TITLE: {title}"
            if snippet:
                line += f" | SNIPPET: {snippet}"
            lines.append(line)

        user_msg = _CLASSIFY_USER_TEMPLATE.replace("{items}", "\n".join(lines))

        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 3000,
                    "messages": [
                        {"role": "system", "content": _CLASSIFY_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                },
                timeout=60,
            )
            resp.raise_for_status()
            body = json.loads(resp.json()["choices"][0]["message"]["content"])
            for r in body.get("results", []):
                local_idx = r.get("idx")
                if local_idx is None or not (1 <= local_idx <= len(batch)):
                    continue
                global_idx = batch[local_idx - 1]["idx"]
                results_map[global_idx] = r
        except Exception as e:
            print(f"    [WARN] GPT classify batch failed: {e}")

    out = []
    for it in items:
        r = results_map.get(it["idx"])
        if r and r.get("is_launch"):
            out.append({**it, **r})
    return out


def dedup_launches(launches: list[dict]) -> list[dict]:
    """
    Dedup by company_name + product_name (normalized). Keep highest-quality source.
    Source priority: company_blog > techcrunch > venturebeat > verge > press_wire > hn > other
    """
    SOURCE_RANK = {
        "techcrunch.com": 2,
        "venturebeat.com": 3,
        "theverge.com": 3,
        "businesswire.com": 4,
        "prnewswire.com": 4,
        "news.ycombinator.com": 5,
    }

    def source_rank(item: dict) -> int:
        domain = item.get("source_domain", "")
        qs = item.get("query_source", "")
        # Company's own domain (not in known press list) = best
        if domain not in SOURCE_RANK and domain and "ycombinator" not in domain:
            return 1
        return SOURCE_RANK.get(domain, 6)

    def key(item: dict) -> str:
        c = re.sub(r"[^a-z0-9]", "", (item.get("company_name") or "").lower())
        p = re.sub(r"[^a-z0-9]", "", (item.get("product_name") or "").lower())
        return f"{c}|{p}"

    groups: dict[str, list] = {}
    for item in launches:
        k = key(item)
        groups.setdefault(k, []).append(item)

    deduped = []
    for k, group in groups.items():
        best = min(group, key=source_rank)
        # Attach all source URLs
        best = dict(best)
        best["all_sources"] = [{"url": g["source_url"], "domain": g["source_domain"]} for g in group]
        deduped.append(best)

    return deduped


def run_classify(raw_results: list[dict]) -> dict:
    """Stage 2: classify raw results, dedup, return structured output."""
    # Assign global idx for batch tracking
    for i, r in enumerate(raw_results):
        r["idx"] = i

    # Drop TC tag/author/archive pagination pages from Serper results
    # These match patterns like /tag/foo/page/N/ or /author/foo/page/N/
    _SKIP_URL_PATTERNS = [
        r"techcrunch\.com/tag/",
        r"techcrunch\.com/author/",
        r"techcrunch\.com/category/",
        r"/page/\d+",
    ]
    _skip_re = re.compile("|".join(_SKIP_URL_PATTERNS))

    deduped_filtered = []
    skipped_pages = 0
    seen_urls: set = set()
    for r in raw_results:
        url = r.get("source_url", "")
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        if _skip_re.search(url):
            skipped_pages += 1
            continue
        deduped_filtered.append(r)

    unique_raw = deduped_filtered
    print(f"    Raw: {len(raw_results)} -> after URL dedup+page filter: {len(unique_raw)}"
          f" (skipped {skipped_pages} pagination pages)")

    launches = classify_batch(unique_raw)
    print(f"    GPT: {len(launches)} launches from {len(unique_raw)} items")

    deduped = dedup_launches(launches)
    print(f"    After company dedup: {len(deduped)}")

    filtered_out = [
        {"title": r.get("title", "")[:80], "url": r.get("source_url", ""),
         "reason": r.get("reason", "not a launch")}
        for r in unique_raw
        if not any(
            (d.get("source_url") == r.get("source_url") or d.get("idx") == r.get("idx"))
            for d in launches
        )
    ]

    return {
        "launches": deduped,
        "filtered_out": filtered_out[:50],  # cap for file size
        "stats": {
            "raw_count": len(raw_results),
            "unique_raw": len(unique_raw),
            "launch_count": len(launches),
            "deduped_count": len(deduped),
        },
    }


# ---------------------------------------------------------------------------
# Stage 3: Score against ground truth
# ---------------------------------------------------------------------------


def score_against_gt(stage2: dict, gt_path: Path = GT_PATH) -> dict:
    """Compare classified launches against GT. Print recall, precision, per-product details."""
    if not gt_path.exists():
        print(f"    GT file not found: {gt_path}")
        return {}

    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    gt_products = gt.get("products", [])
    launches = stage2.get("launches", [])

    def normalize(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    def fuzzy_match(a: str, b: str) -> bool:
        na, nb = normalize(a), normalize(b)
        if not na or not nb:
            return False
        return na in nb or nb in na or na[:6] == nb[:6]

    def item_match(gt_item: dict, launch: dict) -> bool:
        gt_co = gt_item["company_name"]
        gt_prod = gt_item["product_name"]
        found_co = launch.get("company_name", "")
        found_prod = launch.get("product_name", "")
        found_title = launch.get("title", "")
        if fuzzy_match(gt_co, found_co):
            return True
        if fuzzy_match(gt_prod, found_prod):
            return True
        if fuzzy_match(gt_prod, found_co):
            return True
        ngt = normalize(gt_co)
        if len(ngt) >= 4 and ngt in normalize(found_title):
            return True
        return False

    matched = []
    missed = []

    for gt_item in gt_products:
        gt_co = gt_item["company_name"]
        gt_prod = gt_item["product_name"]
        found = None
        for launch in launches:
            if item_match(gt_item, launch):
                found = launch
                break
        if found:
            matched.append({
                "gt_company": gt_co,
                "gt_product": gt_prod,
                "found_company": found.get("company_name"),
                "found_product": found.get("product_name"),
                "gt_launch_type": gt_item.get("launch_type"),
                "found_launch_type": found.get("launch_type"),
                "gt_is_ai": gt_item.get("is_ai"),
                "found_is_ai": found.get("is_ai"),
                "source": found.get("query_source"),
            })
        else:
            missed.append({"gt_company": gt_co, "gt_product": gt_prod, "gt_source": gt_item.get("source_name")})

    recall = len(matched) / len(gt_products) if gt_products else 0
    precision = len(matched) / len(launches) if launches else 0

    # Classification accuracy on matched items
    launch_type_correct = sum(
        1 for m in matched if m["gt_launch_type"] == m["found_launch_type"]
    )
    is_ai_correct = sum(
        1 for m in matched if m["gt_is_ai"] == m["found_is_ai"]
    )

    print(f"\n  --- GT SCORING ---")
    print(f"  Recall:    {len(matched)}/{len(gt_products)} = {recall:.0%}")
    print(f"  Precision: {len(matched)}/{len(launches)} launches found")
    if matched:
        print(f"  launch_type accuracy: {launch_type_correct}/{len(matched)} = {launch_type_correct/len(matched):.0%}")
        print(f"  is_ai accuracy:       {is_ai_correct}/{len(matched)} = {is_ai_correct/len(matched):.0%}")

    print(f"\n  MATCHED ({len(matched)}):")
    for m in matched:
        lt_ok = "[OK]" if m["gt_launch_type"] == m["found_launch_type"] else "[XX]"
        ai_ok = "[OK]" if m["gt_is_ai"] == m["found_is_ai"] else "[XX]"
        print(f"    {m['gt_company']} | type:{lt_ok} ai:{ai_ok} | via {m['source']}")

    print(f"\n  MISSED ({len(missed)}):")
    for m in missed:
        print(f"    {m['gt_company']} ({m['gt_product']}) -- expected from {m['gt_source']}")

    return {
        "recall": recall,
        "precision": precision,
        "matched": matched,
        "missed": missed,
        "launch_type_accuracy": launch_type_correct / len(matched) if matched else None,
        "is_ai_accuracy": is_ai_correct / len(matched) if matched else None,
    }


# ---------------------------------------------------------------------------
# CLI & Main
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Product Launch News Pipeline")
    p.add_argument("--date", default=None, help="Run date as YYYY-MM-DD (default: today)")
    p.add_argument("--stage", type=int, choices=[1, 2], help="Run only up to this stage")
    p.add_argument("--skip-serper", action="store_true", help="Direct scrapes only (no Serper queries)")
    p.add_argument("--dry-run", action="store_true", help="Preview queries without running")
    p.add_argument("--score-only", action="store_true", help="Score existing stage2 output vs GT")
    p.add_argument("--tbs", default="qdr:d", help="Serper time filter (qdr:d=day, qdr:w=week)")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)

    stage1_file = STAGE_DIR / f"news-launches-stage1-{date_str}.json"
    stage2_file = STAGE_DIR / f"news-launches-stage2-{date_str}.json"

    print(f"\n{'='*60}")
    print(f"  PRODUCT LAUNCH NEWS PIPELINE -- {date_str}")
    print(f"  Skip Serper: {args.skip_serper} | Dry run: {args.dry_run}")
    print(f"  OpenAI: {'YES' if OPENAI_API_KEY else 'NO'}")
    print(f"{'='*60}")

    # --score-only: load existing stage2 and score
    if args.score_only:
        if not stage2_file.exists():
            print(f"\n  ERROR: stage2 file not found: {stage2_file}")
            sys.exit(1)
        stage2 = json.loads(stage2_file.read_text(encoding="utf-8"))
        print(f"\n  Loaded {len(stage2.get('launches', []))} launches from {stage2_file}")
        score_against_gt(stage2)
        return

    # --- STAGE 1: Discovery ---
    if args.stage and args.stage > 1 and stage1_file.exists():
        print(f"\n  Loading stage 1 from {stage1_file}")
        raw_results = json.loads(stage1_file.read_text(encoding="utf-8"))
    else:
        print(f"\n  STAGE 1A: DIRECT SOURCE FETCHES")
        direct = run_direct_fetches(date_str, dry_run=args.dry_run)

        if args.skip_serper:
            serper = []
            print(f"\n  STAGE 1B: SERPER SKIPPED (--skip-serper)")
        else:
            print(f"\n  STAGE 1B: SERPER SUPPLEMENT")
            serper = run_serper_queries(args.tbs, dry_run=args.dry_run)

        if args.dry_run:
            return

        raw_results = direct + serper
        print(f"\n  Stage 1 total: {len(raw_results)} raw items "
              f"({len(direct)} direct + {len(serper)} Serper)")

        stage1_file.write_text(json.dumps(raw_results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved: {stage1_file}")

    if args.stage == 1:
        print(f"\n  Done (stage 1 only). {len(raw_results)} raw items.")
        return

    # --- STAGE 2: Classify & Filter ---
    print(f"\n  STAGE 2: CLASSIFY & FILTER")
    stage2 = run_classify(raw_results)
    stage2_file.write_text(json.dumps(stage2, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Saved: {stage2_file}")

    launches = stage2.get("launches", [])
    print(f"\n  Stage 2 result: {len(launches)} launches")
    for lx in launches[:10]:
        ai_flag = "[AI]" if lx.get("is_ai") else ""
        print(f"    {lx.get('company_name', '?')} -- {lx.get('product_name', '?')} "
              f"({lx.get('launch_type', '?')}) {ai_flag}")
    if len(launches) > 10:
        print(f"    ... and {len(launches) - 10} more")

    if args.stage == 2:
        print(f"\n  Done (stage 2 only).")
        return

    # --- STAGE 3: Score against GT ---
    print(f"\n  STAGE 3: SCORE AGAINST GROUND TRUTH")
    scores = score_against_gt(stage2)

    # Write final output JSON
    output_path = OUTPUT_DIR / f"news-launches-{date_str}.json"
    output_json = {
        "date": date_str,
        "launch_count": len(launches),
        "launches": launches,
        "gt_scores": scores,
        "metadata": {
            "stage1_raw": len(raw_results),
            "stage2_deduped": len(launches),
            "generated_at": datetime.now().isoformat(),
        },
    }
    output_path.write_text(json.dumps(output_json, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Output: {output_path}")

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Launches found: {len(launches)}")
    if scores:
        print(f"  GT recall: {scores.get('recall', 0):.0%}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
