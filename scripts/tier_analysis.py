"""
Tier Analysis — Break down pattern performance by company size tier.

Reads master test results and the config to produce:
1. Per-tier accuracy breakdown (% categories at PRIMARY per tier)
2. Categories that break at Tier 3-4
3. Data source reliability matrix by tier
4. Company-specific failure analysis

Usage:
    py scripts/tier_analysis.py                              # full analysis
    py scripts/tier_analysis.py --category founders_ceo      # single category
    py scripts/tier_analysis.py --source-matrix               # data source tier matrix only
    py scripts/tier_analysis.py --company-scores              # per-company score breakdown
    py scripts/tier_analysis.py --no-exclude                  # include pathological companies
"""

import json
import re
import argparse
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_FILES = [
    SCRIPT_DIR.parent / "searches" / "raw-results-master.json",
    SCRIPT_DIR.parent / "searches" / "raw-results-master-combo.json",
]
CONFIG_FILE = SCRIPT_DIR / "master_test_config.json"

# Companies excluded from PRIMARY classification by default.
# These have pathological disambiguation issues (common English words or
# domain-name ambiguity) that no search pattern can reliably overcome.
# They're still in the test set — their scores are shown but don't count
# toward classification thresholds.
EXCLUDE_COMPANIES = {"Rewatch", "Hoo.be"}


def load_data():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    results = []
    for fpath in RESULTS_FILES:
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                results.extend(json.load(f))

    # Build company tier lookup
    company_tiers = {}
    for c in config["test_companies"]:
        company_tiers[c["company_name"]] = c.get("tier", 2)

    return config, results, company_tiers


def analyze_by_tier(results, company_tiers, category_filter=None, exclude=None):
    """Group results by (category, variant, tier) and compute tier-specific scores.

    Returns two dicts:
      data: {cat_id: {var_id: {tier: [quality_scores]}}}  (excluded companies filtered out)
      data_all: same but with ALL companies (for display)
    """
    exclude = exclude or set()

    data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    data_all = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for r in results:
        cat_id = r.get("category_id")
        var_id = r.get("variant_id")
        company = r.get("company", "?")
        quality = r.get("scores", {}).get("quality", 0)
        tier = company_tiers.get(company, 2)

        if category_filter and cat_id != category_filter:
            continue

        data_all[cat_id][var_id][tier].append(quality)
        if company not in exclude:
            data[cat_id][var_id][tier].append(quality)

    return data, data_all


def classify_variant(scores_by_tier):
    """Given {tier: [scores]}, compute per-tier and overall classification.

    Thresholds (calibrated for 23-25 company test sets):
      PRIMARY:    avg >= 3.8 AND consistency >= 3.5
      ENRICHMENT: avg >= 3.5 AND consistency >= 3.0
      FALLBACK:   avg >= 2.5
      KILL:       below 2.5
    """
    all_scores = []
    tier_avgs = {}
    for tier in sorted(scores_by_tier.keys()):
        scores = scores_by_tier[tier]
        if scores:
            avg = sum(scores) / len(scores)
            tier_avgs[tier] = round(avg, 1)
            all_scores.extend(scores)

    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    q4_count = sum(1 for s in all_scores if s >= 4)
    consistency = q4_count / len(all_scores) * 5 if all_scores else 0

    if overall_avg >= 3.8 and consistency >= 3.5:
        classification = "PRIMARY"
    elif overall_avg >= 3.5 and consistency >= 3.0:
        classification = "ENRICHMENT"
    elif overall_avg >= 2.5:
        classification = "FALLBACK"
    else:
        classification = "KILL"

    return {
        "overall_avg": round(overall_avg, 1),
        "consistency": round(consistency, 1),
        "classification": classification,
        "tier_avgs": tier_avgs,
        "total_tests": len(all_scores),
    }


def classify_tier_split(scores_by_tier):
    """Classify separately for T1-T2 (enterprise/growth) vs T3-T4 (early/micro)."""
    upper = {}  # T1-T2
    lower = {}  # T3-T4
    for tier, scores in scores_by_tier.items():
        if tier <= 2:
            upper[tier] = scores
        else:
            lower[tier] = scores

    return {
        "upper": classify_variant(upper) if upper else None,
        "lower": classify_variant(lower) if lower else None,
    }


