# Find Third-Party Profiles Process

**Goal:** Given a company name and domain, build a company fact sheet from structured data platforms (ZoomInfo, Crunchbase, LinkedIn, PitchBook, Tracxn).
**Accuracy:** 100% validated across 11 companies (SpaceX to micro startups)
**Built:** 2026-03-04
**Methodology:** research-process-builder skill, 18 patterns tested, 0 iterations needed

## What "Good" Looks Like

- Company description, category, and industry identified
- Employee count and funding data found (or confirmed as unavailable)
- At least 3 third-party platform profiles located
- Company size tier determined for routing downstream research
- For micro companies: existence confirmed even if profiles are thin

## Preprocessing

### Step 0a: Name Disambiguation

Is the company name ambiguous? (6 chars or fewer, common word, famous namesake)

If YES: construct `disambiguated_name` = `[name] [category]` or use domain.
If NO: `disambiguated_name` = `company_name`.

### Step 0b: Note on Size Detection

This process IS the size detection step. The results from Step 1 determine the company's tier. Count profiles found and set the tier before proceeding to other research processes.

---

## Steps

### Step 1: Multi-Platform Sweep

**Search:** `[disambiguated_name] company overview`
**Extract:** Every platform profile that appears. For each, extract: company description, category, employee count, funding, HQ location, founded year.
**Quality:** 5 | **Consistency:** 5
**Notes:** Best multi-platform sweep pattern. A single search returns 4-8 platform profiles simultaneously (ZoomInfo, Crunchbase, LinkedIn, PitchBook, Tracxn, Owler, CBInsights). Count the profiles to determine tier.

**After this step, set the tier:**

- 5+ profiles → Tier 1
- 2-4 profiles → Tier 2
- 0-1 profiles → Tier 3

### Step 2: Crunchbase (Funding Data)

**Search:** `site:crunchbase.com [company_name]`
**Extract:** Funding rounds (dates, amounts, investors), total raised, last round type, company description, category tags.
**Quality:** 5 | **Consistency:** 5
**Notes:** Gold standard for startup funding data. If gated, note "Crunchbase profile exists, data gated." Coverage is excellent for funded companies, poor for bootstrapped micro companies.

### Step 3: ZoomInfo (Company Intelligence)

**Search:** `site:zoominfo.com [company_name]`
**Extract:** Revenue estimate, employee count, tech stack signals, industry classification, HQ address, SIC/NAICS codes.
**Quality:** 5 | **Consistency:** 5
**Notes:** Best coverage across ALL company sizes. ZoomInfo indexes companies that Crunchbase and PitchBook miss entirely. Even 6-month-old startups show up. The only platform that reliably covers micro/bootstrapped companies.

### Step 4: PitchBook (Valuation and Sector)

**Search:** `site:pitchbook.com [company_name]`
**Extract:** Valuation, sector classification, comparable companies, analyst commentary, deal history.
**Quality:** 4 | **Consistency:** 4
**When:** Tier 1-2 only. PitchBook has poor coverage for micro companies.
**Notes:** Strongest for valuation data and sector classification. Comparable companies listed here are often different from G2-style competitors.

### Step 5: Tracxn (Early-Stage Indexing)

**Search:** `site:tracxn.com [company_name]`
**Extract:** Sector maps, competitor landscapes, growth signals, funding history, team size.
**Quality:** 4 | **Consistency:** 4
**When:** Tier 1-2. Moderate coverage for Tier 3.
**Notes:** Tracxn excels at early-stage company indexing. Their sector maps and competitor landscapes are particularly useful for understanding market positioning.

### Step 6: LinkedIn Company Profile

**Search:** `site:linkedin.com/company [company_name]`
**Extract:** Employee count, recent company posts, about section, specialties, headquarters, company size bracket.
**Quality:** 4 | **Consistency:** 4
**Notes:** Universal. Every company with employees has a LinkedIn page. The "about" section often has the clearest description of what the company actually does. Employee count here is more current than ZoomInfo.

