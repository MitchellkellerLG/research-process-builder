"""
Product Hunt Daily Launch Pipeline

Fetches the PH daily leaderboard, classifies each product (new_product vs
new_feature, is_ai), and scores against ground truth.

Three stages:
  1. Fetch PH leaderboard via HTTP GET -> extract product list via GPT-4o-mini
  2. Classify each product (launch_type, is_ai) via GPT-4o-mini batch call
  3. Score against ground truth

Usage:
    py scripts/product_launch_ph_pipeline.py                     # full run, today
    py scripts/product_launch_ph_pipeline.py --date 2026-05-04   # specific date
    py scripts/product_launch_ph_pipeline.py --stage 1            # discovery only
    py scripts/product_launch_ph_pipeline.py --dry-run            # preview URL, no API calls
    py scripts/product_launch_ph_pipeline.py --score-only         # score stage2 output vs GT
"""

import json
import sys
import os
import re
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Env + paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
STAGE_DIR = OUTPUT_DIR / "stages"

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(PROJECT_DIR.parent / ".env", override=False)
load_dotenv(Path.home() / ".env", override=False)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

GT_PATH = PROJECT_DIR / "processes" / "find-product-launches-ph" / "ground_truth.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _openai_chat(messages: list[dict], model: str = "gpt-4o-mini") -> str:
    """Single OpenAI chat completion. Returns content string."""
    import urllib.request
    payload = json.dumps({"model": model, "messages": messages}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


def _parse_json_response(raw: str) -> dict | list:
    """Strip markdown fences and parse JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())


def build_ph_url(date_str: str) -> str:
    """Build PH leaderboard URL with no leading zeros on month/day."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"https://www.producthunt.com/leaderboard/daily/{d.year}/{d.month}/{d.day}"


# ---------------------------------------------------------------------------
# Stage 1: Fetch leaderboard
# ---------------------------------------------------------------------------

def stage1_fetch(date_str: str) -> dict:
    """Fetch PH leaderboard and extract products via GPT-4o-mini."""
    url = build_ph_url(date_str)
    print(f"\n[Stage 1] Fetching {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    page_content = None

    # Serper scrape is primary -- PH pages are JS-rendered, raw HTML misses products
    if SERPER_API_KEY:
        try:
            serper_resp = requests.post(
                "https://google.serper.dev/scrape",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"url": url},
                timeout=30,
            )
            serper_resp.raise_for_status()
            text = serper_resp.json().get("text", "")
            if len(text) > 500:
                page_content = text[:80000]
                print(f"  Serper scrape: {len(text)} chars")
        except Exception as e:
            print(f"  Serper scrape failed: {e} -- trying direct fetch")

    # Direct fetch fallback (may miss products due to JS rendering)
    if page_content is None:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200 and len(resp.text) > 5000:
                page_content = resp.text[:80000]
                print(f"  Direct fetch: {len(resp.text)} chars (JS-rendered, may miss products)")
            else:
                print(f"  Direct fetch returned {resp.status_code} / {len(resp.text)} chars")
        except Exception as e:
            print(f"  Direct fetch failed: {e}")

    if page_content is None:
        raise RuntimeError("Both Serper scrape and direct fetch failed -- cannot continue")

    print("  Extracting products via GPT-4o-mini...")
    raw = _openai_chat([
        {"role": "system", "content": (
            "You are extracting structured product data from a Product Hunt leaderboard page. "
            "Extract every ranked product. Return JSON only -- no commentary."
        )},
        {"role": "user", "content": (
            f"Page content:\n{page_content}\n\n"
            "Extract all ranked products. For each, return:\n"
            '{"rank": <int>, "product_name": "<string>", "tagline": "<string>", '
            '"score": <int>, "ph_url": "<full PH URL>", '
            '"categories": ["<cat>", ...], "maker_website": "<URL or null>"}\n\n'
            'Return as JSON: {"products": [...]}\n'
            'If the leaderboard has not posted yet, return {"products": [], "error": "leaderboard_not_posted"}.'
        )},
    ])

    parsed = _parse_json_response(raw)
    products = parsed.get("products", [])
    error = parsed.get("error")

    if error == "leaderboard_not_posted":
        print("  PH leaderboard not yet posted for this date.")
        return {"date": date_str, "leaderboard_url": url, "products": [], "error": error}

    if not products:
        print("  WARNING: empty product list with no error -- flag for manual review")
        return {"date": date_str, "leaderboard_url": url, "products": [], "error": "unexpected_empty"}

    # Kill list: skip score < 10
    before = len(products)
    products = [p for p in products if (p.get("score") or 0) >= 10]
    if len(products) < before:
        print(f"  Dropped {before - len(products)} products with score < 10")

    print(f"  Extracted {len(products)} products")
    for p in products:
        print(f"    #{p.get('rank')} {p.get('product_name')} (score {p.get('score')})")

    return {"date": date_str, "leaderboard_url": url, "products": products}


# ---------------------------------------------------------------------------
# Stage 2b: Product page launch count
# ---------------------------------------------------------------------------

_PH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _posts_count_from_slug(slug: str) -> int | None:
    """Fetch a PH product page by slug and extract postsCount from raw HTML."""
    url = f"https://www.producthunt.com/products/{slug}"
    try:
        resp = requests.get(url, headers=_PH_HEADERS, timeout=15)
        if resp.status_code != 200 or len(resp.text) < 10000:
            return None
        m = re.search(r'postsCount[\":\s]+(\d+)', resp.text)
        if m:
            count = int(m.group(1))
            return count if count > 0 else None
        return None
    except Exception:
        return None


def _serper_find_product_slug(product_name: str) -> str | None:
    """
    Use Serper search API to find the canonical PH product page slug.
    Costs ~$0.0075/call. Only invoked when direct slug fetch fails.
    """
    if not SERPER_API_KEY:
        return None
    query = f'site:producthunt.com/products "{product_name}"'
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 3},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        for r in resp.json().get("organic", []):
            m = re.match(r"https://www\.producthunt\.com/products/([^/?#]+)", r.get("link", ""))
            if m:
                return m.group(1)
        return None
    except Exception:
        return None


