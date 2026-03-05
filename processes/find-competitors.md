# Find Competitors Process

**Goal:** Given a company name and domain, find their top 5+ direct competitors with positioning context.
**Accuracy:** 93% validated across 11 companies (SpaceX to micro startups)
**Built:** 2026-03-04
**Methodology:** research-process-builder skill, 34 patterns tested across 2 iterations

## What "Good" Looks Like

- At least 3 named competitors (not just categories)
- Competitors are in the same market segment (not adjacent industries)
- At least one source is a structured review/data platform (G2, Capterra, Tracxn)
- Head-to-head positioning is surfaced (how they differ)
- Works for both well-known companies and obscure startups

## Preprocessing

### Step 0a: Name Disambiguation

Is the company name ambiguous? (6 chars or fewer, common word, famous namesake)

If YES: construct `disambiguated_name` = `[name] [category]` or use domain.
If NO: `disambiguated_name` = `company_name`.

### Step 0b: Company Size Detection

Search: `[company_name] company overview`

- 5+ third-party profiles → **Tier 1** → run all 12 steps
- 2-4 profiles → **Tier 2** → run Steps 1-8, skip 9-10
- 0-1 profiles → **Tier 3** → run Steps 1-6, then jump to Steps 9-12

---

## Steps

### Step 1: Direct Competitor Search

**Search:** `[disambiguated_name] competitors`
**Extract:** Every company named as a competitor. Note which source (G2, blog, Tracxn, etc.) mentioned each one.
**Quality:** 5 | **Consistency:** 4
**Notes:** Best single pattern. Triggers G2 comparison pages, CBInsights competitor lists, Tracxn profiles, and blog roundups simultaneously.

### Step 2: Alternatives Search

**Search:** `[disambiguated_name] alternatives`
**Extract:** Companies listed as alternatives. Often surfaces different competitors than Step 1 because "alternatives" attracts Capterra, Product Hunt, and "best alternatives to X" blog posts.
**Quality:** 5 | **Consistency:** 4
**Notes:** Overlaps ~50% with Step 1 results. The non-overlapping 50% is where the value is.

### Step 3: Category Market Map

**Search:** `best [category derived from profile data] tools 2026`
**Extract:** Full list of tools/companies in the category. Note market positioning of each.
**Quality:** 5 | **Consistency:** 4
**Notes:** Year modifier is mandatory. Without it, results are 2-3 years stale. This gives you the market map, not just head-to-head competitors.

### Step 4: Practitioner Opinions

**Search:** `who competes with [company_name]`
**Extract:** Companies mentioned in forum posts, Reddit-synthesis articles, and practitioner blogs.
**Quality:** 4 | **Consistency:** 4
**Notes:** Natural language query. Surfaces opinions from actual users and practitioners, not just marketing content. Different signal quality than platform data.

### Step 5: G2 Alternatives (SaaS only)

**Search:** `site:g2.com [company_name] alternatives`
**Extract:** G2 alternative listings with structured ratings and comparison data.
**Quality:** 5 | **Consistency:** 3
**When:** SaaS companies only. Skip for non-software companies (hardware, services, agencies).
**Notes:** Gold standard for B2B SaaS competitive data. If the company is on G2, this is the most reliable single source.

### Step 6: Reddit/Community Signal

**Search:** `[company_name] reddit discussion`
**Extract:** Community opinions on competitors, switching stories, comparison threads.
**Quality:** 4 | **Consistency:** 3
**Notes:** DO NOT use `site:reddit.com` — it's broken. This pattern without the site: operator surfaces Reddit-synthesis articles that aggregate community sentiment.

### Step 7: Head-to-Head Positioning

**Search:** `[company_name] vs [top competitor from Steps 1-6]`
**Extract:** Detailed comparison: pricing, features, ideal use case for each, switching stories.
**Quality:** 5 | **Consistency:** 4
**When:** Run after Steps 1-6 have identified at least one clear competitor.
**Notes:** This is where you get positioning depth, not just names.

### Step 8: Market Map Visual

**Search:** `[category] market map 2026`
**Extract:** Visual or structured market overview showing all players by segment/quadrant.
**Quality:** 4 | **Consistency:** 3
**When:** Category is clearly established from earlier steps.
**Notes:** Surfaces analyst reports, blog market maps, and industry overviews.

### Step 9: Disambiguation Variant (ambiguous names only)

**Search:** `[company_name] [category] competitors`
**Extract:** Same as Step 1 but with category qualifier to filter noise.
**Quality:** 4 | **Consistency:** 4
**When:** Company name is ambiguous and Steps 1-2 returned contaminated results.
**Notes:** Example: "Clay GTM competitors" vs just "Clay competitors" (which returns pottery results).

### Step 10: Domain-Anchored Search (Tier 3 or ambiguous names)

**Search:** `[domain] competitors`
**Extract:** Competitors identified via domain-based matching.
**Quality:** 3 | **Consistency:** 4
**When:** Name disambiguation isn't enough, or company is Tier 3 with minimal web presence.
**Notes:** Domain is unambiguous 100% of the time. Falls back to this when name-based patterns fail.

### Step 11: Similar Company Search (Tier 3 fallback)

**Search:** `[company_name] similar companies`
**Extract:** Companies described as similar by any source.
**Quality:** 3 | **Consistency:** 3
**When:** Tier 3 only. Primary steps returned fewer than 3 competitors.
**Notes:** Weaker signal than "competitors" or "alternatives" but catches companies that the structured platforms haven't indexed yet.

### Step 12: LinkedIn Competitor Signal (Tier 3 fallback)

**Search:** `[company_name] LinkedIn similar companies [category]`
**Extract:** Companies that appear alongside this company in LinkedIn recommendations or shared audiences.
**Quality:** 3 | **Consistency:** 3
**When:** Tier 3 only. All other steps returned thin results.
**Notes:** Last resort. LinkedIn's "similar companies" feature sometimes surfaces competitors that no other platform indexes.

---

## Kill List

DO NOT use these patterns. They look promising but waste searches:

| Pattern                                    | Why It Fails                                                            |
| ------------------------------------------ | ----------------------------------------------------------------------- |
| `[name] market landscape`                  | Returns unrelated industry research papers and market reports           |
| `[name] competitive intelligence`          | Attracts CI vendor marketing content, not actual competitor data        |
| `site:crunchbase.com [name] competitors`   | Description-based matching is wildly inaccurate                         |
| `[domain] competitors site:similarweb.com` | Traffic-based matching identifies audience overlap sites as competitors |
| `[name] rival companies`                   | Weaker duplicate of "competitors" with lower consistency                |

---

## Output Template

```
COMPETITORS (ranked by mention frequency across sources):
1. [Name] — [one-line positioning] — Sources: [G2, blog, Tracxn, etc.]
2. [Name] — [one-line positioning] — Sources: [...]
3. [Name] — [one-line positioning] — Sources: [...]
4. [Name] — [one-line positioning] — Sources: [...]
5. [Name] — [one-line positioning] — Sources: [...]

COMPETITIVE POSITIONING vs [Top Competitor]:
- [Company] wins on: [strengths]
- [Top Competitor] wins on: [strengths]
- Buyer deciding factor: [what matters most]

MARKET CATEGORY: [derived category name]
TOTAL COMPETITORS IDENTIFIED: [N]
CONFIDENCE: [High/Medium/Low] — [why]
```