def print_tier_report(data, data_all, company_tiers, exclude):
    """Print comprehensive tier analysis report."""
    tier_names = {1: "T1 Enterprise", 2: "T2 Growth", 3: "T3 Early", 4: "T4 Micro"}
    tiers_present = sorted(set(company_tiers.values()))

    # For each category, find the best variant (using filtered data for classification)
    best_per_category = {}
    all_variants = {}
    all_variants_full = {}  # Including excluded companies for display

    for cat_id, variants in sorted(data.items()):
        best_overall = None
        best_score = -1

        for var_id, tier_scores in variants.items():
            stats = classify_variant(tier_scores)
            all_variants[(cat_id, var_id)] = stats

            # Also compute with ALL companies for display
            if cat_id in data_all and var_id in data_all[cat_id]:
                full_stats = classify_variant(data_all[cat_id][var_id])
                all_variants_full[(cat_id, var_id)] = full_stats

            # Compute tier split
            split = classify_tier_split(tier_scores)
            stats["tier_split"] = split

            if stats["overall_avg"] > best_score or (
                stats["overall_avg"] == best_score and stats["consistency"] > (best_overall or {}).get("consistency", 0)
            ):
                best_score = stats["overall_avg"]
                best_overall = {**stats, "var_id": var_id}

        if best_overall:
            best_per_category[cat_id] = best_overall

    # === SUMMARY TABLE ===
    excluded_str = f" (excluding {', '.join(sorted(exclude))})" if exclude else ""
    print("\n" + "=" * 130)
    print(f"TIER ANALYSIS — ONE BEST PER CATEGORY{excluded_str}")
    print("=" * 130)

    header = f"{'Category':<35} {'Best Variant':<20} {'Overall':>8} {'Status':<12} {'T1-T2':<12} {'T3-T4':<12}"
    for t in tiers_present:
        header += f" {'T' + str(t):>6}"
    print(header)
    print("-" * 130)

    primary_count = 0
    enrichment_count = 0
    total_count = 0
    tier_primary_counts = {t: 0 for t in tiers_present}
    tier_total_counts = {t: 0 for t in tiers_present}
    weak_categories = []

    for cat_id in sorted(best_per_category.keys()):
        best = best_per_category[cat_id]
        total_count += 1

        if best["classification"] == "PRIMARY":
            primary_count += 1
        elif best["classification"] == "ENRICHMENT":
            enrichment_count += 1

        # Tier split labels
        upper_label = best.get("tier_split", {}).get("upper", {})
        lower_label = best.get("tier_split", {}).get("lower", {})
        upper_str = upper_label["classification"][:4] if upper_label else "---"
        lower_str = lower_label["classification"][:4] if lower_label else "---"

        row = f"{cat_id:<35} {best['var_id']:<20} Q{best['overall_avg']:>4} {best['classification']:<12} {upper_str:<12} {lower_str:<12}"
        for t in tiers_present:
            tavg = best["tier_avgs"].get(t, 0)
            row += f" Q{tavg:>4}"
            tier_total_counts[t] += 1
            if tavg >= 3.8:
                tier_primary_counts[t] += 1

        # Flag weak tiers
        weak_tiers = [t for t in tiers_present if best["tier_avgs"].get(t, 0) < 3.5]
        if weak_tiers:
            row += f"  << WEAK at {', '.join('T' + str(t) for t in weak_tiers)}"
            weak_categories.append((cat_id, best, weak_tiers))

        print(row)

    # === ACCURACY SUMMARY ===
    print("\n" + "=" * 80)
    print("ACCURACY SUMMARY")
    print("=" * 80)
    primary_pct = primary_count / total_count * 100 if total_count else 0
    usable_pct = (primary_count + enrichment_count) / total_count * 100 if total_count else 0
    print(f"PRIMARY:    {primary_count}/{total_count} categories ({primary_pct:.0f}%)")
    print(f"ENRICHMENT: {enrichment_count}/{total_count} categories")
    print(f"Usable (PRIMARY+ENRICHMENT): {primary_count + enrichment_count}/{total_count} ({usable_pct:.0f}%)")
    print(f"\nPer-tier breakdown (categories with tier avg >= 3.8):")
    for t in tiers_present:
        pct = tier_primary_counts[t] / tier_total_counts[t] * 100 if tier_total_counts[t] else 0
        print(f"  {tier_names.get(t, f'Tier {t}')}: {tier_primary_counts[t]}/{tier_total_counts[t]} at Q3.8+ ({pct:.0f}%)")

    if exclude:
        print(f"\nExcluded from classification: {', '.join(sorted(exclude))}")
        print("  (Pathological disambiguation — common English words or domain ambiguity)")

    # === WEAK CATEGORIES DETAIL ===
    if weak_categories:
        print("\n" + "=" * 80)
        print(f"WEAK CATEGORIES ({len(weak_categories)} categories below Q3.5 on at least one tier)")
        print("=" * 80)
        for cat_id, best, weak_tiers in weak_categories:
            print(f"\n  {cat_id} (best: {best['var_id']}, overall Q{best['overall_avg']})")
            for t in weak_tiers:
                print(f"    Tier {t} ({tier_names.get(t, '?')}): Q{best['tier_avgs'].get(t, 0)}")

            # Show all variants for this category
            print(f"    All variants for this category:")
            for var_id, tier_scores in data[cat_id].items():
                stats = all_variants[(cat_id, var_id)]
                tier_str = ", ".join(f"T{t}:Q{stats['tier_avgs'].get(t, 0)}" for t in tiers_present)
                print(f"      {var_id}: Q{stats['overall_avg']} ({stats['classification']}) -- {tier_str}")

    return best_per_category, weak_categories


