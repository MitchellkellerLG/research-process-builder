import os, json, sys, re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import requests

key = os.getenv("SPIDER_API_KEY", "")
if not key:
    print("No SPIDER_API_KEY found")
    sys.exit(1)

product_url = "https://www.producthunt.com/posts/kanwas"
print(f"Fetching: {product_url}")

resp = requests.post(
    "https://api.spider.cloud/crawl",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"url": product_url, "limit": 1, "return_format": "markdown", "render_js": True, "wait_for": {"delay": {"secs": 3, "nanos": 0}}},
    timeout=60,
)
data = resp.json()
content = data[0].get("content", "") if isinstance(data, list) and data else ""
print(f"Content length: {len(content)} chars")

# Find ALL URLs in the content
urls = re.findall(r'https?://[^\s\)\"\'<>]+', content)
external = [u for u in urls if "producthunt.com" not in u and "imgix" not in u and "ph-static" not in u and "ph-files" not in u]
print(f"\nAll external URLs ({len(external)}):")
for u in external:
    print(f"  {u}")

# Also search for "website" or "visit" context
print("\nLines containing 'visit' or 'website' or 'link':")
for line in content.split("\n"):
    low = line.lower()
    if any(w in low for w in ["visit", "website", "link", "launch"]):
        if "producthunt" not in low and "imgix" not in low and len(line.strip()) > 5:
            print(f"  {line.strip()[:200]}")
