"""
Validate Series B/C pipeline output against known funding announcements.

Usage:
    py scripts/validate_round_pipeline.py --round B
    py scripts/validate_round_pipeline.py --round C
    py scripts/validate_round_pipeline.py --round B --date 2026-04-21

Compares pipeline output (from trigger.dev test run logs or Supabase) against
manually curated ground truth for the specified round type and date range.
"""

import json
import argparse
from datetime import datetime

# Ground truth: known funding announcements April 2026
# Source: finsmes.com, thesaasnews.com, techcrunch.com, prnewswire.com
GROUND_TRUTH = {
    "B": {
        "month": "2026-04",
        "companies": [
            {"name": "Turion", "amount": "$75M", "source": "finsmes.com"},
            {"name": "Bluefish", "amount": "$43M", "source": "finsmes.com"},
            {"name": "Syneron Bio", "amount": "$150M", "source": "finsmes.com"},
            {"name": "Patlytics", "amount": "$40M", "source": "finsmes.com"},
            {"name": "Linx Security", "amount": "$50M", "source": "finsmes.com"},
            {"name": "EnerVenue", "amount": "$300M", "source": "finsmes.com"},
            {"name": "Alcatraz", "amount": "$50M", "source": "finsmes.com"},
            {"name": "Barrell Lithium", "amount": "undisclosed", "source": "finsmes.com"},
            {"name": "Kytopen", "amount": "undisclosed", "source": "finsmes.com"},
            {"name": "Genspark", "amount": "$385M", "source": "thesaasnews.com"},
            {"name": "Benepass", "amount": "$40M", "source": "thesaasnews.com"},
            {"name": "Ivo", "amount": "$55M", "source": "thesaasnews.com"},
            {"name": "Emergent", "amount": "$70M", "source": "thesaasnews.com"},
            {"name": "GovDash", "amount": "$30M", "source": "thesaasnews.com"},
            {"name": "MontyCloud", "amount": "undisclosed", "source": "thesaasnews.com"},
            {"name": "april", "amount": "$38M", "source": "thesaasnews.com"},
            {"name": "Numeric", "amount": "$51M", "source": "thesaasnews.com"},
            {"name": "Spiral Therapeutics", "amount": "$27M", "source": "nationaltoday.com"},
            {"name": "Mintlify", "amount": "$45M", "source": "various"},
            {"name": "Expo", "amount": "$45M", "source": "various"},
        ],
    },
    "C": {
        "month": "2026-04",
        "companies": [
            {"name": "Slash", "amount": "$100M", "source": "finsmes.com"},
            {"name": "Coder", "amount": "$90M", "source": "finsmes.com"},
            {"name": "Hermeus", "amount": "$350M", "source": "hermeus.com"},
            {"name": "Slate", "amount": "$650M", "source": "various"},
            {"name": "Factory", "amount": "$150M", "source": "various"},
            {"name": "Loop", "amount": "$95M", "source": "various"},
        ],
    },
}


def normalize(name: str) -> str:
    return name.lower().strip().replace(",", "").replace(".", "")


def evaluate(pipeline_output: list[dict], gt_companies: list[dict]) -> dict:
    """Compare pipeline output against ground truth."""
    found_names = {normalize(r.get("company_name", "")) for r in pipeline_output}

    hits = []
    misses = []
    for gt in gt_companies:
        gt_norm = normalize(gt["name"])
        if any(gt_norm in fn or fn in gt_norm for fn in found_names if len(fn) > 2):
            hits.append(gt["name"])
        else:
            misses.append(gt["name"])

    extra = []
    gt_norms = {normalize(g["name"]) for g in gt_companies}
    for r in pipeline_output:
        r_norm = normalize(r.get("company_name", ""))
        if not any(gn in r_norm or r_norm in gn for gn in gt_norms if len(gn) > 2):
            extra.append(r.get("company_name", "?"))

    recall = len(hits) / len(gt_companies) if gt_companies else 0
    precision = len(hits) / len(pipeline_output) if pipeline_output else 0

    return {
        "recall": f"{recall:.0%}",
        "precision": f"{precision:.0%}",
        "hits": len(hits),
        "misses": len(misses),
        "extra": len(extra),
        "total_gt": len(gt_companies),
        "total_output": len(pipeline_output),
        "hit_names": hits,
        "missed_names": misses,
        "extra_names": extra[:20],
    }


def main():
    parser = argparse.ArgumentParser(description="Validate round pipeline against GT")
    parser.add_argument("--round", required=True, choices=["B", "C"], help="Round type")
    parser.add_argument("--output-file", type=str, help="Path to pipeline JSON output")
    parser.add_argument("--date", type=str, default=None, help="Filter GT to specific date")
    args = parser.parse_args()

    gt = GROUND_TRUTH.get(args.round)
    if not gt:
        print(f"No ground truth for Series {args.round}")
        return

    gt_companies = gt["companies"]
    print(f"\n{'='*60}")
    print(f"  SERIES {args.round} PIPELINE VALIDATION")
    print(f"  Ground truth: {len(gt_companies)} companies ({gt['month']})")
    print(f"{'='*60}")

    if args.output_file:
        with open(args.output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        pipeline_output = data if isinstance(data, list) else data.get("companies", [])

        result = evaluate(pipeline_output, gt_companies)

        print(f"\n  Recall:    {result['recall']} ({result['hits']}/{result['total_gt']})")
        print(f"  Precision: {result['precision']} ({result['hits']}/{result['total_output']})")
        print(f"\n  HITS ({result['hits']}):")
        for h in result["hit_names"]:
            print(f"    ✓ {h}")
        print(f"\n  MISSES ({result['misses']}):")
        for m in result["missed_names"]:
            print(f"    ✗ {m}")
        if result["extra_names"]:
            print(f"\n  EXTRA ({result['extra']}) — found by pipeline, not in GT:")
            for e in result["extra_names"]:
                print(f"    ? {e}")
    else:
        print("\n  No --output-file provided. Run the pipeline first via trigger.dev")
        print("  test, then download the output and pass it here.")
        print(f"\n  Expected GT companies for Series {args.round}:")
        for c in gt_companies:
            print(f"    - {c['name']} ({c['amount']}) via {c['source']}")


if __name__ == "__main__":
    main()
