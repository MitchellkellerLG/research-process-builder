"""
Validation Orchestrator — Compare AutoScorer vs ground truth, calibrate, and report.

Three modes:
  --score:     Compare AutoScorer Q-scores with GT accuracy across all GT companies.
  --calibrate: Statistical correlation between AutoScorer and GT scores.
  --summary:   Quick summary of GT coverage and key findings.

Usage:
    py scripts/validate.py --score                          # full accuracy report
    py scripts/validate.py --calibrate                      # correlation analysis
    py scripts/validate.py --summary                        # quick coverage summary
    py scripts/validate.py --score --category founders_ceo  # single category
    py scripts/validate.py --score --company Stripe         # single company
"""

import json
import argparse
import math
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# Import gt_evaluator functions
import sys
sys.path.insert(0, str(SCRIPT_DIR))
from gt_evaluator import run_evaluation, load_ground_truth, load_schema, load_results


def compute_correlation(x_vals, y_vals):
    """Compute Pearson correlation coefficient between two lists."""
    n = len(x_vals)
    if n < 3:
        return 0.0, "insufficient_data"

    mean_x = sum(x_vals) / n
    mean_y = sum(y_vals) / n

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in x_vals))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_vals))

    if den_x == 0 or den_y == 0:
        return 0.0, "no_variance"

    r = num / (den_x * den_y)
    return round(r, 4), "ok"


def mode_score(company_filter=None, category_filter=None):
    """Run full accuracy comparison: AutoScorer vs Ground Truth."""
    evaluations = run_evaluation(
        company_filter=company_filter,
        category_filter=category_filter,
    )

    if not evaluations:
        print("No evaluations found. Check that ground truth files exist and match result companies.")
        return

    # Import and use the report printer from gt_evaluator
    from gt_evaluator import print_report
    print_report(evaluations)

    return evaluations


