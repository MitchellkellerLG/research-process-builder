"""
Ground Truth Evaluator — Deterministic accuracy scoring against verified facts.

Reads stored search results + ground truth JSON files, computes accuracy scores
per (company, category, variant) tuple. Pure Python, no LLM calls.

Match strategies:
  - name_in_text:    Full name substring match (1.0), last name only (0.5), fuzzy (0.8)
  - names_in_text:   Count how many expected names appear. Score = found / expected.
  - field_present:   Check if data type pattern exists (money, date, URL).
  - text_match:      Substring match for expected text fragments.
  - boolean_present: Check if expected signal exists at all. 1.0 or 0.0.

Usage:
    py scripts/gt_evaluator.py                              # evaluate all GT companies
    py scripts/gt_evaluator.py --company Stripe             # single company
    py scripts/gt_evaluator.py --category founders_ceo      # single category
    py scripts/gt_evaluator.py --needs-review               # only show items needing LLM review
    py scripts/gt_evaluator.py --json                       # output as JSON (for validate.py)
"""

import json
import re
import argparse
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
GT_DIR = PROJECT_DIR / "ground-truth"
SCHEMA_FILE = GT_DIR / "schema.json"
RESULTS_FILES = [
    PROJECT_DIR / "searches" / "raw-results-master.json",
    PROJECT_DIR / "searches" / "raw-results-master-combo.json",
]


def load_ground_truth():
    """Load all ground truth files from ground-truth/*.json (excluding schema)."""
    gt = {}
    for fpath in GT_DIR.glob("*.json"):
        if fpath.name == "schema.json":
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        company = data.get("company")
        if company:
            gt[company] = data
    return gt


def load_schema():
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_results():
    results = []
    for fpath in RESULTS_FILES:
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                results.extend(json.load(f))
    return results


def get_searchable_text(result):
    """Extract all searchable text from a result's top_results."""
    parts = []
    for r in result.get("top_results", []):
        if r.get("title"):
            parts.append(r["title"])
        if r.get("snippet"):
            parts.append(r["snippet"])
        if r.get("link"):
            parts.append(r["link"])
    return " ".join(parts).lower()


# --- Match strategy implementations ---