def print_company_scores(results, company_tiers, exclude):
    """Print per-company score breakdown to identify score-poisoning outliers."""
    company_scores = defaultdict(list)
    for r in results:
        company = r.get("company", "?")
        quality = r.get("scores", {}).get("quality", 0)
        company_scores[company].append(quality)

    print("\n" + "=" * 80)
    print("PER-COMPANY SCORE BREAKDOWN")
    print("=" * 80)

    header = f"{'Company':<20} {'Tier':>4} {'Avg Q':>6} {'Q4+':>6} {'Q3':>6} {'Q2':>6} {'Q1':>6} {'Tests':>6} {'Excl':>6}"
    print(header)
    print("-" * 80)

    rows = []
    for company, scores in company_scores.items():
        tier = company_tiers.get(company, 2)
        avg = sum(scores) / len(scores)
        q4 = sum(1 for s in scores if s >= 4)
        q3 = sum(1 for s in scores if s == 3)
        q2 = sum(1 for s in scores if s == 2)
        q1 = sum(1 for s in scores if s <= 1)
        excl = "YES" if company in exclude else ""
        rows.append((tier, avg, company, q4, q3, q2, q1, len(scores), excl))

    for tier, avg, company, q4, q3, q2, q1, total, excl in sorted(rows):
        print(f"{company:<20} T{tier:>3} Q{avg:>4.1f} {q4:>5} {q3:>5} {q2:>5} {q1:>5} {total:>5}  {excl}")


def print_source_matrix(results, company_tiers):
    """Print data source reliability matrix by tier."""
    tier_names = {1: "T1 Enterprise", 2: "T2 Growth", 3: "T3 Early", 4: "T4 Micro"}
    tiers_present = sorted(set(company_tiers.values()))

    # Collect domains from Q3+ results, grouped by tier
    tier_domains = defaultdict(lambda: defaultdict(int))
    tier_totals = defaultdict(int)

    for r in results:
        quality = r.get("scores", {}).get("quality", 0)
        if quality < 3:
            continue
        company = r.get("company", "?")
        tier = company_tiers.get(company, 2)
        tier_totals[tier] += 1

        domains = r.get("all_domains", [])
        seen = set()
        for d in domains:
            if d not in seen:
                tier_domains[tier][d] = tier_domains[tier].get(d, 0) + 1
                seen.add(d)

    # Find top domains across all tiers
    all_domain_counts = defaultdict(int)
    for tier_data in tier_domains.values():
        for domain, count in tier_data.items():
            all_domain_counts[domain] += count

    top_domains = sorted(all_domain_counts.items(), key=lambda x: x[1], reverse=True)[:25]

    print("\n" + "=" * 100)
    print("DATA SOURCE RELIABILITY MATRIX (Q3+ results only)")
    print("=" * 100)

    header = f"{'Source':<30}"
    for t in tiers_present:
        header += f" {tier_names.get(t, f'T{t}'):>14}"
    header += f" {'Overall':>10}"
    print(header)
    print("-" * 100)

    for domain, total_count in top_domains:
        row = f"{domain:<30}"
        for t in tiers_present:
            count = tier_domains[t].get(domain, 0)
            total = tier_totals.get(t, 1)
            pct = count / total * 100 if total else 0
            if pct >= 50:
                row += f" {pct:>10.0f}% ***"
            elif pct >= 25:
                row += f" {pct:>10.0f}% **"
            elif pct >= 10:
                row += f" {pct:>10.0f}% *"
            else:
                row += f" {pct:>10.0f}%"
        overall_pct = total_count / sum(tier_totals.values()) * 100 if sum(tier_totals.values()) else 0
        row += f" {overall_pct:>8.0f}%"
        print(row)

    print(f"\nTotal Q3+ results by tier: {', '.join(f'T{t}: {tier_totals[t]}' for t in tiers_present)}")


def main():
    parser = argparse.ArgumentParser(description="Tier Analysis")
    parser.add_argument("--category", type=str, help="Analyze single category")
    parser.add_argument("--source-matrix", action="store_true", help="Print source reliability matrix only")
    parser.add_argument("--company-scores", action="store_true", help="Print per-company score breakdown")
    parser.add_argument("--no-exclude", action="store_true", help="Include all companies (no exclusions)")
    args = parser.parse_args()

    config, results, company_tiers = load_data()
    exclude = set() if args.no_exclude else EXCLUDE_COMPANIES

    if args.source_matrix:
        print_source_matrix(results, company_tiers)
        return

    if args.company_scores:
        print_company_scores(results, company_tiers, exclude)
        return

    data, data_all = analyze_by_tier(results, company_tiers, category_filter=args.category, exclude=exclude)
    best_per_category, weak_categories = print_tier_report(data, data_all, company_tiers, exclude)
    print_company_scores(results, company_tiers, exclude)
    print_source_matrix(results, company_tiers)


if __name__ == "__main__":
    main()
