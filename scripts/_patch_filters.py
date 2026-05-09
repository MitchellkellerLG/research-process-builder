"""One-shot patch: replace Series-A-only filter block with all-rounds filter."""
import re

path = "scripts/series_a_pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Normalize line endings for matching
content_lf = content.replace("\r\n", "\n")

OLD = (
    "            title_has_series_a = bool(SERIES_A_PATTERN.search(title))\n"
    "            title_has_hard_non_a = bool(NON_SERIES_A.search(title))\n"
    "            title_has_soft_non_a = bool(SOFT_NON_A.search(title))\n"
    "            has_series_a = bool(SERIES_A_PATTERN.search(combined))\n"
    "            has_hard_non_a = bool(NON_SERIES_A.search(combined))\n"
    "            snippet_has_hard_non_a = bool(NON_SERIES_A.search(snippet))\n"
    "\n"
    "            if title_has_hard_non_a:\n"
    '                filtered_out.append({"title": title[:80], "reason": "non-Series A in title", "url": url})\n'
    "                continue\n"
    "            if title_has_soft_non_a and not title_has_series_a:\n"
    '                filtered_out.append({"title": title[:80], "reason": "Seed/Growth in title, no Series A", "url": url})\n'
    "                continue\n"
    "            if has_hard_non_a and not has_series_a:\n"
    '                filtered_out.append({"title": title[:80], "reason": "non-Series A round detected", "url": url})\n'
    "                continue\n"
)

NEW = (
    "            title_has_invalid = bool(INVALID_ROUND.search(title))\n"
    "            has_invalid = bool(INVALID_ROUND.search(combined))\n"
    "            has_funding_signal = bool(FUNDING_ROUND_PATTERN.search(combined))\n"
    "            has_amount = bool(AMOUNT_PATTERN.search(combined))\n"
    "\n"
    "            if title_has_invalid:\n"
    '                filtered_out.append({"title": title[:80], "reason": "acquisition/IPO/debt/grant in title", "url": url})\n'
    "                continue\n"
    "            if has_invalid and not has_funding_signal:\n"
    '                filtered_out.append({"title": title[:80], "reason": "non-funding event detected", "url": url})\n'
    "                continue\n"
)

if OLD in content_lf:
    patched = content_lf.replace(OLD, NEW)
    # Also fix remaining Series-A references in the block below
    patched = patched.replace(
        "# Roundup articles: non-A in snippet but Series A mentioned elsewhere → still non-A article\n"
        "            if snippet_has_hard_non_a and not title_has_series_a:\n"
        '                filtered_out.append({"title": title[:80], "reason": "non-Series A in snippet, no Series A in title", "url": url})\n'
        "                continue\n"
        "            if not has_series_a and not re.search(\n"
        r"                r'(?:raises?|raised|secures?|closes?)\s+[\$€£]', combined, re.IGNORECASE" + "\n"
        "            ):\n"
        '                filtered_out.append({"title": title[:80], "reason": "no Series A and no funding amount", "url": url})\n'
        "                continue\n",
        "            if not has_funding_signal and not has_amount:\n"
        '                filtered_out.append({"title": title[:80], "reason": "no funding signal and no amount", "url": url})\n'
        "                continue\n",
    )
    # Fix round_type detection in candidates builder
    patched = patched.replace(
        '            has_series_a_combined = bool(SERIES_A_PATTERN.search(combined))',
        '            round_match = ROUND_TYPE_EXTRACT.search(combined)\n'
        '            detected_round_type = round_match.group(0).title() if round_match else "Unknown"',
    )
    patched = patched.replace(
        '            if has_series_a_combined:\n                data_completeness += 1',
        '            if round_match:\n                data_completeness += 1',
    )
    patched = patched.replace(
        '"round_type": "Series A" if has_series_a_combined else "Unknown"',
        '"round_type": detected_round_type',
    )
    # Fix extraction prompt
    patched = patched.replace(
        'Extract Series A funding data from this article.',
        'Extract funding round data from this article.',
    )
    patched = patched.replace(
        '- If this is NOT actually a Series A funding announcement, set company_name to "NOT_SERIES_A"',
        '- If this is NOT a funding announcement (e.g. earnings, acquisition, job post), set company_name to "NOT_FUNDING_EVENT"',
    )
    # Fix post_extract_filter sentinel
    patched = patched.replace(
        'if extracted.get("company_name") == "NOT_SERIES_A":',
        'if extracted.get("company_name") in ("NOT_SERIES_A", "NOT_FUNDING_EVENT"):',
    )
    # Fix build_enriched_record default round type
    patched = patched.replace(
        '"round_type": company.get("round_type", "Series A"),',
        '"round_type": company.get("round_type", "Unknown"),',
    )
    patched = patched.replace(
        '"round_type": company.get("round_type", "Series A"),\n            "source_url": company["best_source_url"]',
        '"round_type": company.get("round_type", "Unknown"),\n            "source_url": company["best_source_url"]',
    )
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(patched)
    print("PATCH OK")
else:
    print("OLD block not found — showing actual lines 145-175:")
    for i, line in enumerate(content_lf.split("\n")[144:175], start=145):
        print(f"  {i}: {repr(line)}")
