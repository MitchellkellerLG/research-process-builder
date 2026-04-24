"""
Backfill article_text for existing funding_discoveries rows.

Fetches rows where article_text is null, scrapes via Spider API,
and PATCHes the text back to Supabase.

Usage:
    py scripts/backfill_article_text.py
    py scripts/backfill_article_text.py --dry-run
    py scripts/backfill_article_text.py --limit 10
"""

import os
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error

SUPABASE_URL = os.environ.get("SUPABASE_PROJECT_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))
SPIDER_API_KEY = os.environ.get("SPIDER_API_KEY", "")
TABLE = "funding_discoveries"


def supabase_headers(prefer: str = "") -> dict:
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def fetch_rows_missing_text(limit: int) -> list[dict]:
    url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE}"
        f"?article_text=is.null&select=id,company_name,source_url"
        f"&order=id.asc&limit={limit}"
    )
    req = urllib.request.Request(url, headers=supabase_headers())
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def scrape_article(source_url: str) -> str | None:
    if SPIDER_API_KEY:
        try:
            payload = json.dumps({"url": source_url, "limit": 1, "return_format": "markdown"}).encode()
            req = urllib.request.Request(
                "https://api.spider.cloud/crawl",
                data=payload,
                headers={
                    "Authorization": f"Bearer {SPIDER_API_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read())
            content = ""
            if isinstance(data, list) and data:
                content = data[0].get("content", "")
            elif isinstance(data, dict):
                content = data.get("content", "")
            if len(content) > 200:
                return content[:15000]
        except Exception as e:
            print(f"    Spider failed: {e}")

    try:
        req = urllib.request.Request(
            source_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LeadGrow/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        if len(text) > 200:
            return text[:15000]
    except Exception as e:
        print(f"    Direct fetch failed: {e}")

    return None


def patch_article_text(row_id: int, text: str) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{row_id}"
    payload = json.dumps({"article_text": text}).encode()
    req = urllib.request.Request(
        url, data=payload, headers=supabase_headers(), method="PATCH"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"    PATCH failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Backfill article_text in funding_discoveries")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but don't write")
    parser.add_argument("--limit", type=int, default=100, help="Max rows to process")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY env vars required")
        return

    rows = fetch_rows_missing_text(args.limit)
    print(f"Found {len(rows)} rows missing article_text")

    success = 0
    failed = 0
    for i, row in enumerate(rows):
        print(f"[{i+1}/{len(rows)}] {row['company_name']} — {row['source_url'][:60]}...")
        text = scrape_article(row["source_url"])
        if not text:
            print("    SKIP: no content retrieved")
            failed += 1
            continue

        if args.dry_run:
            print(f"    DRY RUN: would write {len(text)} chars")
            success += 1
        else:
            if patch_article_text(row["id"], text):
                print(f"    OK: {len(text)} chars")
                success += 1
            else:
                failed += 1

        time.sleep(1)

    print(f"\nDone: {success} backfilled, {failed} failed, {len(rows)} total")


if __name__ == "__main__":
    main()