def _fetch_launch_count(product: dict) -> tuple[int, int | None]:
    """
    Resolve launch count for a single product. Returns (rank, launch_count_or_None).

    Strategy:
    1. Extract slug from ph_url (already in /products/ format from stage1).
    2. Try postsCount regex on that slug.
    3. If 404 or no count, try slug variations (strip -N suffix, strip -for-X).
    4. If still no count, fall back to Serper search to find canonical slug.
    """
    rank = product.get("rank")
    ph_url = product.get("ph_url", "")
    product_name = product.get("product_name", "")

    # Extract slug from URL
    if "/products/" in ph_url:
        slug = ph_url.rstrip("/").split("/products/")[-1]
    elif "/posts/" in ph_url:
        slug = ph_url.rstrip("/").split("/posts/")[-1]
    else:
        return rank, None

    # Try 1: exact slug
    count = _posts_count_from_slug(slug)
    if count is not None:
        return rank, count

    # Try 2: strip trailing -N (e.g., flowly-9 -> flowly)
    stripped = re.sub(r"-\d+$", "", slug)
    if stripped != slug:
        count = _posts_count_from_slug(stripped)
        if count is not None:
            return rank, count

    # Try 3: strip -for-X suffix (e.g., sleek-analytics-for-ios -> sleek-analytics)
    for_stripped = re.sub(r"-for-[a-z]+$", "", slug)
    if for_stripped not in (slug, stripped):
        count = _posts_count_from_slug(for_stripped)
        if count is not None:
            return rank, count

    # Try 4: Serper search for canonical product slug
    canonical_slug = _serper_find_product_slug(product_name)
    if canonical_slug and canonical_slug not in (slug, stripped, for_stripped):
        count = _posts_count_from_slug(canonical_slug)
        if count is not None:
            return rank, count

    return rank, None


