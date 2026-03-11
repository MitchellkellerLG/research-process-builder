"""
Generate serper-patterns-people.md from people testing results.

Merges both people results files (round 1 + round 2 combo) and both configs
to produce ONE BEST pattern per category with full reference documentation.

Usage:
    py scripts/generate_people_doc.py
"""

import json
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
SEARCHES_DIR = SCRIPT_DIR.parent / "searches"

RESULT_FILES = [
    SEARCHES_DIR / "raw-results-people.json",
    SEARCHES_DIR / "raw-results-people-combo.json",
]

CONFIG_FILES = [
    SCRIPT_DIR / "people_patterns.json",
    SCRIPT_DIR / "people_combo_patterns.json",
]

OUTPUT_FILE = SEARCHES_DIR / "serper-patterns-people.md"

# Category display order (executive → management → specialist → creative)
CATEGORY_ORDER = [
    "founders_ceo",
    "c_suite_technical",
    "c_suite_commercial",
    "vp_sales_revenue",
    "vp_marketing_growth",
    "vp_engineering_product",
    "director_sales_bd",
    "director_marketing_content",
    "director_engineering_product",
    "head_of_department",
    "sales_ops_leads",
    "hr_people_talent",
    "finance_legal_ops",
    "technical_leads",
    "people_via_media",
    "people_via_platforms",
    "people_via_content",
]

# Human-readable category names
CATEGORY_NAMES = {
    "founders_ceo": "Founders / CEO / President",
    "c_suite_technical": "C-Suite Technical (CTO / CPO / CISO)",
    "c_suite_commercial": "C-Suite Commercial (CMO / CRO / CFO / COO)",
    "vp_sales_revenue": "VP Sales / Revenue / Business Development",
    "vp_marketing_growth": "VP Marketing / Growth / Demand Gen",
    "vp_engineering_product": "VP Engineering / Product / Design",
    "director_sales_bd": "Director Sales / BD / Partnerships",
    "director_marketing_content": "Director Marketing / Content / Demand Gen",
    "director_engineering_product": "Director Engineering / Product / Design",
    "head_of_department": "Head of Department (Growth / CS / Ops / Revenue)",
    "sales_ops_leads": "Sales Ops / SDR Managers / RevOps",
    "hr_people_talent": "HR / People / Talent Leadership",
    "finance_legal_ops": "Finance / Legal / Operations Leadership",
    "technical_leads": "Technical Leads / Staff Engineers / Architects",
    "people_via_media": "People Discovery via Media / Events",
    "people_via_platforms": "People Discovery via Data Platforms",
    "people_via_content": "People Discovery via Authored Content",
}

# What each category surfaces
CATEGORY_SURFACES = {
    "founders_ceo": "founder names, CEO identity, co-founder profiles, founding stories, media appearances",
    "c_suite_technical": "CTO, CPO, CISO names and profiles, technical leadership, architecture owners",
    "c_suite_commercial": "CMO, CRO, CFO, COO names and profiles, commercial leadership team",
    "vp_sales_revenue": "VP Sales, VP Revenue, VP BD names, sales leadership structure, partnership leads",
    "vp_marketing_growth": "VP Marketing, VP Growth names, marketing leadership, brand owners, demand gen leads",
    "vp_engineering_product": "VP Engineering, VP Product names, technical leadership below C-suite",
    "director_sales_bd": "Director of Sales, BD Directors, Partnership Directors, revenue team structure",
    "director_marketing_content": "Director of Marketing, Content Directors, Brand Directors, demand gen leads",
    "director_engineering_product": "Director of Engineering, Product Directors, Design Directors, platform leads",
    "head_of_department": "Department heads across Growth, CS, Ops, Revenue, Partnerships",
    "sales_ops_leads": "SDR/BDR Managers, Sales Managers, RevOps leads, Account Executive leadership",
    "hr_people_talent": "Head of Recruiting, VP People, Talent Acquisition leads, HR leadership",
    "finance_legal_ops": "VP Finance, VP Operations, General Counsel, Controller, financial leadership",
    "technical_leads": "Engineering Managers, Staff/Principal Engineers, Architects, Tech Leads",
    "people_via_media": "Anyone at the company who appears on podcasts, conferences, interviews, keynotes",
    "people_via_platforms": "Employee profiles via ZoomInfo, RocketReach, Wellfound, org chart data",
    "people_via_content": "Authors and contributors via company blogs, Medium, Substack, LinkedIn Pulse",
}


