"""Unit tests for series_a_pipeline name extraction logic."""
from series_a_pipeline import extract_company_name_from_title, _is_bad_extraction, _clean_extracted_name


def test_extract():
    cases = [
        # (title, expected_or_None_if_should_be_empty, label)
        ("Smart Robotics raises 10 million Series A - Interpack 2026", "Smart Robotics", "basic raises"),
        ("TextQL Raises $17M for Data Insights Platform", "TextQL", "Raises caps"),
        ("Lumio eyes Series A round after $4 million seed funding", "Lumio", "eyes verb"),
        ("GobbleCube snags $5M Series A", "GobbleCube", "snags verb"),
        ("Integrant locks in $20M Series A", "Integrant", "locks in verb"),
        ("Identity Authentication Startup Auth0 Raises $103M", "Auth0", "strip prefix"),
        ("AI Startup Anthropic Raises $5B", "Anthropic", "AI Startup prefix"),
        ("Fintech Startup Stripe Closes Series F", "Stripe", "Fintech prefix"),
        ("TechCrunch Mobility: Elon's admission", "", "colon column header"),
        ("Latest tech trends, technology in enterprises", "", "lowercase generic"),
        ("AI Market Watch's Post - LinkedIn", "", "post slug"),
        ("Warehoused Deal Closing for New Fund Managers", "", "fund managers"),
        ("Korean Startup Weekly News #115", "", "weekly news"),
        ("Elizabeth Dorman & Megan Gole's Era Raises $11M to Build", "Era", "possessive prefix"),
        ("Sam Altman's Worldcoin Closes $135M Series C", "Worldcoin", "founder possessive"),
    ]
    print("=== extract_company_name_from_title ===")
    all_pass = True
    for title, expected, label in cases:
        got = extract_company_name_from_title(title)
        match = (got == expected) if expected else (got == "")
        status = "PASS" if match else "FAIL"
        print(f"  {status}: {label!r:<30} -> {got!r:<30} (expected {expected!r})")
        if not match:
            all_pass = False
    print(f"\nextract: {'ALL PASS' if all_pass else 'FAILURES DETECTED'}")
    return all_pass


def test_is_bad():
    bad = [
        "TechCrunch Mobility: Elon's admission",
        "AI Market Watch's Post",
        "Latest tech trends",
        "Warehoused Deal Closing for New Fund Managers",
        "lowercase only",
    ]
    good = [
        "Stripe",
        "Smart Robotics",
        "TextQL",
        "OpenAI",
        "BLP Digital",
    ]
    print("\n=== _is_bad_extraction ===")
    all_pass = True
    for n in bad:
        if not _is_bad_extraction(n):
            print(f"  FAIL: {n!r} should be flagged bad")
            all_pass = False
        else:
            print(f"  PASS: {n!r} flagged bad")
    for n in good:
        if _is_bad_extraction(n):
            print(f"  FAIL: {n!r} wrongly flagged bad")
            all_pass = False
        else:
            print(f"  PASS: {n!r} not flagged")
    print(f"\nis_bad: {'ALL PASS' if all_pass else 'FAILURES DETECTED'}")
    return all_pass


if __name__ == "__main__":
    r1 = test_extract()
    r2 = test_is_bad()
    print(f"\n{'='*50}")
    print(f"OVERALL: {'ALL PASS' if r1 and r2 else 'FAILURES DETECTED'}")
    print(f"{'='*50}")
