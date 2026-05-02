"""
Semantic Domain Validation Test

Tests validate_domain_semantic() against 5 cases:
  1. Correct   — domain matches article, no correction needed
  2. Wrong+fix — article hyperlinks company to a different domain
  3. Wrong+rej — article describes wrong company entirely, no correction
  4. Unclear   — ambiguous article, no confident match possible
  5. Hyperlink — company name is a markdown hyperlink → extract domain

Usage: py scripts/test_semantic_validation.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir.parent / ".env")
load_dotenv(_script_dir.parent.parent / ".env", override=False)
load_dotenv(Path.home() / ".env", override=False)

sys.path.insert(0, os.environ.get("SHARED_SCRIPTS_PATH", str(_script_dir)))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not set")
    sys.exit(1)

# Import the pipeline class so we get the real method
sys.path.insert(0, str(_script_dir))
from pipeline_base import ResearchPipeline


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

CASES = [
    {
        "name": "correct — domain matches article",
        "source_url": "https://finsmes.com/zenskar-raises-series-a",
        "company_name": "Zenskar",
        "domain": "zenskar.com",
        "article": (
            "Zenskar, a revenue automation platform for SaaS companies, has raised $20M "
            "in a Series A round led by Tiger Global. The New York-based startup helps "
            "subscription businesses automate their billing and revenue recognition. "
            "Founded in 2022, Zenskar (zenskar.com) serves over 200 enterprise clients. "
            "The funds will be used to expand the engineering team and accelerate product development."
        ),
        "expected_status": "Correct",
    },
    {
        "name": "wrong+fix — article hyperlinks correct domain",
        "source_url": "https://thesaasnews.com/axle-ai-raises-series-a",
        "company_name": "Axle AI",
        "domain": "axle.ai",
        "article": (
            "[Axle AI](https://axleai.com) has secured $8M in Series A funding. "
            "The Boston-based media management platform helps studios and broadcasters "
            "organize video assets using artificial intelligence. "
            "Investors include Accel Partners and Point Nine Capital. "
            "CEO Jake Reisner said the funding will accelerate go-to-market expansion."
        ),
        "expected_status": "Wrong",
        "expected_domain": "axleai.com",
    },
    {
        "name": "wrong+rej — resolver returned news site domain",
        "source_url": "https://techcrunch.com/mosaic-raises-30m",
        "company_name": "Mosaic",
        "domain": "techcrunch.com",
        "article": (
            "Mosaic, a financial planning platform for mid-market companies, has raised $30M "
            "in Series B funding. The San Francisco startup replaces spreadsheet-based FP&A "
            "with real-time financial modeling. Lead investors include General Atlantic. "
            "CEO Bijan Moallemi said the company plans to double headcount by year end."
        ),
        "expected_status": "Wrong",
    },
    {
        "name": "unclear — generic article, no domain signal",
        "source_url": "https://venturebeat.com/startup-funding-roundup",
        "company_name": "DataStack",
        "domain": "datastack.io",
        "article": (
            "Several startups announced funding this week. A data infrastructure company "
            "raised $15M to expand its cloud operations platform. The round was led by "
            "Sequoia Capital. The startup plans to use the funds to hire engineers and "
            "expand into new markets. Further details were not disclosed."
        ),
        "expected_status": "Unclear",
    },
    {
        "name": "hyperlink — company name linked to correct domain",
        "source_url": "https://eu-startups.com/keepit-raises-series-b",
        "company_name": "Keepit",
        "domain": "keep.it",
        "article": (
            "[Keepit](https://www.keepit.com) has raised €40M in a Series B round "
            "to expand its cloud-to-cloud backup platform across Europe and North America. "
            "The Danish SaaS company protects Microsoft 365, Google Workspace, and Salesforce data. "
            "Founded in 2007, Keepit serves over 7,500 businesses globally. "
            "The round was led by Verdane with participation from Lundingruppen."
        ),
        "expected_status": "Wrong",
        "expected_domain": "keepit.com",
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_tests():
    pipeline = ResearchPipeline.__new__(ResearchPipeline)

    passed = 0
    failed = 0

    for case in CASES:
        name = case["name"]
        result = pipeline.validate_domain_semantic(
            source_url=case["source_url"],
            company_name=case["company_name"],
            domain=case["domain"],
            raw_article_text=case["article"],
        )

        status = result.get("status", "")
        correct_domain = result.get("correctDomain", "")
        reason = result.get("reason", "")

        status_ok = status == case["expected_status"]
        domain_ok = True
        if "expected_domain" in case:
            domain_ok = correct_domain == case["expected_domain"]

        ok = status_ok and domain_ok
        marker = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        print(f"\n[{marker}] {name}")
        print(f"  status:    got={status!r}  want={case['expected_status']!r}  {'OK' if status_ok else 'MISMATCH'}")
        if "expected_domain" in case:
            print(f"  domain:    got={correct_domain!r}  want={case['expected_domain']!r}  {'OK' if domain_ok else 'MISMATCH'}")
        print(f"  reason:    {reason}")

    print(f"\n{'='*50}")
    print(f"  {passed}/{len(CASES)} passed  |  {failed} failed")
    print(f"{'='*50}")
    return failed == 0


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
