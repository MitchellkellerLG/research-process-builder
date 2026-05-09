"""
Test Clay webhook + callback roundtrip.
POSTs a real gaming studio to Clay, then polls Worker logs via wrangler tail (run separately).
"""
import json
import requests
import uuid
import time

CLAY_WEBHOOK_URL = "https://api.clay.com/v3/sources/webhook/pull-in-data-from-a-webhook-1bea419a-3bb6-4442-9893-0fb7e8c85e62"
CALLBACK_URL = "https://clay-game-callback.leadgrowai.workers.dev"

TEST_COMPANY = {
    "Company Name": "Rebel Wolves",
    "Company Website": "rebelwolves.com",
    "signal_type": "game_announcement",
    "game_title": "The Blood of Dawnwalker",
    "source_url": "https://www.ign.com/articles/rebel-wolves-blood-of-dawnwalker",
    "date_detected": "2026-05-06",
}

token = str(uuid.uuid4())
payload = {
    "_callback_id": token,
    "_callback_url": CALLBACK_URL,
    **TEST_COMPANY,
}

print(f"Token: {token}")
print(f"Payload:\n{json.dumps(payload, indent=2)}")
print(f"\nPOSTing to Clay...")

resp = requests.post(CLAY_WEBHOOK_URL, json=payload, timeout=15)
print(f"Clay response: {resp.status_code}")
print(resp.text[:500] if resp.text else "(empty)")
print(f"\nWaiting for Clay to enrich + callback...")
print(f"Run in another terminal to watch Worker logs:")
print(f"  cd trigger && npx wrangler tail clay-game-callback --format pretty")