def load_results():
    """Load and merge all people result files."""
    all_results = []
    total_files = 0
    for fpath in RESULT_FILES:
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_results.extend(data)
                total_files += 1
                print(f"  Loaded {len(data)} results from {fpath.name}")
    return all_results, total_files


def load_templates():
    """Load template lookup from all config files."""
    templates = {}  # (cat_id, var_id) -> template
    for fpath in CONFIG_FILES:
        if not fpath.exists():
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            config = json.load(f)
        for cat in config["categories"]:
            for var in cat["variants"]:
                templates[(cat["id"], var["id"])] = var["template"]
    return templates


def analyze_patterns(results, templates):
    """Group results by (category, variant) and compute scores."""
    groups = {}  # (cat_id, var_id) -> {scores: {company: quality}, ...}

    for r in results:
        cat_id = r.get("category_id")
        var_id = r.get("variant_id")
        if not cat_id or not var_id:
            continue

        key = (cat_id, var_id)
        if key not in groups:
            groups[key] = {"scores": {}, "examples": []}

        company = r.get("company", "?")
        quality = r.get("scores", {}).get("quality", 0)
        groups[key]["scores"][company] = quality

        if r.get("top_results") and not groups[key]["examples"]:
            groups[key]["examples"] = r["top_results"][:3]

    # Compute aggregates per variant
    patterns = {}
    for (cat_id, var_id), data in groups.items():
        scores = data["scores"]
        if not scores:
            continue

        avg_q = sum(scores.values()) / len(scores)
        min_q = min(scores.values())
        max_q = max(scores.values())
        q4_count = sum(1 for v in scores.values() if v >= 4)
        consistency = q4_count / len(scores) * 5 if scores else 0

        if avg_q >= 4.0 and consistency >= 4.0:
            classification = "PRIMARY"
        elif avg_q >= 4.0 and consistency >= 3.0:
            classification = "ENRICHMENT"
        elif avg_q >= 3.0:
            classification = "FALLBACK"
        else:
            classification = "KILL"

        if cat_id not in patterns:
            patterns[cat_id] = []

        patterns[cat_id].append({
            "var_id": var_id,
            "template": templates.get((cat_id, var_id), "?"),
            "avg_q": round(avg_q, 1),
            "min_q": min_q,
            "max_q": max_q,
            "consistency": round(consistency, 1),
            "classification": classification,
            "scores": scores,
            "examples": data["examples"],
        })

    # Sort each category by avg_q desc, then consistency desc
    for cat_id in patterns:
        patterns[cat_id].sort(key=lambda x: (x["avg_q"], x["consistency"]), reverse=True)

    return patterns


