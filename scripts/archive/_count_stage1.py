import json, sys
with open('output/stages/stage1-2026-04-26.json', 'rb') as f:
    d = json.loads(f.read().decode('utf-8'))
print(f'items: {len(d)}')
print('sample keys:', list(d[0].keys()))
