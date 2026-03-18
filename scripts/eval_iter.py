"""Quick eval script for iteration comparison."""
import json, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from gt_evaluator import run_evaluation

data = run_evaluation()
cats = {}
for e in data:
    cat = e['category_id']
    if cat not in cats:
        cats[cat] = {'scores': [], 'variants': {}}
    cats[cat]['scores'].append(e['gt_score'])
    vid = e.get('variant_id', 'unknown')
    if vid not in cats[cat]['variants']:
        cats[cat]['variants'][vid] = []
    cats[cat]['variants'][vid].append(e['gt_score'])

print(f"Total evaluations: {len(data)}")
print()
print("=== ITER2 RESULTS ===")
print()

best_per_cat = {}
for cat in sorted(cats, key=lambda c: sum(cats[c]['scores'])/len(cats[c]['scores'])):
    scores = cats[cat]['scores']
    avg = sum(scores)/len(scores)

    best_overall = ('none', 0)
    best_ch2 = ('none', 0)
    for vid, vs in sorted(cats[cat]['variants'].items()):
        va = sum(vs)/len(vs)
        if va > best_overall[1]:
            best_overall = (vid, va)
        if vid.startswith('ch2_') and va > best_ch2[1]:
            best_ch2 = (vid, va)

    best_per_cat[cat] = best_overall[1]
    has_ch2 = any(v.startswith('ch2_') for v in cats[cat]['variants'])
    if has_ch2:
        delta = best_ch2[1] - best_overall[1]
        is_new_best = delta >= 0 and best_ch2[0] != 'none'
        status = 'NEW BEST' if is_new_best else 'no beat'
        print(f"{cat} (avg={avg:.3f}):")
        print(f"  Best overall: {best_overall[0]:<35} {best_overall[1]:.3f}")
        if best_ch2[0] != 'none':
            print(f"  Best ch2:     {best_ch2[0]:<35} {best_ch2[1]:.3f} ({status})")
        for vid in sorted(cats[cat]['variants']):
            vs = cats[cat]['variants'][vid]
            va = sum(vs)/len(vs)
            if vid.startswith('ch2_'):
                marker = ' ** NEW'
            elif vid.startswith('ch1_'):
                marker = ' * W1'
            else:
                marker = ''
            print(f"    {vid:<35} {va:.3f} n={len(vs)}{marker}")
        print()

print("=== BEST-PER-CATEGORY ===")
total = 0
for cat in sorted(best_per_cat):
    total += best_per_cat[cat]
    print(f"  {cat:<30} {best_per_cat[cat]:.3f}")
mean = total / len(best_per_cat)
print(f"  MEAN:                        {mean:.3f}")
