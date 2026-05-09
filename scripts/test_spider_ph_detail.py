import os, json, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import requests

key = os.getenv("SPIDER_API_KEY", "")
if not key:
    print("No SPIDER_API_KEY found")
    sys.exit(1)

# Test 1: Check if leaderboard content has maker_website links
print("=== Leaderboard content check ===")
url = "https://www.producthunt.com/leaderboard/daily/2026/5/6"
resp = requests.post(
    "https://api.spider.cloud/crawl",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"url": url, "limit": 1, "return_format": "markdown", "render_js": True, "wait_for": {"delay": {"secs": 3, "nanos": 0}}},
    timeout=60,
)
data = resp.json()
content = data[0].get("content", "") if isinstance(data, list) and data else ""

# Search for external links (maker websites)
lines_with_links = [l for l in content.split("\n") if "http" in l and "producthunt.com" not in l and "imgix" not in l and "ph-static" not in l]
print(f"External links found in leaderboard: {len(lines_with_links)}")
for l in lines_with_links[:10]:
    print(f"  {l[:200]}")

print()

# Test 2: Fetch a single product page to see if website is there
print("=== Product page detail check (Kanwas) ===")
product_url = "https://www.producthunt.com/posts/kanwas"
resp2 = requests.post(
    "https://api.spider.cloud/crawl",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"url": product_url, "limit": 1, "return_format": "markdown", "render_js": True, "wait_for": {"delay": {"secs": 3, "nanos": 0}}},
    timeout=60,
)
data2 = resp2.json()
content2 = data2[0].get("content", "") if isinstance(data2, list) and data2 else ""
print(f"Product page content length: {len(content2)} chars")

# Look for website link
for line in content2.split("\n"):
    low = line.lower()
    if any(w in low for w in ["visit", "website", "getkanwas", "kanwas.com", "kanwas.io", "kanwas.ai", ".com", ".io", ".ai"]):
        if "producthunt" not in low and "imgix" not in low:
            print(f"  {line[:200]}")
