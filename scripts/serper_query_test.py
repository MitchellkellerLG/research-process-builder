"""Test query patterns against Serper API for product launch detection.
Usage: py scripts/serper_query_test.py
"""
import os, json, requests
from pathlib import Path
from dotenv import load_dotenv

_script_dir = Path(__file__).parent
load_dotenv(_script_dir.parent / ".env")
load_dotenv(_script_dir.parent.parent / ".env", override=False)
load_dotenv(Path.home() / ".env", override=False)

key = os.environ.get('SERPER_API_KEY', '')
if not key:
    print('ERROR: SERPER_API_KEY not in environment')
    exit(1)

print(f'Serper key found: {key[:8]}...')

queries = [
    ('Q1_techcrunch_launched', '"launched" OR "announces" new product site:techcrunch.com'),
    ('Q2_show_hn', '"Show HN" site:news.ycombinator.com 2026'),
    ('Q3_ai_startup_may2026', 'AI startup "launches" OR "announces" OR "introduces" May 2026'),
    ('Q4_product_launch_may2026', '"new feature" OR "product launch" startup technology May 2026'),
    ('Q5_now_available', '"now available" OR "introducing" software product 2026'),
    ('Q6_techcrunch_may4', 'site:techcrunch.com product launch May 4 2026'),
    ('Q7_control', 'DoorDash OR Ouster OR Retroguard OR Airbyte launch 2026'),
]

results = {}
for qid, q in queries:
    r = requests.post(
        'https://google.serper.dev/search',
        headers={'X-API-KEY': key, 'Content-Type': 'application/json'},
        json={'q': q, 'num': 20, 'tbs': 'qdr:w'},
        timeout=15
    )
    data = r.json() if r.ok else {'error': r.text}
    organic = data.get('organic', [])
    results[qid] = {'query': q, 'status': r.status_code, 'hits': len(organic), 'organic': organic}
    print(f'{qid}: status={r.status_code}, hits={len(organic)}')

out = 'data/serper_query_test_raw.json'
with open(out, 'w') as f:
    json.dump(results, f, indent=2)
print(f'\nSaved raw results to {out}')