def levenshtein_distance(s1, s2):
    """Simple Levenshtein distance for fuzzy name matching."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def match_name_in_text(name, text):
    """Match a single name against text. Returns (score, match_type)."""
    name_lower = name.lower()
    text_lower = text.lower()

    # Exact full name match
    if name_lower in text_lower:
        return 1.0, "exact"

    # Last name only match
    parts = name_lower.split()
    if len(parts) >= 2:
        last_name = parts[-1]
        # Require last name to be at least 4 chars to avoid false positives
        if len(last_name) >= 4 and last_name in text_lower:
            return 0.5, "last_name_only"

    # Fuzzy match — check if any similar string exists
    # Split text into word sequences of same length as name
    name_words = name_lower.split()
    text_words = text_lower.split()
    name_len = len(name_words)
    for i in range(len(text_words) - name_len + 1):
        candidate = " ".join(text_words[i:i + name_len])
        dist = levenshtein_distance(name_lower, candidate)
        if dist <= 2:
            return 0.8, "fuzzy"

    return 0.0, "not_found"


def match_names_in_text(names, text):
    """Match a list of names against text. Returns (score, details)."""
    if not names:
        return 0.0, {"found": [], "missing": [], "needs_llm_review": False}

    found = []
    missing = []
    details = {}

    for name in names:
        score, match_type = match_name_in_text(name, text)
        details[name] = match_type
        if score > 0:
            found.append(name)
        else:
            missing.append(name)

    score = len(found) / len(names) if names else 0.0

    # Flag for LLM review if we have partial/fuzzy matches
    needs_review = any(v in ("last_name_only", "fuzzy") for v in details.values())

    return score, {
        "found": found,
        "missing": missing,
        "match_details": details,
        "needs_llm_review": needs_review,
    }


def match_field_present(fields, text, gt_data):
    """Check if expected field types are present in text."""
    scores = []
    details = {}

    for field_name, field_def in fields.items():
        if field_name not in gt_data:
            continue

        expected = gt_data[field_name]
        field_type = field_def.get("type", "text")
        found = False

        if field_type == "money":
            # Look for money patterns: $X, $X million, $X billion, raised $X
            money_patterns = [
                r'\$[\d,.]+\s*(million|billion|m|b|k)?',
                r'raised\s+\$[\d,.]+',
                r'funding.*\$[\d,.]+',
                r'\$[\d,.]+\s*funding',
            ]
            for pattern in money_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    found = True
                    break
            # Also check if the expected amount string appears
            if not found and isinstance(expected, str):
                # Normalize: "$1.1B" -> check for "1.1" and "billion"
                amount = re.sub(r'[^\d.]', '', expected)
                if amount and amount in text:
                    found = True

        elif field_type == "boolean":
            # For boolean fields, we check if the expected value's signal exists
            found = True  # Boolean fields just need the category to have results

        elif field_type == "name_list":
            if isinstance(expected, list) and expected:
                score, match_info = match_names_in_text(expected, text)
                details[field_name] = match_info
                scores.append(score)
                continue

        elif field_type in ("text", "text_list"):
            if isinstance(expected, str):
                # Try exact substring first
                if expected.lower() in text.lower():
                    found = True
                else:
                    # Field-specific presence detection
                    fn = field_name.lower()
                    if 'employee' in fn or 'count' in fn or 'size' in fn:
                        # Any employee count pattern = found
                        if re.search(r'\b\d[\d,]+\s*(employees|team\s+members|people|staff|employs)', text, re.I):
                            found = True
                            details[field_name] = "employee_pattern_detected"
                    elif 'headquarter' in fn or 'location' in fn or 'hq' in fn:
                        # Check if city name from GT appears
                        city = expected.split(',')[0].strip().lower()
                        if len(city) > 3 and city in text.lower():
                            found = True
                            details[field_name] = f"city_match ({city})"
                    elif 'founded' in fn or 'year' in fn:
                        # Check if the year appears
                        year = re.search(r'\b((?:19|20)\d{2})\b', str(expected))
                        if year and year.group(1) in text:
                            found = True
                            details[field_name] = f"year_match ({year.group(1)})"

                    # Generic keyword overlap fallback
                    if not found:
                        words = [w for w in re.split(r'[\s\-/,;:()]+', expected.lower()) if len(w) > 3]
                        if words:
                            hits = sum(1 for w in words if w in text.lower())
                            if hits / len(words) >= 0.4:
                                found = True
                                details[field_name] = f"keyword_overlap ({hits}/{len(words)})"
                                scores.append(hits / len(words))
                                continue
            elif isinstance(expected, list):
                found_count = 0
                for item in expected:
                    item_lower = item.lower()
                    if item_lower in text.lower():
                        found_count += 1
                    else:
                        # Keyword overlap fallback per list item
                        words = [w for w in re.split(r'[\s\-/,;:()]+', item_lower) if len(w) > 3]
                        if words:
                            hits = sum(1 for w in words if w in text.lower())
                            if words and hits / len(words) >= 0.4:
                                found_count += 1
                if expected:
                    scores.append(found_count / len(expected))
                    details[field_name] = f"{found_count}/{len(expected)} found"
                    continue

        else:
            # Default: check if expected value appears as substring
            if isinstance(expected, str) and expected:
                found = expected.lower() in text.lower()

        if found:
            scores.append(1.0)
            details[field_name] = "found"
        else:
            scores.append(0.0)
            details[field_name] = "not_found"

    overall = sum(scores) / len(scores) if scores else 0.0
    return overall, details


def match_text(expected_texts, text):
    """Check if expected text fragments appear in the search text."""
    if not expected_texts:
        return 0.0, {}

    if isinstance(expected_texts, str):
        expected_texts = [expected_texts]

    found = []
    missing = []
    for expected in expected_texts:
        if expected.lower() in text.lower():
            found.append(expected)
        else:
            # Try partial match — split on hyphens/punctuation too, check significant words
            words = [w for w in re.split(r'[\s\-/,;:()]+', expected.lower()) if len(w) > 3]
            word_hits = sum(1 for w in words if w in text.lower())
            if words and word_hits / len(words) >= 0.5:
                found.append(expected)
            else:
                missing.append(expected)

    score = len(found) / len(expected_texts) if expected_texts else 0.0
    return score, {"found": found, "missing": missing}


def match_boolean(gt_data, text, quality_score):
    """Check if expected boolean signal exists."""
    # For boolean categories, we primarily check if the search returned
    # relevant results at all (quality >= 3)
    if quality_score >= 3:
        return 1.0, {"signal": "present", "quality": quality_score}
    return 0.0, {"signal": "absent", "quality": quality_score}


# --- Main evaluation logic ---

def evaluate_result(result, gt_company, schema):
    """Evaluate a single search result against ground truth.

    Returns dict with gt_score, match_details, needs_llm_review.
    """
    category_id = result.get("category_id")
    if category_id not in schema.get("categories", {}):
        return None

    cat_schema = schema["categories"][category_id]
    gt_categories = gt_company.get("categories", {})

    if category_id not in gt_categories:
        return None  # No ground truth for this category

    gt_data = gt_categories[category_id]
    strategy = cat_schema.get("match_strategy", "field_present")
    text = get_searchable_text(result)
    quality = result.get("scores", {}).get("quality", 0)

    if strategy == "name_in_text":
        # Primary field is "names" or "ceo_name"
        names = gt_data.get("names", [])
        if not names:
            ceo = gt_data.get("ceo_name")
            if ceo:
                names = [ceo]
        if not names:
            return {
                "gt_score": 0.0,
                "match_details": {"note": "no ground truth names available"},
                "needs_llm_review": False,
            }
        score, details = match_names_in_text(names, text)
        return {
            "gt_score": round(score, 2),
            "match_details": details,
            "needs_llm_review": details.get("needs_llm_review", False),
        }

    elif strategy == "names_in_text":
        # Find the primary name_list field
        names = []
        for field_name, field_def in cat_schema.get("fields", {}).items():
            if field_def.get("type") == "name_list" and field_name in gt_data:
                names = gt_data[field_name]
                break
        if not names:
            return {
                "gt_score": 0.0,
                "match_details": {"note": "no ground truth names available"},
                "needs_llm_review": False,
            }
        score, details = match_names_in_text(names, text)
        return {
            "gt_score": round(score, 2),
            "match_details": details,
            "needs_llm_review": details.get("needs_llm_review", False),
        }

    elif strategy == "field_present":
        fields = cat_schema.get("fields", {})
        score, details = match_field_present(fields, text, gt_data)
        return {
            "gt_score": round(score, 2),
            "match_details": details,
            "needs_llm_review": False,
        }

    elif strategy == "text_match":
        # Find text or text_list fields in ground truth
        all_texts = []
        for field_name, field_def in cat_schema.get("fields", {}).items():
            if field_name in gt_data:
                val = gt_data[field_name]
                if isinstance(val, list):
                    all_texts.extend(val)
                elif isinstance(val, str):
                    all_texts.append(val)
        if not all_texts:
            return {
                "gt_score": 0.0,
                "match_details": {"note": "no ground truth text available"},
                "needs_llm_review": False,
            }
        score, details = match_text(all_texts, text)
        return {
            "gt_score": round(score, 2),
            "match_details": details,
            "needs_llm_review": False,
        }

    elif strategy == "boolean_present":
        score, details = match_boolean(gt_data, text, quality)
        return {
            "gt_score": round(score, 2),
            "match_details": details,
            "needs_llm_review": False,
        }

    return None


def run_evaluation(company_filter=None, category_filter=None, needs_review_only=False):
    """Run full evaluation. Returns list of evaluation results."""
    schema = load_schema()
    gt = load_ground_truth()
    results = load_results()

    evaluations = []

    for result in results:
        company = result.get("company", "?")
        category_id = result.get("category_id")
        variant_id = result.get("variant_id")

        if company_filter and company != company_filter:
            continue
        if category_filter and category_id != category_filter:
            continue
        if company not in gt:
            continue

        evaluation = evaluate_result(result, gt[company], schema)
        if evaluation is None:
            continue

        if needs_review_only and not evaluation.get("needs_llm_review"):
            continue

        evaluations.append({
            "company": company,
            "category_id": category_id,
            "variant_id": variant_id,
            "auto_score": result.get("scores", {}).get("quality", 0),
            **evaluation,
        })

    return evaluations


def print_report(evaluations):
    """Print human-readable evaluation report."""
    if not evaluations:
        print("No evaluations to report.")
        return

    # Group by category
    by_category = defaultdict(list)
    for e in evaluations:
        by_category[e["category_id"]].append(e)

    print("\n" + "=" * 100)
    print("GROUND TRUTH EVALUATION REPORT")
    print("=" * 100)

    header = f"{'Category':<30} {'Variant':<20} {'Company':<15} {'AutoQ':>6} {'GT':>6} {'Delta':>7} {'Review':>7}"
    print(header)
    print("-" * 100)

    total_auto = 0
    total_gt = 0
    count = 0
    needs_review_count = 0
    overrated = []
    underrated = []

    for cat_id in sorted(by_category.keys()):
        evals = by_category[cat_id]
        for e in sorted(evals, key=lambda x: (x["company"], x["variant_id"])):
            auto_q = e["auto_score"]
            gt_score = e["gt_score"]
            # Normalize auto_score to 0-1 scale for comparison
            auto_norm = auto_q / 5.0
            delta = gt_score - auto_norm
            review = "YES" if e.get("needs_llm_review") else ""

            row = f"{cat_id:<30} {e['variant_id']:<20} {e['company']:<15} Q{auto_q:>4} {gt_score:>5.2f} {delta:>+6.2f} {review:>7}"
            print(row)

            total_auto += auto_norm
            total_gt += gt_score
            count += 1
            if e.get("needs_llm_review"):
                needs_review_count += 1
            if delta < -0.3:
                overrated.append(e)
            elif delta > 0.3:
                underrated.append(e)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    avg_auto = total_auto / count if count else 0
    avg_gt = total_gt / count if count else 0
    print(f"Total evaluations: {count}")
    print(f"Avg AutoScorer (normalized): {avg_auto:.3f}")
    print(f"Avg Ground Truth score:      {avg_gt:.3f}")
    print(f"Correlation delta:           {avg_gt - avg_auto:+.3f}")
    print(f"Needs LLM review:            {needs_review_count}/{count} ({needs_review_count/count*100:.0f}%)" if count else "")

    if overrated:
        print(f"\nOVERRATED by AutoScorer ({len(overrated)} items — AutoQ high, GT low):")
        for e in overrated[:10]:
            print(f"  {e['category_id']} / {e['company']} / {e['variant_id']}: AutoQ{e['auto_score']} vs GT {e['gt_score']:.2f}")

    if underrated:
        print(f"\nUNDERRATED by AutoScorer ({len(underrated)} items — AutoQ low, GT high):")
        for e in underrated[:10]:
            print(f"  {e['category_id']} / {e['company']} / {e['variant_id']}: AutoQ{e['auto_score']} vs GT {e['gt_score']:.2f}")

    # Per-category summary
    print("\n" + "=" * 80)
    print("PER-CATEGORY ACCURACY")
    print("=" * 80)
    print(f"{'Category':<30} {'Count':>6} {'Avg AutoQ':>10} {'Avg GT':>8} {'Delta':>7}")
    print("-" * 65)
    for cat_id in sorted(by_category.keys()):
        evals = by_category[cat_id]
        cat_auto = sum(e["auto_score"] / 5.0 for e in evals) / len(evals)
        cat_gt = sum(e["gt_score"] for e in evals) / len(evals)
        delta = cat_gt - cat_auto
        verdict = ""
        if delta < -0.2:
            verdict = " << OVERRATED"
        elif delta > 0.2:
            verdict = " << UNDERRATED"
        print(f"{cat_id:<30} {len(evals):>6} {cat_auto:>9.3f} {cat_gt:>7.3f} {delta:>+6.3f}{verdict}")


def main():
    parser = argparse.ArgumentParser(description="Ground Truth Evaluator")
    parser.add_argument("--company", type=str, help="Evaluate single company")
    parser.add_argument("--category", type=str, help="Evaluate single category")
    parser.add_argument("--needs-review", action="store_true", help="Only show items needing LLM review")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    evaluations = run_evaluation(
        company_filter=args.company,
        category_filter=args.category,
        needs_review_only=args.needs_review,
    )

    if args.json:
        print(json.dumps(evaluations, indent=2))
    else:
        print_report(evaluations)


if __name__ == "__main__":
    main()
