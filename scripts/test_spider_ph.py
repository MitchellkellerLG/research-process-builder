import os, json, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import requests

key = os.getenv("SPIDER_API_KEY", "")
if not key:
    print("No SPIDER_API_KEY found")
    sys.exit(1)

print(f"Key loaded, length: {len(key)}")

url = "https://www.producthunt.com/leaderboard/daily/2026/5/6"
print(f"Fetching: {url}")

resp = requests.post(
    "https://api.spider.cloud/crawl",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={
        "url": url,
        "limit": 1,
        "return_format": "markdown",
        "render_js": True,
        "wait_for": {"delay": {"secs": 3, "nanos": 0}},
    },
    timeout=60,
)

print(f"Status: {resp.status_code}")
data = resp.json()

content = ""
if isinstance(data, list) and len(data) > 0:
    content = data[0].get("content", "")
elif isinstance(data, dict):
    if "error" in data:
        print(f"Error: {data['error']}")
    content = data.get("content", "")

print(f"Content length: {len(content)} chars")
if content:
    print(content[:3000].encode("utf-8", errors="replace").decode("utf-8"))
else:
    print("No content returned")
    print(f"Raw response: {json.dumps(data)[:500]}")
