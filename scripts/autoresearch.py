"""
Autoresearch — Baseline management for the Karpathy-style optimization loop.

Saves GT score snapshots, compares current vs baseline, tracks improvement history.
The loop itself is Claude Code (the agent reads research_prompt.md and iterates).
This script is the measurement infrastructure — Karpathy's prepare.py equivalent.

Usage:
    py scripts/autoresearch.py --save-baseline           # snapshot current GT scores
    py scripts/autoresearch.py --save-baseline my_name   # named baseline
    py scripts/autoresearch.py --compare                  # compare current vs latest baseline
    py scripts/autoresearch.py --compare my_name          # compare vs named baseline
    py scripts/autoresearch.py --history                  # show all baselines over time
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
BASELINES_DIR = PROJECT_DIR / "baselines"

# Import gt_evaluator
sys.path.insert(0, str(SCRIPT_DIR))
from gt_evaluator import run_evaluation


def compute_scores(evaluations):
    """Compute per-category and per-variant GT scores from evaluations."""
    by_category = defaultdict(list)
    by_variant = defaultdict(list)

    for e in evaluations:
        cat = e["category_id"]
        variant = f"{cat}/{e['variant_id']}"
        by_category[cat].append(e)
        by_variant[variant].append(e)

    categories = {}
    for cat_id, evals in by_category.items():
        gt_avg = sum(e["gt_score"] for e in evals) / len(evals)
        auto_avg = sum(e["auto_score"] / 5.0 for e in evals) / len(evals)
        categories[cat_id] = {
            "gt_avg": round(gt_avg, 4),
            "auto_avg": round(auto_avg, 4),
            "n": len(evals),
        }

    variants = {}
    for var_id, evals in by_variant.items():
        gt_avg = sum(e["gt_score"] for e in evals) / len(evals)
        variants[var_id] = {
            "gt_avg": round(gt_avg, 4),
            "n": len(evals),
        }

    overall_gt = sum(e["gt_score"] for e in evaluations) / len(evaluations) if evaluations else 0
    overall_auto = sum(e["auto_score"] / 5.0 for e in evaluations) / len(evaluations) if evaluations else 0

    return {
        "overall_gt_mean": round(overall_gt, 4),
        "overall_auto_mean": round(overall_auto, 4),
        "total_evaluations": len(evaluations),
        "categories": categories,
        "per_variant": variants,
    }


def compute_correlation(x_vals, y_vals):
    """Pearson correlation coefficient."""
    n = len(x_vals)
    if n < 3:
        return 0.0
    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    den_x = sum((x - x_mean) ** 2 for x in x_vals) ** 0.5
    den_y = sum((y - y_mean) ** 2 for y in y_vals) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return round(num / (den_x * den_y), 4)


def save_baseline(name=None):
    """Save current GT scores as a named baseline."""
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)

    evaluations = run_evaluation()
    if not evaluations:
        print("ERROR: No evaluations to save. Check ground truth files.")
        return

    scores = compute_scores(evaluations)

    # Compute Pearson r
    auto_vals = [e["auto_score"] / 5.0 for e in evaluations]
    gt_vals = [e["gt_score"] for e in evaluations]
    pearson_r = compute_correlation(auto_vals, gt_vals)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    baseline = {
        "timestamp": timestamp,
        "name": name or timestamp.replace(":", "-"),
        "pearson_r": pearson_r,
        **scores,
    }

    filename = f"{name or timestamp.replace(':', '-')}.json"
    filepath = BASELINES_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)

    print(f"Baseline saved: {filepath}")
    print(f"  Overall GT mean: {scores['overall_gt_mean']:.4f}")
    print(f"  Overall Auto mean: {scores['overall_auto_mean']:.4f}")
    print(f"  Pearson r: {pearson_r}")
    print(f"  Evaluations: {scores['total_evaluations']}")
    print(f"  Categories: {len(scores['categories'])}")
    print(f"  Variants: {len(scores['per_variant'])}")

    return baseline


def load_baseline(name=None):
    """Load a baseline by name, or the most recent one."""
    if not BASELINES_DIR.exists():
        return None

    if name:
        filepath = BASELINES_DIR / f"{name}.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    # Find most recent
    files = sorted(BASELINES_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def compare_baseline(name=None):
    """Compare current GT scores against a saved baseline."""
    baseline = load_baseline(name)
    if not baseline:
        print("ERROR: No baseline found. Run --save-baseline first.")
        return

    evaluations = run_evaluation()
    if not evaluations:
        print("ERROR: No evaluations to compare.")
        return

    current = compute_scores(evaluations)

    print("=" * 80)
    print(f"COMPARISON vs baseline: {baseline.get('name', 'unknown')}")
    print(f"Baseline timestamp: {baseline['timestamp']}")
    print("=" * 80)

    # Overall comparison
    gt_delta = current["overall_gt_mean"] - baseline["overall_gt_mean"]
    auto_delta = current["overall_auto_mean"] - baseline["overall_auto_mean"]
    arrow = "^" if gt_delta > 0 else "v" if gt_delta < 0 else "="

    print(f"\n{'Metric':<25} {'Baseline':>10} {'Current':>10} {'Delta':>10}")
    print("-" * 60)
    print(f"{'GT Mean':<25} {baseline['overall_gt_mean']:>10.4f} {current['overall_gt_mean']:>10.4f} {gt_delta:>+10.4f} {arrow}")
    print(f"{'Auto Mean':<25} {baseline['overall_auto_mean']:>10.4f} {current['overall_auto_mean']:>10.4f} {auto_delta:>+10.4f}")
    print(f"{'Evaluations':<25} {baseline['total_evaluations']:>10} {current['total_evaluations']:>10}")

    # Per-category comparison
    print(f"\n{'Category':<30} {'Base GT':>8} {'Curr GT':>8} {'Delta':>8} {'Verdict':>12}")
    print("-" * 72)

    improved = []
    regressed = []
    unchanged = []

    all_cats = set(list(baseline["categories"].keys()) + list(current["categories"].keys()))
    for cat_id in sorted(all_cats):
        base_cat = baseline["categories"].get(cat_id, {})
        curr_cat = current["categories"].get(cat_id, {})

        base_gt = base_cat.get("gt_avg", 0)
        curr_gt = curr_cat.get("gt_avg", 0)
        delta = curr_gt - base_gt

        if delta > 0.05:
            verdict = "IMPROVED"
            improved.append((cat_id, delta))
        elif delta < -0.05:
            verdict = "REGRESSED"
            regressed.append((cat_id, delta))
        else:
            verdict = "unchanged"
            unchanged.append(cat_id)

        base_n = base_cat.get("n", 0)
        curr_n = curr_cat.get("n", 0)
        n_str = f" (n={curr_n})" if curr_n != base_n else ""

        print(f"{cat_id:<30} {base_gt:>7.3f} {curr_gt:>7.3f} {delta:>+7.3f} {verdict:>12}{n_str}")

    # Per-variant comparison (only show changed ones)
    print(f"\n{'Changed Variants':<45} {'Base GT':>8} {'Curr GT':>8} {'Delta':>8}")
    print("-" * 72)

    variant_changes = 0
    all_variants = set(list(baseline.get("per_variant", {}).keys()) + list(current.get("per_variant", {}).keys()))
    for var_id in sorted(all_variants):
        base_var = baseline.get("per_variant", {}).get(var_id, {})
        curr_var = current.get("per_variant", {}).get(var_id, {})

        base_gt = base_var.get("gt_avg", 0)
        curr_gt = curr_var.get("gt_avg", 0)
        delta = curr_gt - base_gt

        if abs(delta) > 0.01:
            print(f"{var_id:<45} {base_gt:>7.3f} {curr_gt:>7.3f} {delta:>+7.3f}")
            variant_changes += 1

    if variant_changes == 0:
        print("  (no variant-level changes)")

    # New variants (in current but not baseline)
    new_variants = [v for v in current.get("per_variant", {}).keys() if v not in baseline.get("per_variant", {})]
    if new_variants:
        print(f"\nNEW VARIANTS ({len(new_variants)}):")
        for var_id in sorted(new_variants):
            curr_var = current["per_variant"][var_id]
            print(f"  {var_id}: GT {curr_var['gt_avg']:.3f} (n={curr_var['n']})")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Overall GT: {baseline['overall_gt_mean']:.4f} -> {current['overall_gt_mean']:.4f} ({gt_delta:+.4f})")
    print(f"  Improved categories: {len(improved)}")
    for cat_id, delta in improved:
        print(f"    {cat_id}: {delta:+.3f}")
    print(f"  Regressed categories: {len(regressed)}")
    for cat_id, delta in regressed:
        print(f"    {cat_id}: {delta:+.3f}")
    print(f"  Unchanged categories: {len(unchanged)}")

    if gt_delta > 0.01:
        print(f"\n  VERDICT: IMPROVED (+{gt_delta:.4f} GT mean). Keep changes, save new baseline.")
    elif gt_delta < -0.01:
        print(f"\n  VERDICT: REGRESSED ({gt_delta:.4f} GT mean). Revert changes.")
    else:
        print(f"\n  VERDICT: NO CHANGE. Patterns didn't move the needle.")


def show_history():
    """Show all baselines over time."""
    if not BASELINES_DIR.exists():
        print("No baselines directory found.")
        return

    files = sorted(BASELINES_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)
    if not files:
        print("No baselines saved yet. Run --save-baseline first.")
        return

    print(f"{'#':>3} {'Name':<25} {'Timestamp':<22} {'GT Mean':>8} {'Auto':>8} {'r':>7} {'n':>5}")
    print("-" * 82)

    for i, fpath in enumerate(files, 1):
        with open(fpath, "r", encoding="utf-8") as f:
            b = json.load(f)
        print(
            f"{i:>3} {b.get('name', '?'):<25} "
            f"{b['timestamp']:<22} "
            f"{b['overall_gt_mean']:>7.4f} "
            f"{b['overall_auto_mean']:>7.4f} "
            f"{b.get('pearson_r', 0):>6.3f} "
            f"{b['total_evaluations']:>5}"
        )


def main():
    parser = argparse.ArgumentParser(description="Autoresearch — Baseline management for pattern optimization")
    parser.add_argument("--save-baseline", nargs="?", const="", metavar="NAME",
                        help="Save current GT scores as baseline (optional name)")
    parser.add_argument("--compare", nargs="?", const="", metavar="NAME",
                        help="Compare current vs saved baseline (optional name)")
    parser.add_argument("--history", action="store_true",
                        help="Show all baselines over time")
    args = parser.parse_args()

    if args.save_baseline is not None:
        name = args.save_baseline if args.save_baseline else None
        save_baseline(name)
    elif args.compare is not None:
        name = args.compare if args.compare else None
        compare_baseline(name)
    elif args.history:
        show_history()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
