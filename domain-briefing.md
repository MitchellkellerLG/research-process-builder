# Domain Briefing: Web Search Pattern Optimization for Company Intelligence

## Problem Class

**Generative/Classification hybrid** - generating search query templates that maximize the probability of finding specific factual data (names, amounts, relationships) in Google SERP snippets. The optimization target is GT (ground truth) score: did the snippet contain the correct answer?

## Recommended Approaches (prioritized)

### 1. Platform-Specific Site Operators (highest ROI for people categories)

The categories stuck below 0.3 GT (c_suite_technical, c_suite_commercial, customer_case_studies, partnerships_integrations) share a common failure: generic queries return homepage/career pages, not the data. Platform-specific operators bypass this.

**Key platforms by data type:**

| Data Type | High-Signal Platforms | Operator Pattern |
|---|---|---|
| Executive names | theorg.com, rocketreach.co, zoominfo.com, crunchbase.com | `site:theorg.com "{{company_name}}"` |
| Tech stack | stackshare.io, builtwith.com, wappalyzer.com | `site:stackshare.io "{{company_name}}"` |
| Partnerships | zapier.com/apps, marketplace pages | `site:zapier.com "{{company_name}}"` |
| Case studies | G2.com, trustradius.com, company /customers page | `site:g2.com "{{company_name}}" review` |
| Funding | crunchbase.com, pitchbook.com, techcrunch.com | `site:crunchbase.com "{{company_name}}" funding` |

**Why this works:** These platforms structure data in predictable formats. SERP snippets from theorg.com literally contain "CTO: [Name]" in the page title. Generic queries like "Company CTO" return noise.

### 2. DNS/Infrastructure Signals for Tech Stack & Partnerships

Google search alone caps at ~0.17 GT for tech_stack because technology choices aren't in web copy. Alternative signals:

- **DNS TXT records:** Companies add verification TXT records for every SaaS tool they use (Google Workspace, Cloudflare, Salesforce). A TXT record = confirmed usage.
- **Job posting requirements:** "Experience with Kubernetes, React, PostgreSQL" in job listings reveals actual stack. Query: `{{company_name}} jobs "experience with" OR "proficiency in" site:lever.co OR site:greenhouse.io OR site:ashbyhq.com`
- **GitHub org activity:** `site:github.com/{{company_name}}` reveals open-source stack choices
- **Segment/analytics pixels:** Network tab inspection reveals all integrated tools, but this needs page visits (not SERP-extractable)

### 3. Structured Data Patterns in Snippets

Google's featured snippets and knowledge panels extract structured data predictably. Queries that trigger these formats have higher GT:

- **"Who is the CTO of [Company]"** - triggers knowledge panel with name
- **"[Company] founded"** - triggers infobox with founding date, founders
- **"[Company] pricing plans"** - triggers table snippet from pricing pages
- **"[Company] vs [Competitor]"** - triggers comparison snippets with partnership/integration data

### 4. Temporal Anchoring for People Categories

Executive roles change. Queries without year anchoring return stale results:

- **Bad:** `{{company_name}} CTO`
- **Good:** `{{company_name}} CTO {{current_year}}` or `{{company_name}} "appointed" OR "named" CTO`
- **Best:** Combine platform + temporal: `site:linkedin.com/in "{{company_name}}" "Chief Technology Officer"` (LinkedIn profiles are current)

### 5. Negative Operator Hygiene

Many current patterns waste results on job listings and salary pages. Systematic exclusions:

```
-careers -jobs -salary -glassdoor -indeed -ziprecruiter
```

Apply to ALL people-finding queries. Currently only some variants use this.

## Known Pitfalls

1. **LinkedIn rate limiting:** `site:linkedin.com` queries get throttled after ~50/day. Use sparingly, rotate with other platforms.
2. **Disambiguation failures:** Companies with common names (Clay, Mercury, Grain, Ramp) need `{{category}}` or `{{domain}}` as disambiguator. Current config flags these but not all variants use the flag.
3. **Snippet extraction limits:** Google snippets are ~155 chars. If the answer isn't in those 155 chars, GT = 0 even if the page has the data. Prefer queries that surface the answer in the title or meta description.
4. **OR operator overload:** Too many OR clauses dilute relevance. Max 3-4 OR terms per query.
5. **Case study detection is fundamentally hard via SERP:** Most case studies are behind gated forms. The snippet says "Download our case study" not "Customer X achieved Y." Consider G2/TrustRadius reviews as proxy data.

## Benchmark Targets

From latest baseline (post-case-study-fields, 2026-03-13):

| Category | Current GT | Target | Strategy to Close Gap |
|---|---|---|---|
| leadership_people | 1.000 | 1.000 | Solved. Don't touch. |
| funding_financial | 0.656 | 0.750 | Add crunchbase site: variant |
| pricing_intelligence | 0.492 | 0.600 | Add "$" and "per month" triggers |
| founders_ceo | 0.433 | 0.600 | theorg.com + temporal anchoring |
| competitor_identification | 0.355 | 0.500 | G2 compare pages + "alternative to" |
| customer_case_studies | 0.128 | 0.300 | G2 reviews as proxy, site:{{domain}} /customers |
| c_suite_technical | 0.229 | 0.400 | theorg.com + "appointed CTO {{current_year}}" |
| c_suite_commercial | 0.216 | 0.400 | theorg.com + zoominfo for commercial roles |
| company_profile | 0.206 | 0.400 | crunchbase + pitchbook structured pages |
| tech_stack | 0.165 | 0.300 | stackshare + job posting extraction |
| partnerships_integrations | 0.149 | 0.300 | zapier.com/apps + site:{{domain}} /integrations |

## Priority Order for Next Autoresearch Run

1. **c_suite_technical** (0.229 -> 0.400) - theorg.com is likely a one-variant fix
2. **c_suite_commercial** (0.216 -> 0.400) - same theorg.com approach
3. **founders_ceo** (0.433 -> 0.600) - temporal anchoring on existing variants
4. **company_profile** (0.206 -> 0.400) - crunchbase structured pages
5. **customer_case_studies** (0.128 -> 0.300) - hardest, need G2/TrustRadius proxy

## Sources

- [Google Dorking Reference 2026](https://maxintel.org/google-dorking-reference-2026.html) - operator status
- [Find Company Tech Stack Tutorial](https://coresignal.com/blog/find-tech-stack-of-any-company/) - BuiltWith/Wappalyzer/DNS methods
- [StackWho Database](https://stackwho.com/) - 600K+ company tech stacks
- [How to Find Tech Stack Without Paying](https://bloomberry.com/blog/how-to-find-any-companys-tech-stack-without-paying-for-it/) - free methods
- [Clay Tech Stack Enrichment](https://www.clay.com/blog/how-to-find-a-companys-tech-stack-by-enrichment) - enrichment patterns
- [OSINT Advanced Searching](https://github.com/The-Osint-Toolbox/OSINT-Advanced-Searching) - operator reference
