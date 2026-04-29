"""
TDD Harness — Confidence Scorer
5 progressive cycles. Each cycle enables additional signals.
Reports pass rate and delta between cycles.

Usage:
    py scripts/test_confidence_scorer.py           # run all 5 cycles
    py scripts/test_confidence_scorer.py --cycle 3 # run specific cycle
    py scripts/test_confidence_scorer.py --apply   # show what today's stage1 would filter
"""

import argparse
import json
import sys
from pathlib import Path
from dataclasses import dataclass

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# ---------------------------------------------------------------------------
# Test Cases
# Labels are the EXPECTED composite confidence level.
# Rationale column explains what the case is testing.
# ---------------------------------------------------------------------------

@dataclass
class Case:
    id: str
    company_name: str
    title: str
    snippet: str
    source_domain: str
    expected: str          # "high" | "medium" | "low"
    rationale: str


TEST_CASES: list[Case] = [
    # ── TRUE POSITIVES: should be HIGH ───────────────────────────────────────
    Case(
        id="TP01",
        company_name="Fathom Therapeutics",
        title="Fathom Therapeutics Raises $47M in Series A Funding",
        snippet="Fathom Therapeutics, a Boston-based biotech, raised $47M Series A led by Atlas.",
        source_domain="finsmes.com",
        expected="high",
        rationale="Tier-S source, clean name, 'Series A' in title",
    ),
    Case(
        id="TP02",
        company_name="IC Realtime",
        title="IC Realtime Secures $2 Million Series A Funding Round",
        snippet="IC Realtime, a provider of surveillance technology, secured $2M Series A.",
        source_domain="prnewswire.com",
        expected="high",
        rationale="Press wire source, clean name, 'Series A' in title",
    ),
    Case(
        id="TP03",
        company_name="Clarasight",
        title="Clarasight Raises $11.5M in Series A Funding",
        snippet="Clarasight, an AI platform for enterprise travel, raised $11.5M Series A.",
        source_domain="finsmes.com",
        expected="high",
        rationale="Canonical tier-S case",
    ),
    Case(
        id="TP04",
        company_name="OpenLight",
        title="OpenLight Raises $50M in Series A-1 Funding",
        snippet="OpenLight, a photonics company, raised $50M in Series A-1.",
        source_domain="finsmes.com",
        expected="high",
        rationale="Series A-1 variant — should still score HIGH",
    ),
    Case(
        id="TP05",
        company_name="Cybord",
        title="Cybord Raises $7M Extended Series A; Establishes U.S. Sales Office",
        snippet="Cybord, an electronics supply chain integrity company, raised $7M.",
        source_domain="prnewswire.com",
        expected="high",
        rationale="Extended Series A — still Series A, press wire source",
    ),
    Case(
        id="TP06",
        company_name="Avoca",
        title="Avoca Raises $125M+ at $1B Valuation | The SaaS News",
        snippet="Avoca announced a Series A round of $125M led by General Catalyst.",
        source_domain="thesaasnews.com",
        expected="medium",
        rationale="'Series A' in snippet only -> review queue even from tier-S source (not auto-promoted)",
    ),
    Case(
        id="TP07",
        company_name="A&K Robotics",
        title="A&K Robotics Closes $50M Series A to Scale Autonomous Mobility",
        snippet="A&K Robotics, a Vancouver-based autonomous mobility company, raised $50M.",
        source_domain="techcrunch.com",
        expected="high",
        rationale="TechCrunch source, clean name",
    ),

    # ── MEDIUM CONFIDENCE: borderline ────────────────────────────────────────
    Case(
        id="MD01",
        company_name="Forest",
        title="British e-bike operator Forest secures further £31 million",
        snippet="Forest, the e-bike sharing company, has raised a further £31M in its Series A extension.",
        source_domain="eu-startups.com",
        expected="medium",
        rationale="Good source but no 'Series A' in title — extension round description",
    ),
    Case(
        id="MD02",
        company_name="Celea Therapeutics",
        title="PureTech Announces Annual Results for Year Ended December 31 2025",
        snippet="Within annual results, subsidiary Celea Therapeutics completed a $45M Series A.",
        source_domain="businesswire.com",
        expected="medium",
        rationale="Press wire but 'Series A' buried in annual results, not primary announcement",
    ),
    Case(
        id="MD03",
        company_name="SomeCompany",
        title="SomeCompany Closes Funding Round",
        snippet="SomeCompany raised $15M to expand its platform.",
        source_domain="unknownnewssite.co",
        expected="medium",
        rationale="Unknown source + no 'Series A' in title = double MEDIUM",
    ),
    Case(
        id="MD04",
        company_name="Signit",
        title="Signit Raises $15 Million Series A | The SaaS News",
        snippet="Signit, a threat intelligence startup, raised $15M Series A.",
        source_domain="thesaasnews.com",
        expected="high",
        rationale="'Series A' in title, tier-S source — should be HIGH despite 'startup' in snippet",
    ),

    # ── TRUE NEGATIVES: should be LOW ────────────────────────────────────────
    Case(
        id="TN01",
        company_name="Ex-Twitter CEO's AI Startup",
        title="Ex-Twitter CEO's AI Startup Raises Funds at $2 Billion Valuation",
        snippet="Jack Dorsey's new venture has raised money at a $2B valuation.",
        source_domain="wsj.com",
        expected="low",
        rationale="Headline as company name + low-tier paywall source",
    ),
    Case(
        id="TN02",
        company_name="Inc42",
        title="Saas Startup Mojro Technologies has raised an additional $2.5M Series A",
        snippet="Mojro raised $2.5M in additional Series A funding led by Accel India.",
        source_domain="facebook.com",
        expected="low",
        rationale="Media outlet name as company_name + social media source",
    ),
    Case(
        id="TN03",
        company_name="Goldman Sachs Alternatives",
        title="Goldman Sachs Alternatives Announces Strategic Investment in Kashable",
        snippet="Goldman Sachs Alternatives led the Series C equity round for Kashable.",
        source_domain="businesswire.com",
        expected="low",
        rationale="Investor/fund name captured as company_name — VC pattern match",
    ),
    Case(
        id="TN04",
        company_name="AI-powered recruiting startup",
        title="AI-powered recruiting startup Dex raises $5.3 million seed round",
        snippet="Dex, an AI recruiting tool, raised $5.3M in seed funding.",
        source_domain="vcnewsdaily.com",
        expected="low",
        rationale="'startup' in name + dead source domain",
    ),
    Case(
        id="TN05",
        company_name="Manifest OS",
        title="Manifest OS Raises $60 Million Series A at $750 Million Valuation",
        snippet="Manifest OS has raised $60M Series A.",
        source_domain="yimg.com",
        expected="medium",
        rationale="Clean name + 'Series A' in title BUT yimg.com is a CDN/Yahoo image domain — unknown tier",
    ),
]