def mode_calibrate(company_filter=None, category_filter=None):
    """Correlation analysis between AutoScorer and Ground Truth."""
    evaluations = run_evaluation(
        company_filter=company_filter,
        category_filter=category_filter,
    )

    if not evaluations:
        print("No evaluations found.")
        return

    print("\n" + "=" * 80)
    print("CALIBRATION ANALYSIS — AutoScorer vs Ground Truth Correlation")
    print("=" * 80)

    # Overall correlation
    auto_scores = [e["auto_score"] / 5.0 for e in evaluations]
    gt_scores = [e["gt_score"] for e in evaluations]

    r, status = compute_correlation(auto_scores, gt_scores)
    print(f"\nOverall Pearson r: {r} ({status})")
    print(f"  n = {len(evaluations)} evaluation pairs")
    print(f"  AutoScorer mean: {sum(auto_scores)/len(auto_scores):.3f}")
    print(f"  GT mean:         {sum(gt_scores)/len(gt_scores):.3f}")

    if r > 0.8:
        print(f"  Verdict: STRONG correlation — AutoScorer is a good proxy for accuracy")
    elif r > 0.5:
        print(f"  Verdict: MODERATE correlation — AutoScorer captures some signal but misses cases")
    elif r > 0.2:
        print(f"  Verdict: WEAK correlation — AutoScorer is a poor proxy, GT layer adds real value")
    else:
        print(f"  Verdict: NO correlation — AutoScorer and actual accuracy are essentially unrelated")

    # Per-category correlation
    print("\n" + "-" * 80)
    print("PER-CATEGORY CORRELATION")
    print("-" * 80)

    by_category = defaultdict(list)
    for e in evaluations:
        by_category[e["category_id"]].append(e)

    print(f"{'Category':<30} {'n':>4} {'r':>8} {'AutoAvg':>8} {'GTAvg':>8} {'Verdict':<20}")
    print("-" * 80)

    category_verdicts = {}
    for cat_id in sorted(by_category.keys()):
        evals = by_category[cat_id]
        cat_auto = [e["auto_score"] / 5.0 for e in evals]
        cat_gt = [e["gt_score"] for e in evals]

        cat_r, cat_status = compute_correlation(cat_auto, cat_gt)
        auto_avg = sum(cat_auto) / len(cat_auto)
        gt_avg = sum(cat_gt) / len(cat_gt)

        # Determine verdict
        if auto_avg > 0.7 and gt_avg < 0.3:
            verdict = "OVERRATED"
        elif auto_avg < 0.5 and gt_avg > 0.7:
            verdict = "UNDERRATED"
        elif abs(auto_avg - gt_avg) < 0.15:
            verdict = "CONFIRMED"
        elif auto_avg > gt_avg:
            verdict = "SLIGHTLY OVERRATED"
        else:
            verdict = "SLIGHTLY UNDERRATED"

        category_verdicts[cat_id] = verdict
        print(f"{cat_id:<30} {len(evals):>4} {cat_r:>7.3f} {auto_avg:>7.3f} {gt_avg:>7.3f} {verdict:<20}")

    # Per-tier correlation
    print("\n" + "-" * 80)
    print("PER-TIER CORRELATION")
    print("-" * 80)

    gt = load_ground_truth()
    tier_names = {1: "T1 Enterprise", 2: "T2 Growth", 3: "T3 Early", 4: "T4 Micro"}

    by_tier = defaultdict(list)
    for e in evaluations:
        company = e["company"]
        if company in gt:
            tier = gt[company].get("tier", 2)
            by_tier[tier].append(e)

    print(f"{'Tier':<20} {'n':>4} {'r':>8} {'AutoAvg':>8} {'GTAvg':>8}")
    print("-" * 50)
    for tier in sorted(by_tier.keys()):
        evals = by_tier[tier]
        tier_auto = [e["auto_score"] / 5.0 for e in evals]
        tier_gt = [e["gt_score"] for e in evals]
        tier_r, _ = compute_correlation(tier_auto, tier_gt)
        print(f"{tier_names.get(tier, f'T{tier}'):<20} {len(evals):>4} {tier_r:>7.3f} {sum(tier_auto)/len(tier_auto):>7.3f} {sum(tier_gt)/len(tier_gt):>7.3f}")

    # Agreement matrix
    print("\n" + "-" * 80)
    print("AGREEMENT MATRIX (AutoQ >= 3 vs GT >= 0.5)")
    print("-" * 80)

    tp = sum(1 for e in evaluations if e["auto_score"] >= 3 and e["gt_score"] >= 0.5)
    fp = sum(1 for e in evaluations if e["auto_score"] >= 3 and e["gt_score"] < 0.5)
    fn = sum(1 for e in evaluations if e["auto_score"] < 3 and e["gt_score"] >= 0.5)
    tn = sum(1 for e in evaluations if e["auto_score"] < 3 and e["gt_score"] < 0.5)

    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0

    print(f"  True Positive  (AutoQ>=3, GT>=0.5): {tp}")
    print(f"  False Positive (AutoQ>=3, GT<0.5):  {fp}  << AutoScorer says good, GT says bad")
    print(f"  False Negative (AutoQ<3, GT>=0.5):  {fn}  << AutoScorer says bad, GT says good")
    print(f"  True Negative  (AutoQ<3, GT<0.5):   {tn}")
    print(f"  Accuracy:  {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")

    # Key finding
    print("\n" + "=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)

    overrated = [cat for cat, v in category_verdicts.items() if "OVERRATED" in v]
    underrated = [cat for cat, v in category_verdicts.items() if "UNDERRATED" in v]
    confirmed = [cat for cat, v in category_verdicts.items() if v == "CONFIRMED"]

    if overrated:
        print(f"\nOVERRATED categories ({len(overrated)}) — AutoScorer gives high marks but GT shows low accuracy:")
        for cat in overrated:
            print(f"  - {cat}")
        print("  Action: These patterns need fixing. Search returns results but not the RIGHT results.")

    if underrated:
        print(f"\nUNDERRATED categories ({len(underrated)}) — AutoScorer is pessimistic but GT shows decent accuracy:")
        for cat in underrated:
            print(f"  - {cat}")
        print("  Action: AutoScorer thresholds may be too strict for these.")

    if confirmed:
        print(f"\nCONFIRMED categories ({len(confirmed)}) — AutoScorer and GT agree:")
        for cat in confirmed:
            print(f"  - {cat}")

    needs_review = sum(1 for e in evaluations if e.get("needs_llm_review"))
    if needs_review:
        print(f"\nNEEDS LLM REVIEW: {needs_review}/{len(evaluations)} evaluations have ambiguous matches.")
        print("  Run: py scripts/gt_evaluator.py --needs-review")

    return evaluations


def mode_summary():
    """Quick summary of GT coverage."""
    gt = load_ground_truth()
    schema = load_schema()

    print("\n" + "=" * 60)
    print("GROUND TRUTH COVERAGE SUMMARY")
    print("=" * 60)

    print(f"\nCompanies with ground truth: {len(gt)}")
    tier_counts = defaultdict(int)
    for company, data in gt.items():
        tier = data.get("tier", 2)
        tier_counts[tier] += 1

    tier_names = {1: "T1 Enterprise", 2: "T2 Growth", 3: "T3 Early", 4: "T4 Micro"}
    for tier in sorted(tier_counts.keys()):
        companies = [c for c, d in gt.items() if d.get("tier") == tier]
        print(f"  {tier_names.get(tier, f'T{tier}')}: {tier_counts[tier]} ({', '.join(companies)})")

    # Category coverage
    all_categories = set(schema.get("categories", {}).keys())
    covered_categories = set()
    category_company_count = defaultdict(int)

    for company, data in gt.items():
        for cat_id in data.get("categories", {}).keys():
            covered_categories.add(cat_id)
            category_company_count[cat_id] += 1

    print(f"\nCategories in schema: {len(all_categories)}")
    print(f"Categories with GT data: {len(covered_categories)}")
    missing = all_categories - covered_categories
    if missing:
        print(f"Missing categories: {', '.join(sorted(missing))}")

    print(f"\nCategory coverage depth:")
    for cat_id in sorted(covered_categories):
        count = category_company_count[cat_id]
        depth = "thin" if count < 3 else "ok" if count < 6 else "good"
        print(f"  {cat_id:<35} {count:>3} companies ({depth})")


def main():
    parser = argparse.ArgumentParser(description="Validation Orchestrator")
    parser.add_argument("--score", action="store_true", help="Compare AutoScorer vs GT")
    parser.add_argument("--calibrate", action="store_true", help="Correlation analysis")
    parser.add_argument("--summary", action="store_true", help="Quick GT coverage summary")
    parser.add_argument("--company", type=str, help="Filter to single company")
    parser.add_argument("--category", type=str, help="Filter to single category")
    args = parser.parse_args()

    if not any([args.score, args.calibrate, args.summary]):
        # Default: run summary then score
        mode_summary()
        mode_score(company_filter=args.company, category_filter=args.category)
        return

    if args.summary:
        mode_summary()

    if args.score:
        mode_score(company_filter=args.company, category_filter=args.category)

    if args.calibrate:
        mode_calibrate(company_filter=args.company, category_filter=args.category)


if __name__ == "__main__":
    main()
