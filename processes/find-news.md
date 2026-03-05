# Find Recent News Process

**Goal:** Given a company name and domain, surface everything newsworthy in the last 6-12 months. Partnerships, expansions, acquisitions, funding, product launches, leadership changes, controversies, awards.
**Accuracy:** 90% validated across 11 companies (SpaceX to micro startups)
**Built:** 2026-03-04
**Methodology:** research-process-builder skill, 36 patterns tested across 2 iterations

## What "Good" Looks Like

- Multiple event types captured (not just one category of news)
- Events are from the last 6-12 months (not stale)
- Sources are credible (news outlets, company blogs, wire services)
- Company trajectory signal is derivable from the collection of events
- For Tier 3 companies: absence of news is documented as a signal, not ignored

## Preprocessing

### Step 0a: Name Disambiguation

Is the company name ambiguous? (6 chars or fewer, common word, famous namesake)

If YES: construct `disambiguated_name` = `[name] [category]` or use domain.
If NO: `disambiguated_name` = `company_name`.

### Step 0b: Company Size Detection

Search: `[company_name] company overview`

- 5+ third-party profiles → **Tier 1** → run all 12 steps
- 2-4 profiles → **Tier 2** → run Steps 1-8
- 0-1 profiles → **Tier 3** → run Steps 1-4, then jump to Steps 9-12

---

## Steps

### Step 1: General News Sweep

**Search:** `[disambiguated_name] recent news`
**Extract:** Scan for ALL event types: acquisitions, partnerships, funding, product launches, leadership moves, expansions, controversies, awards, layoffs.
**Quality:** 4 | **Consistency:** 4 | **Freshness:** 5
**Notes:** Most reliable general pattern. Cast the widest net first, then drill into specific event types.

### Step 2: M&A Activity

**Search:** `[company_name] acquisition`
**Extract:** Has the company acquired anyone? Has the company been acquired? Deal terms, strategic rationale.
**Quality:** 5 | **Consistency:** 5 | **Freshness:** 5
**Notes:** Best single news pattern across all company sizes. Catches both directions ("Company acquired X" and "Company was acquired by Y"). Works from SpaceX to The Kiln.

### Step 3: Partnership and Integration Intel

**Search:** `[company_name] partnership`
**Extract:** Strategic alliances, integration announcements, channel partnerships, co-marketing deals, ecosystem plays.
**Quality:** 4 | **Consistency:** 4 | **Freshness:** 3
**Notes:** Partnerships signal company trajectory and ecosystem positioning. A company announcing 5 integrations is in growth mode. A company with zero partnerships may be isolated.

### Step 4: Expansion and Growth Signals

**Search:** `[company_name] expansion OR "new office" OR "new market"`
**Extract:** Geographic expansion, new market entry, office openings, international launches, new verticals.
**Quality:** 4 | **Consistency:** 3 | **Freshness:** 4
**Notes:** Physical expansion signals are high-confidence growth indicators. Opening a London office = serious about EMEA. Entering healthcare = vertical expansion.

### Step 5: Leadership and Strategic Narrative

**Search:** `[company_name] CEO interview`
**Extract:** CEO/founder quotes about company direction, growth plans, market positioning. Also catches leadership changes, new C-suite hires, board appointments.
**Quality:** 4 | **Consistency:** 4 | **Freshness:** 3
**Notes:** Underrated. CEO interviews contain strategic narrative that press releases don't. Look for quotes about future direction, not just past achievements.

### Step 6: Product and Launch News

**Search:** `[company_name] launches OR "new feature" OR "product update" 2025 2026`
**Extract:** Product launches, major feature releases, platform updates, version announcements, pricing changes.
**Quality:** 4 | **Consistency:** 3 | **Freshness:** 5
**Notes:** Year range ensures freshness. Product velocity is a health signal. Companies shipping features are alive and investing.

### Step 7: Year-Anchored News

**Search:** `[company_name] news 2026`
**Extract:** Anything from the current year that Steps 1-6 missed.
**Quality:** 4 | **Consistency:** 3 | **Freshness:** 5
**Notes:** Broad net with year filter. Supplements Step 1. Strong for Tier 1 brands where there's a lot of coverage.

### Step 8: Funding Activity

