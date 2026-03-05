# Find PR/Releases Process

**Goal:** Given a company name and domain, surface official company communications: press releases, blog announcements, wire service distributions.
**Accuracy:** 90% validated across 11 companies (SpaceX to micro startups)
**Built:** 2026-03-04
**Methodology:** research-process-builder skill, 15 patterns tested across 1 iteration

## What "Good" Looks Like

- Official first-party communications found (not third-party coverage)
- Company newsroom/press page located (if it exists)
- Blog content surfaced
- Communication cadence assessed (active PR machine vs silent)
- Wire service presence identified

## Preprocessing

### Step 0a: Name Disambiguation

Is the company name ambiguous? (6 chars or fewer, common word, famous namesake)

If YES: construct `disambiguated_name` = `[name] [category]` or use domain.
If NO: `disambiguated_name` = `company_name`.

### Step 0b: Company Size Detection

Search: `[company_name] company overview`

- 5+ third-party profiles → **Tier 1** → run all 10 steps
- 2-4 profiles → **Tier 2** → run Steps 1-8
- 0-1 profiles → **Tier 3** → run Steps 1-5 only. Tier 3 companies rarely use wire services.

---

## Steps

### Step 1: General Announcement Search

**Search:** `[disambiguated_name] announces`
**Extract:** All official announcements: product launches, partnerships, funding, hires, milestones. Note the source of each (company blog, wire service, news outlet covering the announcement).
**Quality:** 5 | **Consistency:** 4
**Notes:** Best general PR pattern. "Announces" is the verb companies use in official communications. Catches blog posts, wire distributions, and news coverage simultaneously. More reliable than "press release" which many modern companies don't use.

### Step 2: Company Newsroom

**Search:** `site:[domain]/newsroom`
**Extract:** Newsroom URL, list of recent releases, release cadence (monthly? quarterly?).
**Quality:** 5 | **Consistency:** 4

If no results, try these path variants in order:

1. `site:[domain]/press`
2. `site:[domain]/news`
3. `site:[domain]/media`
4. `site:[domain]/media-coverage`

**Notes:** Zero noise. Returns only official company press content. If none of these paths return results, the company doesn't maintain a formal press section.

### Step 3: Company Blog

**Search:** `site:[domain]/blog`
**Extract:** Blog URL, recent post titles, posting frequency, content themes (product updates vs thought leadership vs case studies).
**Quality:** 5 | **Consistency:** 5
**Notes:** Most companies communicate via blog, not press releases. This is often the richest source of first-party content. Even micro companies usually have a blog.

### Step 4: Year-Filtered Press Releases

**Search:** `[company_name] press release 2026`
**Extract:** Formal press releases from the current year. Note which wire service distributed them.
**Quality:** 4 | **Consistency:** 3
**Notes:** Works best for companies that actively use wire services. Falls flat for blog-only communicators.

### Step 5: Blog Announcements

**Search:** `[company_name] blog announcement`
**Extract:** Blog posts specifically tagged as announcements (product launches, company milestones, feature releases).
**Quality:** 4 | **Consistency:** 3
**Notes:** Targets the announcement category of company blogs specifically. Different from Step 3 which surfaces all blog content.

### Step 6: BusinessWire (Tier 1-2 only)

**Search:** `[company_name] site:businesswire.com`
**Extract:** Formal press releases distributed via BusinessWire. Often includes funding announcements, partnerships, executive hires.
**Quality:** 4 | **Consistency:** 3
**When:** Growth-stage funded companies that use wire services. Skip for Tier 3.
**Notes:** BusinessWire is the most common wire service for VC-backed startups.

### Step 7: PR Newswire (Tier 1-2 only)

**Search:** `[company_name] site:prnewswire.com`
**Extract:** Press releases distributed via PR Newswire. Good for partner-issued releases (where the partner, not the company, issued the release).
**Quality:** 4 | **Consistency:** 3
**When:** Supplement to Step 6. Especially useful for catching releases issued by partners about the company.

### Step 8: Globe Newswire (Tier 1-2 only)

**Search:** `[company_name] site:globenewswire.com`
**Extract:** Press releases focused on M&A, financial results, and regulatory announcements.
**Quality:** 3 | **Consistency:** 3
**When:** Supplement. Best for M&A announcements specifically.
**Notes:** Less common for pure software companies, more common for companies with financial reporting obligations.

### Step 9: Product Changelog (SaaS companies)

**Search:** `site:[domain]/changelog OR site:[domain]/updates OR site:[domain]/whats-new`
**Extract:** Product changelog entries, update cadence, feature shipping velocity.
**Quality:** 4 | **Consistency:** 2
**When:** SaaS companies with public changelogs. Skip for non-software.
**Notes:** Changelogs are the most honest communication channel. No marketing spin, just what shipped and when.

### Step 10: Investor Communications (Tier 1 only)

**Search:** `[company_name] investor update OR shareholder letter`
**Extract:** Investor letters, shareholder communications, annual reviews.
**Quality:** 3 | **Consistency:** 2
**When:** Tier 1 only. Public companies or late-stage private companies that publish investor communications.
**Notes:** Rare but extremely valuable when found. Investor letters contain strategic direction that press releases sanitize.

---

## Kill List

DO NOT use these patterns:

| Pattern                        | Why It Fails                                      |
| ------------------------------ | ------------------------------------------------- |
| `[name] media release`         | American tech companies don't use this phrase     |
| `[name] official announcement` | Weaker duplicate of "announces" — wastes a search |
| `[name] annual report`         | Private companies don't publish annual reports    |
| `site:apollo.io [name]`        | Data is gated, returns SEO blog posts instead     |

---

## Output Template

```
OFFICIAL CHANNELS:
- Newsroom: [URL or "not found"]
- Blog: [URL or "not found"]
- Changelog: [URL or "not found"]
- Wire services used: [BusinessWire / PRNewswire / GlobeNewswire / None]

RECENT RELEASES (most recent first):
1. [Date] — [Title] — [Source: blog/wire/newsroom] — [Summary]
2. [Date] — [Title] — [Source] — [Summary]
3. [Date] — [Title] — [Source] — [Summary]

COMMUNICATION CADENCE: [Active PR machine / Monthly blogger / Occasional announcements / Dark]
LAST COMMUNICATION: [date or "unknown"]
CONFIDENCE: [High/Medium/Low] — [why]
```