### Step 7: Company Description (Tier 3 fallback)

**Search:** `[company_name] official website about`
**Extract:** Self-described company purpose, team, product description.
**Quality:** 3 | **Consistency:** 4
**When:** Primary steps (1-6) returned fewer than 3 profiles. Tier 3 companies.
**Notes:** Falls back to the company's own website to build the profile. Less structured than platform data but better than nothing.

### Step 8: Company Description Alternate (Tier 3 fallback)

**Search:** `[company_name] company description`
**Extract:** Any third-party description of what the company does.
**Quality:** 3 | **Consistency:** 3
**When:** Tier 3 only. Step 7 returned thin results.
**Notes:** Catches descriptions from directories, partner pages, and industry listings that the major platforms haven't indexed yet.

### Step 9: Founder/CEO Biographical Search (Tier 3 fallback)

**Search:** `[company_name] founded by [CEO name if known]`
**Extract:** Founder background, company origin story, founding date, initial product description.
**Quality:** 4 | **Consistency:** 3
**When:** Tier 3 only. CEO/founder name is known from earlier steps or provided as input.
**Notes:** Biographical results are surprisingly rich for obscure companies. Founder profiles on LinkedIn, podcast appearances, and conference talks surface company information that no platform has indexed.

### Step 10: Industry Directory Check (Tier 3 fallback)

**Search:** `[company_name] [category] company`
**Extract:** Any directory listings, industry association memberships, or niche platform profiles.
**Quality:** 3 | **Consistency:** 3
**When:** Tier 3 only. All other steps returned minimal results.
**Notes:** Niche industry directories (e.g., BuiltWith for tech companies, Clutch for agencies) sometimes have profiles that the big platforms don't.

---

## Kill List

DO NOT use these patterns:

| Pattern                       | Why It Fails                                                        |
| ----------------------------- | ------------------------------------------------------------------- |
| `site:apollo.io [name]`       | Data is gated. Returns SEO blog posts, not company profiles.        |
| `[name] annual report`        | Useless for private companies. Only public companies publish these. |
| `site:stackshare.io [name]`   | Only covers developer tools, not company intelligence.              |
| `site:web.archive.org [name]` | Archive.org doesn't expose snapshots to search crawlers.            |

---

## Platform Coverage Reference

| Platform   | Enterprise | Growth Startup | Early Startup    | Micro/Bootstrapped |
| ---------- | ---------- | -------------- | ---------------- | ------------------ |
| ZoomInfo   | Excellent  | Excellent      | Good             | Good               |
| Crunchbase | Excellent  | Excellent      | Good (if funded) | Poor               |
| PitchBook  | Excellent  | Excellent      | Moderate         | Poor               |
| Tracxn     | Good       | Excellent      | Good             | Moderate           |
| LinkedIn   | Excellent  | Excellent      | Good             | Good               |
| Owler      | Good       | Moderate       | Poor             | Poor               |
| CBInsights | Excellent  | Good           | Moderate         | Poor               |

**Key takeaway:** ZoomInfo + LinkedIn are the only platforms that reliably cover ALL company sizes.

---

## Output Template

```
COMPANY: [name]
DOMAIN: [domain]
TIER: [1/2/3 — based on profiles found]

DESCRIPTION: [one-liner from best source]
CATEGORY: [industry/sector classification]
FOUNDED: [year]
HQ: [city, state/country]
EMPLOYEES: [range]

FUNDING:
- Stage: [Seed/A/B/C/Public/Bootstrapped]
- Total raised: [$X]
- Last round: [$X, date, lead investor]
- Valuation: [$X or "not disclosed"]

PROFILES FOUND:
- ZoomInfo: [yes/no — URL if found]
- Crunchbase: [yes/no — URL if found]
- PitchBook: [yes/no — URL if found]
- Tracxn: [yes/no — URL if found]
- LinkedIn: [yes/no — URL if found]
- Other: [list any additional]

CONFIDENCE: [High/Medium/Low] — [why]
```