def stage2b_launch_counts(products: list[dict]) -> dict[int, int | None]:
    """
    Fetch launch counts for all products in parallel.
    Returns dict of {rank: launch_count_or_None}.
    """
    print(f"\n[Stage 2b] Fetching product pages for {len(products)} products...")
    results: dict[int, int | None] = {}

    def fetch_with_delay(product, delay):
        time.sleep(delay)
        return _fetch_launch_count(product)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_with_delay, p, i * 0.5): p
            for i, p in enumerate(products)
        }
        for future in as_completed(futures):
            rank, count = future.result()
            results[rank] = count
            product = futures[future]
            count_display = str(count) if count is not None else "?"
            print(f"  #{rank:2} {product.get('product_name')}: {count_display} launch(es)")

    return results


# ---------------------------------------------------------------------------
# Stage 2: Classify
# ---------------------------------------------------------------------------

def stage2_classify(stage1: dict) -> dict:
    """
    Classify all products in one GPT batch call.
    Determines launch_type (new_product | new_feature) and is_ai.

    NOTE: The process spec calls for fetching each product page to count launches.
    In this pipeline we use a single batch classification call on the leaderboard
    data (name, tagline, categories) for simplicity and cost. launch_count will
    be null -- requires per-product page fetch if needed (future stage 2b).
    """
    products = stage1.get("products", [])
    if not products:
        return {**stage1, "products": [], "stage2_note": "no products to classify"}

    print(f"\n[Stage 2] Classifying {len(products)} products via GPT-4o-mini batch...")

    # Build compact product list for the prompt
    product_lines = []
    for p in products:
        cats = ", ".join(p.get("categories") or [])
        product_lines.append(
            f"rank={p['rank']} | name={p['product_name']} | "
            f"tagline={p.get('tagline','')} | categories={cats}"
        )
    product_block = "\n".join(product_lines)

    raw = _openai_chat([
        {"role": "system", "content": (
            "You classify Product Hunt launches. For each product, determine launch_type and is_ai. "
            "Return JSON only -- no commentary."
        )},
        {"role": "user", "content": (
            f"Products (from leaderboard, no product page data available):\n{product_block}\n\n"
            "For each product, classify:\n"
            "1. launch_type: 'new_product' if this appears to be a first-time PH launch based on product name/tagline/categories. "
            "'new_feature' if the product name or tagline strongly implies it is an addition/update to an existing product "
            "(e.g. 'v2', 'for X product', OpenAI products, products with version suffixes). "
            "When uncertain from leaderboard data alone, default to 'new_product'.\n"
            "2. is_ai: true if ANY apply: categories contain 'AI' prefix or 'Artificial Intelligence', "
            "tagline contains: AI, agent, LLM, GPT, Claude, automated, intelligent, generative. "
            "false if no explicit AI signal.\n"
            "3. classification_reasoning: 1 sentence.\n\n"
            'Return: {"classifications": [{"rank": <int>, "product_name": "<str>", '
            '"launch_type": "new_product|new_feature", "is_ai": true|false, '
            '"classification_reasoning": "<str>", "launch_count": null}]}'
        )},
    ])

    parsed = _parse_json_response(raw)
    classifications = {c["rank"]: c for c in parsed.get("classifications", [])}

    enriched_products = []
    for p in products:
        rank = p.get("rank")
        cls = classifications.get(rank, {})
        enriched_products.append({
            **p,
            "launch_type": cls.get("launch_type", "unknown"),
            "is_ai": cls.get("is_ai", False),
            "classification_reasoning": cls.get("classification_reasoning", ""),
            "launch_count": cls.get("launch_count"),
        })

    print(f"  Classified {len(enriched_products)} products")
    for p in enriched_products:
        ai_flag = "AI" if p["is_ai"] else "  "
        print(f"    #{p['rank']:2} [{p['launch_type']:<12}] [{ai_flag}] {p['product_name']}")

    # Stage 2b: override launch_type using actual PH launch count
    launch_counts = stage2b_launch_counts(enriched_products)
    overrides = 0
    for p in enriched_products:
        rank = p.get("rank")
        count = launch_counts.get(rank)
        p["launch_count"] = count
        if count is not None:
            if count > 1 and p["launch_type"] != "new_feature":
                p["launch_type"] = "new_feature"
                p["classification_reasoning"] += f" [2b: {count} launches on PH -> new_feature]"
                overrides += 1
            elif count == 1 and p["launch_type"] != "new_product":
                p["launch_type"] = "new_product"
                p["classification_reasoning"] += f" [2b: 1 launch on PH -> new_product]"
                overrides += 1

    print(f"\n  Stage 2b overrides: {overrides}")
    print(f"  Final classifications:")
    for p in enriched_products:
        ai_flag = "AI" if p["is_ai"] else "  "
        count_str = str(p.get("launch_count")) if p.get("launch_count") is not None else "?"
        print(f"    #{p['rank']:2} [{p['launch_type']:<12}] [{ai_flag}] (launches={count_str}) {p['product_name']}")

    return {**stage1, "products": enriched_products}


