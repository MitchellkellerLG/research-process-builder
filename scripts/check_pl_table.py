"""Quick check: what's in product_launches table."""
import os, requests, json
from pathlib import Path
from dotenv import dotenv_values

env = {
    **dotenv_values(Path(__file__).parent.parent.parent / ".env"),
    **dotenv_values(Path(__file__).parent.parent / ".env"),
    **os.environ,
}
url = env.get("SUPABASE_PROJECT_URL") or env.get("SUPABASE_URL", "")
key = env.get("SUPABASE_KEY") or env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("SUPABASE_ANON_KEY", "")

if not url or not key:
    print("SUPABASE not configured")
    exit(1)

h = {"apikey": key, "Authorization": f"Bearer {key}"}

# Count total
r = requests.get(f"{url}/rest/v1/product_launches?select=id", headers={**h, "Prefer": "count=exact"}, timeout=10)
print(f"Total rows: {r.headers.get('content-range', '?')}")

# Recent rows
r = requests.get(
    f"{url}/rest/v1/product_launches?select=id,company_name,source,discovered_date,launch_type,is_ai&order=created_at.desc&limit=10",
    headers=h, timeout=10,
)
print(f"Status: {r.status_code}")
rows = r.json() if r.ok else r.text
print(json.dumps(rows, indent=2)[:2000])