# ---------------------------------------------------------------------------
# Cycle Definitions
# Each cycle enables a subset of signals to simulate progressive TDD.
# Cycle 5 = full scorer (all signals active).
# ---------------------------------------------------------------------------

CYCLE_CONFIGS = {
    1: {"name": "Name quality only",               "use_name": True,  "use_explicit": False, "use_tier": False},
    2: {"name": "Name + Series A explicitness",    "use_name": True,  "use_explicit": True,  "use_tier": False},
    3: {"name": "Name + Explicit + Source tier",   "use_name": True,  "use_explicit": True,  "use_tier": True},
    4: {"name": "Full scorer (same as cycle 3)",   "use_name": True,  "use_explicit": True,  "use_tier": True},
    5: {"name": "Full scorer + stage1 live apply", "use_name": True,  "use_explicit": True,  "use_tier": True},
}


# ---------------------------------------------------------------------------
# Partial scorer — respects cycle config
# ---------------------------------------------------------------------------

from confidence_scorer import (
    score_name_quality,
    score_funding_explicit,
    score_source_tier,
    ConfidenceLevel,
    _composite,
)


def run_cycle_on_case(case: Case, cfg: dict) -> ConfidenceLevel:
    signals = []
    if cfg["use_name"]:
        lvl, _ = score_name_quality(case.company_name)
        signals.append(lvl)
    if cfg["use_explicit"]:
        lvl, _ = score_funding_explicit(case.title, case.snippet)
        signals.append(lvl)
    if cfg["use_tier"]:
        lvl, _ = score_source_tier(case.source_domain)
        signals.append(lvl)

    if not signals:
        return ConfidenceLevel.HIGH  # no signals = no filter

    return _composite(signals)


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def score_cycle(cycle_num: int) -> dict:
    cfg = CYCLE_CONFIGS[cycle_num]
    results = []
    for case in TEST_CASES:
        got = run_cycle_on_case(case, cfg)
        passed = got.value == case.expected
        results.append({
            "id": case.id,
            "expected": case.expected,
            "got": got.value,
            "pass": passed,
            "rationale": case.rationale,
        })

    total = len(results)
    passed_count = sum(1 for r in results if r["pass"])
    fails = [r for r in results if not r["pass"]]

    # Precision proxy: of HIGH outputs, how many were expected HIGH?
    high_outputs = [r for r in results if r["got"] == "high"]
    true_positives = [r for r in high_outputs if r["expected"] == "high"]
    precision = len(true_positives) / len(high_outputs) if high_outputs else 1.0

    # Recall proxy: of expected HIGH cases, how many scored HIGH?
    expected_high = [r for r in results if r["expected"] == "high"]
    recall = len(true_positives) / len(expected_high) if expected_high else 0.0

    # LOW catch rate: of expected LOW cases, how many scored LOW?
    expected_low = [r for r in results if r["expected"] == "low"]
    caught_low = [r for r in expected_low if r["got"] == "low"]
    low_catch_rate = len(caught_low) / len(expected_low) if expected_low else 0.0

    return {
        "cycle": cycle_num,
        "name": cfg["name"],
        "total": total,
        "passed": passed_count,
        "pass_rate": passed_count / total,
        "precision": precision,
        "recall": recall,
        "low_catch_rate": low_catch_rate,
        "fails": fails,
    }