# ---------------------------------------------------------------------------
# Stage 3: Score against ground truth
# ---------------------------------------------------------------------------

def stage3_score(stage2: dict, gt_path: Path = GT_PATH) -> dict:
    """Compare stage2 output against ground truth. Print recall/precision/accuracy."""
    print(f"\n[Stage 3] Scoring against {gt_path.name}...")

    if not gt_path.exists():
        print(f"  WARNING: ground truth not found at {gt_path}")
        return {"score_error": "gt_not_found"}

    gt = json.loads(gt_path.read_text())
    gt_list = gt.get("products", [])
    pipeline_list = stage2.get("products", [])

    def normalize(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    def fuzzy_match(gt_p: dict, pip_p: dict) -> bool:
        gt_name = normalize(gt_p["product_name"])
        pip_name = normalize(pip_p["product_name"])
        if gt_name in pip_name or pip_name in gt_name:
            return True
        if gt_name[:6] == pip_name[:6] and len(gt_name) >= 4:
            return True
        pip_tagline = normalize(pip_p.get("tagline", ""))
        if gt_name in pip_tagline:
            return True
        return False

    matched_pairs = []
    matched_gt_idx = set()
    matched_pip_idx = set()
    for gi, gt_p in enumerate(gt_list):
        for pi, pip_p in enumerate(pipeline_list):
            if pi in matched_pip_idx:
                continue
            if fuzzy_match(gt_p, pip_p):
                matched_pairs.append((gt_p, pip_p))
                matched_gt_idx.add(gi)
                matched_pip_idx.add(pi)
                break

    missed = [gt_list[i] for i in range(len(gt_list)) if i not in matched_gt_idx]
    extra = [pipeline_list[i] for i in range(len(pipeline_list)) if i not in matched_pip_idx]

    recall = len(matched_pairs) / len(gt_list) if gt_list else 0
    precision = len(matched_pairs) / len(pipeline_list) if pipeline_list else 0

    launch_type_correct = 0
    is_ai_correct = 0
    classification_results = []

    for gt_p, pip_p in matched_pairs:

        lt_ok = gt_p.get("launch_type") == pip_p.get("launch_type")
        ai_ok = gt_p.get("is_ai") == pip_p.get("is_ai")

        if lt_ok:
            launch_type_correct += 1
        if ai_ok:
            is_ai_correct += 1

        classification_results.append({
            "product_name": gt_p["product_name"],
            "launch_type_gt": gt_p.get("launch_type"),
            "launch_type_pipeline": pip_p.get("launch_type"),
            "launch_type_ok": lt_ok,
            "is_ai_gt": gt_p.get("is_ai"),
            "is_ai_pipeline": pip_p.get("is_ai"),
            "is_ai_ok": ai_ok,
        })

    n_matched = len(matched_pairs)
    lt_acc = launch_type_correct / n_matched if n_matched else 0
    ai_acc = is_ai_correct / n_matched if n_matched else 0

    print(f"\n  === Score Results ===")
    print(f"  GT products:          {len(gt_list)}")
    print(f"  Pipeline products:    {len(pipeline_list)}")
    print(f"  Matched:              {n_matched}")
    print(f"  Recall:               {recall:.0%}  ({n_matched}/{len(gt_list)})")
    print(f"  Precision:            {precision:.0%}  ({n_matched}/{len(pipeline_list)})")
    print(f"  launch_type accuracy: {lt_acc:.0%}  ({launch_type_correct}/{n_matched})")
    print(f"  is_ai accuracy:       {ai_acc:.0%}  ({is_ai_correct}/{n_matched})")

    if missed:
        print(f"\n  Missed (in GT, not found):")
        for p in missed:
            print(f"    - {p['product_name']}")

    if extra:
        print(f"\n  Extra (found, not in GT):")
        for p in extra:
            print(f"    + {p['product_name']}")

    if classification_results:
        print(f"\n  Per-product classification:")
        for r in classification_results:
            lt_icon = "OK" if r["launch_type_ok"] else "XX"
            ai_icon = "OK" if r["is_ai_ok"] else "XX"
            print(
                f"    {r['product_name']}: launch_type [{lt_icon}] "
                f"({r['launch_type_gt']} vs {r['launch_type_pipeline']})  "
                f"is_ai [{ai_icon}] ({r['is_ai_gt']} vs {r['is_ai_pipeline']})"
            )

    return {
        "recall": recall,
        "precision": precision,
        "launch_type_accuracy": lt_acc,
        "is_ai_accuracy": ai_acc,
        "matched": n_matched,
        "missed": sorted(missed),
        "extra": sorted(extra),
        "classification_results": classification_results,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Product Hunt daily launch pipeline")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3],
                        help="Run only this stage (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview URL and exit -- no API calls")
    parser.add_argument("--score-only", action="store_true",
                        help="Load existing stage2 output and score against GT")
    args = parser.parse_args()

    date_str = args.date
    OUTPUT_DIR.mkdir(exist_ok=True)
    STAGE_DIR.mkdir(exist_ok=True)

    stage1_path = STAGE_DIR / f"ph-launches-stage1-{date_str}.json"
    stage2_path = STAGE_DIR / f"ph-launches-stage2-{date_str}.json"

    # Dry-run
    if args.dry_run:
        url = build_ph_url(date_str)
        print(f"[dry-run] Stage 1 URL: {url}")
        print(f"[dry-run] Stage 1 output: {stage1_path}")
        print(f"[dry-run] Stage 2 output: {stage2_path}")
        return

    # Score-only: load existing stage2 and score
    if args.score_only:
        if not stage2_path.exists():
            print(f"ERROR: stage2 output not found: {stage2_path}")
            sys.exit(1)
        stage2 = json.loads(stage2_path.read_text())
        stage3_score(stage2)
        return

    # --- Stage 1 ---
    if args.stage is None or args.stage == 1:
        # Load from cache if exists
        if stage1_path.exists() and args.stage != 1:
            print(f"[Stage 1] Loading cached: {stage1_path.name}")
            stage1 = json.loads(stage1_path.read_text())
        else:
            stage1 = stage1_fetch(date_str)
            stage1_path.write_text(json.dumps(stage1, indent=2))
            print(f"  Saved: {stage1_path}")

        if stage1.get("error") or not stage1.get("products"):
            print("Stage 1 failed or empty -- stopping.")
            return
        if args.stage == 1:
            return

    # --- Stage 2 ---
    if args.stage is None or args.stage == 2:
        if args.stage == 2:
            if not stage1_path.exists():
                print(f"ERROR: stage1 output not found: {stage1_path}")
                sys.exit(1)
            stage1 = json.loads(stage1_path.read_text())
        stage2 = stage2_classify(stage1)
        stage2_path.write_text(json.dumps(stage2, indent=2))
        print(f"  Saved: {stage2_path}")
        if args.stage == 2:
            return

    # --- Stage 3 ---
    if args.stage is None or args.stage == 3:
        if args.stage == 3:
            if not stage2_path.exists():
                print(f"ERROR: stage2 output not found: {stage2_path}")
                sys.exit(1)
            stage2 = json.loads(stage2_path.read_text())
        score = stage3_score(stage2)

    print(f"\nDone. Date: {date_str}")


if __name__ == "__main__":
    main()
