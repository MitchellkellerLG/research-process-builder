# Find Reviews Process

**Goal:** Given a company name and domain, surface customer sentiment, pain points, employee satisfaction, and product quality signals.
**Accuracy:** 95% validated across 11 companies (SpaceX to micro startups)
**Built:** 2026-03-04
**Methodology:** research-process-builder skill, 35 patterns tested across 2 iterations

## What "Good" Looks Like

- Customer sentiment identified (positive/mixed/negative)
- Specific pain points surfaced (not just star ratings)
- At least one structured review platform found (G2, Trustpilot, Glassdoor)
- Employee health signal included (Glassdoor)
- Both praise and complaints captured for balanced view

## Preprocessing

### Step 0a: Name Disambiguation

Is the company name ambiguous? (6 chars or fewer, common word, famous namesake)

If YES: construct `disambiguated_name` = `[name] [category]` or use domain.
If NO: `disambiguated_name` = `company_name`.

### Step 0b: Company Size Detection

Search: `[company_name] company overview`

- 5+ third-party profiles → **Tier 1** → run all 12 steps
- 2-4 profiles → **Tier 2** → run Steps 1-9
- 0-1 profiles → **Tier 3** → run Steps 1-5, then Steps 10-12

---

## Steps

### Step 1: General Review Sweep

**Search:** `[disambiguated_name] review 2026`
**Extract:** Overall sentiment, recurring praise themes, recurring complaint themes, platforms mentioned.
**Quality:** 5 | **Consistency:** 5
**Notes:** Best single pattern in the entire review stack. The year qualifier is the highest-leverage modifier. Without it, you get 3-year-old reviews. With it, you get current editorial deep-dives and recent platform reviews.

### Step 2: Complaints and Pain Points

**Search:** `[disambiguated_name] complaints`
**Extract:** Specific complaints, common frustrations, deal-breakers, support issues.
**Quality:** 5 | **Consistency:** 4
**Notes:** Most underrated pattern. Surfaces the pain points that polished review platforms hide. Where Step 1 gives you the marketing-friendly version, this gives you the real one.

### Step 3: Employee Health Signal

**Search:** `[company_name] glassdoor reviews`
**Extract:** Overall rating (X/5), CEO approval %, top pros, top cons, culture themes.
**Quality:** 5 | **Consistency:** 4
**Notes:** Required for hiring intel, company culture assessment, and "is this company healthy" signals. A company with 2.5/5 Glassdoor and declining CEO approval is in trouble regardless of what their marketing says.

### Step 4: Editorial Deep-Dives

**Search:** `[company_name] honest review`
**Extract:** Balanced, long-form assessments. Look for specific use case recommendations (good for X, bad for Y).
**Quality:** 4 | **Consistency:** 4
**Notes:** Surfaces editorial reviews from bloggers and industry analysts who tested the product. Different signal than platform star ratings.

### Step 5: Quick Rating Snapshot

**Search:** `[company_name] rating`
**Extract:** Numerical ratings across platforms (G2 score, Trustpilot score, app store ratings).
**Quality:** 4 | **Consistency:** 4
**Notes:** Fast benchmarking. If G2 says 4.5/5 and Trustpilot says 2.1/5, there's a B2B vs B2C sentiment split worth investigating.

### Step 6: B2B SaaS Reviews (B2B companies)

**Search:** `[company_name] reviews site:g2.com`
**Extract:** G2 rating, review count, category ranking, top pros/cons from verified buyers.
**Quality:** 5 | **Consistency:** 4
**When:** B2B SaaS companies. Skip for B2C, consumer, or non-software.
**Notes:** Structured ratings with verified buyer reviews. Gold standard for B2B.

### Step 7: Consumer Reviews (B2C companies)

**Search:** `[company_name] reviews site:trustpilot.com`
**Extract:** Trustpilot rating, review count, recent review themes, response rate from company.
**Quality:** 5 | **Consistency:** 4
**When:** B2C or consumer-facing companies. Skip for pure B2B.
**Notes:** Customer experience reviews. Company response rate is itself a signal.