def print_cycle_report(result: dict, prev: dict | None = None):
    delta = ""
    if prev:
        d = result["passed"] - prev["passed"]
        delta = f"  [delta {'+' if d >= 0 else ''}{d} vs cycle {prev['cycle']}]"

    print(f"\n{'='*60}")
    print(f"CYCLE {result['cycle']}: {result['name']}")
    print(f"{'='*60}")
    print(f"  Tests:     {result['passed']}/{result['total']} pass ({result['pass_rate']:.0%}){delta}")
    print(f"  Precision: {result['precision']:.0%}  (HIGH outputs that were correct)")
    print(f"  Recall:    {result['recall']:.0%}  (legit companies scoring HIGH)")
    print(f"  LOW catch: {result['low_catch_rate']:.0%}  (garbage scoring LOW)")

    if result["fails"]:
        print(f"\n  Failures ({len(result['fails'])}):")
        for f in result["fails"]:
            print(f"    [{f['id']}] expected={f['expected']} got={f['got']} — {f['rationale'][:70]}")


# ---------------------------------------------------------------------------
# Live stage1 apply (cycle 5)
# ---------------------------------------------------------------------------

def apply_to_stage1():
    stage_dir = REPO_ROOT / "output" / "stages"
    stage1_files = sorted(stage_dir.glob("stage1-*.json"), reverse=True)
    if not stage1_files:
        print("\n  [SKIP] No stage1 JSON found — run pipeline first")
        return

    path = stage1_files[0]
    print(f"\n  Applying confidence scorer to: {path.name}")

    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    if isinstance(records, dict):
        records = records.get("results", list(records.values())[0] if records else [])

    from confidence_scorer import score_funding_explicit, score_source_tier, _composite

    buckets = {"high": [], "medium": [], "low": []}
    for r in records:
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        domain = r.get("source_domain", "")

        # Stage1 pre-filter: name_quality SKIPPED (company not extracted yet).
        # Only score Series A explicitness + source tier.
        # name_quality fires later at Stage 2 after GPT extracts company name.
        explicit_lvl, explicit_reason = score_funding_explicit(title, snippet)
        tier_lvl, tier_reason = score_source_tier(domain)
        composite = _composite([explicit_lvl, tier_lvl])

        buckets[composite.value].append({
            "title": title[:80],
            "domain": domain,
            "signals": [explicit_lvl.value, tier_lvl.value],
        })

    total = len(records)
    print(f"\n  Stage1 results: {total}")
    print(f"  HIGH:   {len(buckets['high'])} ({len(buckets['high'])/total:.0%}) -> write to Supabase")
    print(f"  MEDIUM: {len(buckets['medium'])} ({len(buckets['medium'])/total:.0%}) -> review queue")
    print(f"  LOW:    {len(buckets['low'])} ({len(buckets['low'])/total:.0%}) -> drop")

    print(f"\n  Sample LOW entries (would be dropped):")
    for entry in buckets["low"][:5]:
        print(f"    [{entry['signals']}] {entry['title']}")

    print(f"\n  Sample MEDIUM entries (would need review):")
    for entry in buckets["medium"][:5]:
        print(f"    [{entry['signals']}] {entry['title']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle", type=int, help="Run a single cycle number (1-5)")
    parser.add_argument("--apply", action="store_true", help="Apply scorer to latest stage1 JSON")
    args = parser.parse_args()

    if args.apply:
        apply_to_stage1()
        return

    cycles_to_run = [args.cycle] if args.cycle else [1, 2, 3, 4, 5]

    print("\nSeries A Confidence Scorer — TDD Anneal Cycles")
    print("="*60)

    results = {}
    for c in cycles_to_run:
        result = score_cycle(c)
        prev = results.get(c - 1)
        print_cycle_report(result, prev)
        results[c] = result

        if c == 5 and not args.cycle:
            apply_to_stage1()

    # Final summary table
    if len(results) > 1:
        print(f"\n{'='*60}")
        print("SUMMARY ACROSS ALL CYCLES")
        print(f"{'='*60}")
        print(f"  {'Cycle':<8} {'Pass%':<8} {'Precision':<12} {'Recall':<10} {'LOW catch'}")
        print(f"  {'-'*50}")
        for c, r in sorted(results.items()):
            print(f"  {c:<8} {r['pass_rate']:<8.0%} {r['precision']:<12.0%} {r['recall']:<10.0%} {r['low_catch_rate']:.0%}")


if __name__ == "__main__":
    main()