def load_source_data():
    """Load source analysis for dominant domain info."""
    source_file = SEARCHES_DIR / "source-analysis.md"
    if not source_file.exists():
        return {}

    sources = {}
    current_cat = None

    with open(source_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("## "):
                current_cat = line[3:].strip()
                sources[current_cat] = {"primary": [], "secondary": []}
            elif current_cat and "| PRIMARY |" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    domain = parts[1].strip()
                    sources[current_cat]["primary"].append(domain)
            elif current_cat and "| SECONDARY |" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    domain = parts[1].strip()
                    sources[current_cat]["secondary"].append(domain)

    return sources


def generate_doc(patterns, templates, sources, total_results):
    """Generate the markdown document."""
    lines = []

    # Header
    lines.append("# serper people-finding patterns — validated reference")
    lines.append("")
    lines.append(f"**validated:** {datetime.now().strftime('%Y-%m-%d')} (round 1 baseline + round 2 combo optimization)")
    lines.append(f"**total queries tested:** {total_results} (470 round 1 + 240 round 2 combos)")
    lines.append(f"**total cost:** ~${total_results * 0.0001:.2f}")
    lines.append("**cost per search:** $0.0001 via Serper vs $2-5 per lead via data vendors")
    lines.append(f"**categories:** {len(CATEGORY_ORDER)} role levels from founder to individual contributor")
    lines.append(f"**PRIMARY patterns:** {sum(1 for cat in patterns.values() for p in cat if p['classification'] == 'PRIMARY')} variants across {sum(1 for cat_id in CATEGORY_ORDER if any(p['classification'] == 'PRIMARY' for p in patterns.get(cat_id, [])))}/{len(CATEGORY_ORDER)} categories")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Usage section
    lines.append("## how to use in Clay")
    lines.append("")
    lines.append("each pattern below is a Clay HTTP API column:")
    lines.append("")
    lines.append("1. add column > HTTP API")
    lines.append("2. method: `POST`")
    lines.append("3. URL: `https://google.serper.dev/search`")
    lines.append("4. headers: `X-API-KEY: {{SERPER_API_KEY}}` and `Content-Type: application/json`")
    lines.append('5. body: `{"q": "[pattern with your variables]", "gl": "us", "hl": "en", "num": 10}`')
    lines.append("6. map response: `{{http_response.organic[0].title}}` or `{{http_response.organic[0].link}}`")
    lines.append("")
    lines.append("**variables:** replace `{{company_name}}` with column reference `/Company Name/`, `{{domain}}` with `/Domain/`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Key insights section
    lines.append("## key findings from 710 searches")
    lines.append("")
    lines.append("1. **LinkedIn profile searches dominate** — `site:linkedin.com/in` is the most reliable source across all role categories")
    lines.append("2. **General keywords beat exact titles** — `\"VP\" sales OR revenue` outperforms `\"VP Sales\"` because it catches title variations")
    lines.append("3. **Full title phrases work for C-suite** — `\"chief technology\" OR \"chief product\"` beats `CTO OR CPO` (less ambiguity)")
    lines.append('4. **Exclusion operators are essential** — `-jobs -careers -salary` prevents job board noise from dominating results')
    lines.append("5. **ZoomInfo is the only reliable data platform** — Apollo, TheOrg, AngelList all fail for smaller companies")
    lines.append("6. **Company size matters** — patterns that work for SpaceX/ClickUp may fail for startups like Lovable/Cursor")
    lines.append("7. **Media patterns surface undiscoverable names** — podcast/interview queries find people not in any database")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Category sections
    for cat_id in CATEGORY_ORDER:
        cat_patterns = patterns.get(cat_id, [])
        cat_name = CATEGORY_NAMES.get(cat_id, cat_id)
        surfaces = CATEGORY_SURFACES.get(cat_id, "")

        lines.append(f"## {cat_name}")
        lines.append("")

        if not cat_patterns:
            lines.append("*No tested patterns for this category.*")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        # Get best pattern
        best = cat_patterns[0]
        primary_patterns = [p for p in cat_patterns if p["classification"] == "PRIMARY"]
        enrichment_patterns = [p for p in cat_patterns if p["classification"] == "ENRICHMENT"]
        fallback_patterns = [p for p in cat_patterns if p["classification"] == "FALLBACK"]
        kill_patterns = [p for p in cat_patterns if p["classification"] == "KILL"]

        # Dominant sources
        src = sources.get(cat_id, {})
        primary_sources = src.get("primary", [])
        secondary_sources = src.get("secondary", [])

        # Best pattern block
        lines.append(f"**best:** `{best['template']}`")
        lines.append(f"**avg Q:** {best['avg_q']} | **min Q:** {best['min_q']} | tested across {len(best['scores'])} companies")
        lines.append(f"**what it surfaces:** {surfaces}")

        # Clay body example
        clay_q = best["template"].replace("{{company_name}}", "/Company Name/").replace("{{domain}}", "/Domain/").replace("{{category}}", "/Category/")
        lines.append(f'**Clay body:** `{{"q": "{clay_q}", "gl": "us", "hl": "en", "num": 10}}`')

        # Runner-up
        if len(cat_patterns) > 1:
            runner = cat_patterns[1]
            lines.append(f"**runner-up:** `{runner['template']}` (Q{runner['avg_q']})")

        # Source info
        if primary_sources:
            lines.append(f"**dominant sources:** {', '.join(primary_sources)}")
        elif secondary_sources:
            lines.append(f"**useful sources:** {', '.join(secondary_sources)}")

        lines.append("")

        # Per-company scores for best pattern
        if best["scores"]:
            lines.append("**per-company scores:**")
            for company, score in sorted(best["scores"].items()):
                indicator = "OK" if score >= 4 else ("WEAK" if score >= 3 else "FAIL")
                lines.append(f"- {company}: Q{score} {indicator}")
            lines.append("")

        # Additional PRIMARY patterns
        if len(primary_patterns) > 1:
            lines.append(f"### also PRIMARY ({len(primary_patterns) - 1} more)")
            lines.append("")
            for p in primary_patterns[1:]:
                scores_str = ", ".join(f"{c} Q{q}" for c, q in sorted(p["scores"].items()))
                lines.append(f"- `{p['template']}` — avg Q{p['avg_q']} ({scores_str})")
            lines.append("")

        # ENRICHMENT patterns
        if enrichment_patterns:
            lines.append(f"### ENRICHMENT ({len(enrichment_patterns)})")
            lines.append("")
            for p in enrichment_patterns:
                lines.append(f"- `{p['template']}` — avg Q{p['avg_q']}")
            lines.append("")

        # FALLBACK patterns (condensed)
        if fallback_patterns:
            lines.append(f"### FALLBACK ({len(fallback_patterns)})")
            lines.append("")
            for p in fallback_patterns[:3]:
                lines.append(f"- `{p['template']}` — avg Q{p['avg_q']}")
            if len(fallback_patterns) > 3:
                lines.append(f"- *...and {len(fallback_patterns) - 3} more*")
            lines.append("")

        # KILL patterns (just count)
        if kill_patterns:
            lines.append(f"### KILL ({len(kill_patterns)} patterns below Q3.0)")
            lines.append("")
            for p in kill_patterns[:3]:
                lines.append(f"- ~~`{p['template']}`~~ — avg Q{p['avg_q']}")
            if len(kill_patterns) > 3:
                lines.append(f"- *...and {len(kill_patterns) - 3} more*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Summary table at the end
    lines.append("## quick reference — ONE BEST per category")
    lines.append("")
    lines.append("| Category | Best Pattern | Avg Q | Status |")
    lines.append("|----------|-------------|-------|--------|")

    for cat_id in CATEGORY_ORDER:
        cat_patterns = patterns.get(cat_id, [])
        cat_name = CATEGORY_NAMES.get(cat_id, cat_id)
        if cat_patterns:
            best = cat_patterns[0]
            status = best["classification"]
            lines.append(f"| {cat_name} | `{best['template']}` | {best['avg_q']} | {status} |")
        else:
            lines.append(f"| {cat_name} | — | — | UNTESTED |")

    lines.append("")

    return "\n".join(lines)


def main():
    print("Loading results...")
    results, total_files = load_results()
    print(f"  Total: {len(results)} results from {total_files} files")

    print("Loading templates...")
    templates = load_templates()
    print(f"  Total: {len(templates)} template variants")

    print("Analyzing patterns...")
    patterns = analyze_patterns(results, templates)
    total_categories = len(patterns)
    primary_count = sum(1 for cat in patterns.values() for p in cat if p["classification"] == "PRIMARY")
    print(f"  {total_categories} categories, {primary_count} PRIMARY patterns")

    print("Loading source analysis...")
    sources = load_source_data()

    print("Generating document...")
    doc = generate_doc(patterns, templates, sources, len(results))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"\nGenerated: {OUTPUT_FILE}")
    print(f"  {len(doc)} chars, {doc.count(chr(10))} lines")


if __name__ == "__main__":
    main()