**Search:** `[company_name] funding round 2025 2026`
**Extract:** Last round date, amount raised, lead investor, valuation, round type (seed, A, B, etc.).
**Quality:** 4 | **Consistency:** 3 | **Freshness:** 5
**Notes:** Funding recency is a major health signal. Raised 6 months ago = growth mode. Raised 3 years ago with no new round = either profitable or struggling. No funding ever = bootstrapped or pre-revenue.

### Step 9: Tech Press Deep-Dive (Tier 1 only)

**Search:** `[company_name] site:techcrunch.com`
**Extract:** TechCrunch coverage. Funding announcements, product launches, industry analysis.
**Quality:** 4 | **Consistency:** 3 | **Freshness:** 4
**When:** Tier 1 (VC-backed startups with press coverage). Skip for Tier 2-3.

**Supplement:** `[company_name] site:venturebeat.com`
**When:** AI and enterprise SaaS companies specifically. VentureBeat has better coverage than TechCrunch for this segment.

**Supplement:** `[company_name] revenue growth`
**When:** Companies that publicly disclose ARR/revenue figures.

### Step 10: Activity Signal via Social (Tier 3 fallback)

**Search:** `[company_name] LinkedIn posts recent`
**Extract:** Recent LinkedIn activity from company page or founders. Posting frequency, topic focus, engagement levels.
**Quality:** 3 | **Consistency:** 3 | **Freshness:** 4
**When:** Tier 3 only. Primary news steps returned thin/no results.
**Notes:** For companies with no press coverage, social activity is the best proxy for "are they alive and active?"

### Step 11: Hiring Signal (Tier 3 fallback)

**Search:** `[company_name] hiring`
**Extract:** Open positions, hiring velocity, roles being filled (engineering = building, sales = scaling, support = retention).
**Quality:** 3 | **Consistency:** 4 | **Freshness:** 4
**When:** Tier 3 only. Company has minimal press coverage.
**Notes:** Hiring is the strongest company health proxy for obscure companies. A company with 5 open roles is alive and growing. Zero open roles for 6+ months is a warning sign.

### Step 12: Existence Verification (Tier 3 fallback)

**Search:** `[domain]` (bare domain search)
**Extract:** Confirm the company still exists and the website is live. Check for any mentions at all.
**Quality:** 3 | **Consistency:** 5 | **Freshness:** 3
**When:** Tier 3 only. All other steps returned near-zero results.

**Supplement:** `[company_name] blog post`
**Extract:** Self-published content. A recent blog post = active company.

**Key insight:** For companies with no press coverage, the ABSENCE of results from Steps 1-8 is itself a signal. Document it. "No news coverage found" is a finding, not a failure.

---

## Kill List

DO NOT use these patterns:

| Pattern                                          | Why It Fails                                        |
| ------------------------------------------------ | --------------------------------------------------- |
| `site:businessinsider.com [name]`                | Zero results for all startups tested                |
| `site:reuters.com [name]`                        | Useless below unicorn tier                          |
| `[name] breaking news`                           | Identical results to plain "news" — wastes a search |
| `[name] launch`                                  | Ambiguous (SpaceX literally launches rockets)       |
| `site:crunchbase.com/organization [name]`        | Returns data directory page, not news               |
| `[name] job openings 2026` with generic category | Too broad, returns job board SEO pages              |

---

## Output Template

```
RECENT NEWS (last 6-12 months):

[Date/Recency] — [EVENT TYPE] — [Headline/summary] — [Source]
[Date/Recency] — [EVENT TYPE] — [Headline/summary] — [Source]
[Date/Recency] — [EVENT TYPE] — [Headline/summary] — [Source]
...

EVENT TYPES DETECTED:
- Acquisitions: [yes/no — details]
- Partnerships: [yes/no — details]
- Funding: [yes/no — details]
- Product launches: [yes/no — details]
- Expansion/new offices: [yes/no — details]
- Leadership changes: [yes/no — details]
- Controversies: [yes/no — details]
- Awards/recognition: [yes/no — details]

COMPANY TRAJECTORY: [Growing / Stable / Declining / Pivoting / Unknown]
EVIDENCE: [2-3 sentences explaining trajectory assessment]
CONFIDENCE: [High/Medium/Low] — [why]
```