### Step 8: Community Adoption Signal (Startups / Dev Tools)

**Search:** `[company_name] reviews site:producthunt.com`
**Extract:** Product Hunt score, upvotes, maker responses, early-user feedback.
**Quality:** 4 | **Consistency:** 3
**When:** Startups and developer tools. Skip for enterprise or legacy companies.
**Notes:** Community adoption signal. A high Product Hunt score with active maker engagement = healthy early-stage company.

### Step 9: Enterprise Reviews (Enterprise B2B only)

**Search:** `[company_name] reviews site:gartner.com peer insights`
**Extract:** Gartner Peer Insights rating, deployment feedback, enterprise buyer recommendations.
**Quality:** 5 | **Consistency:** 3
**When:** Enterprise B2B companies (50+ employee customers, 6-figure deals).

**Supplement:** `[company_name] reviews site:peerspot.com`
**Extract:** Deployment and ROI focused reviews, implementation complexity, support quality.
**Notes:** Enterprise buyer reviews with deployment context. PeerSpot is especially good for "what was implementation actually like" intelligence.

### Step 10: Reddit/Community Sentiment

**Search:** `[company_name] reddit discussion`
**Extract:** Unfiltered community opinions, switching stories, specific use-case feedback.
**Quality:** 4 | **Consistency:** 3
**Notes:** DO NOT use `site:reddit.com` — it's broken. This surfaces Reddit-synthesis articles. Works best for dev tools with active Reddit communities. Weaker for consumer apps.

### Step 11: Head-to-Head Comparison Reviews (Tier 1-2)

**Search:** `[company_name] vs [top competitor] comparison review`
**Extract:** Side-by-side feature comparisons, pricing comparisons, reviewer recommendations.
**Quality:** 4 | **Consistency:** 3
**When:** Tier 1-2 and a clear top competitor has been identified.
**Notes:** Comparison reviews are more actionable than standalone reviews because they position strengths relative to alternatives.

### Step 12: Community Forum Sentiment (Tier 3 fallback)

**Search:** `[company_name] feedback OR testimonial`
**Extract:** Any customer feedback, testimonials, or user stories.
**Quality:** 3 | **Consistency:** 3
**When:** Tier 3 only. Primary review platforms returned no results.
**Notes:** For micro companies without G2/Trustpilot presence, this catches scattered feedback from blog comments, social media, and niche forums.

---

## Kill List

DO NOT use these patterns:

| Pattern                               | Why It Fails                                                    |
| ------------------------------------- | --------------------------------------------------------------- |
| `[name] review site:reddit.com`       | BROKEN. Zero results universally. Reddit blocks site: operator. |
| `[name] experience site:reddit.com`   | BROKEN. Same issue.                                             |
| `[name] NPS score`                    | Companies don't publish NPS externally.                         |
| `[name] site:saastr.com reviews`      | SaaStr is not a review platform. Returns conference content.    |
| `[name] reviews site:sourceforge.net` | Only covers open-source projects.                               |
| `[name] reviews site:getapp.com`      | Poor coverage for modern tools.                                 |

---

## Output Template

```
REVIEW SENTIMENT: [Positive/Mixed/Negative]

WHAT CUSTOMERS LOVE:
- [Theme 1] — [evidence and source]
- [Theme 2] — [evidence and source]
- [Theme 3] — [evidence and source]

WHAT CUSTOMERS COMPLAIN ABOUT:
- [Pain point 1] — [evidence and source]
- [Pain point 2] — [evidence and source]
- [Pain point 3] — [evidence and source]

EMPLOYEE SENTIMENT:
- Glassdoor: [X]/5 ([N] reviews)
- CEO approval: [X]%
- Top pro: [theme]
- Top con: [theme]

PLATFORM RATINGS:
- G2: [score]/5 ([N] reviews)
- Trustpilot: [score]/5 ([N] reviews)
- Product Hunt: [score] ([N] upvotes)
- Glassdoor: [score]/5 ([N] reviews)

CONFIDENCE: [High/Medium/Low] — [why]
```
