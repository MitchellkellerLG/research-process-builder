# find PR and releases

surface official company communications: press releases, blog announcements, wire service distributions.

## inputs

- `{{company_name}}` — the company to research
- `{{domain}}` — their website domain (required for site: searches)
- `{{category}}` — what they do in 2-3 words. required if name is ambiguous.

## steps

### step 1: general announcement search

search: `{{company_name}} {{category}} announces`

extract from results:

- every official announcement found
- for each: date, title, source (company blog / wire service / news outlet), and a three sentence summary of what was announced
- note the announcement cadence (how frequently do they announce things?)

**stop if:** you found 3+ official announcements with dates and summaries. skip to output.

### step 2: company blog

search: `site:{{domain}}/blog`

extract from results:

- blog URL
- recent post titles and dates
- posting frequency (weekly, monthly, quarterly, sporadic)
- three sentence summary of the most recent post

### step 3: company newsroom / press page

search: `site:{{domain}}/newsroom`

if no results, try in order: `site:{{domain}}/press`, then `site:{{domain}}/news`, then `site:{{domain}}/media`

extract from results:

- newsroom URL (or "not found")
- most recent press release title and date
- three sentence summary

**stop if:** you have blog content from step 2 AND press content from step 3. skip to output.

### step 4: wire service check (skip for small/bootstrapped companies)

search: `{{company_name}} site:businesswire.com`

extract from results:

- any formal press releases on businesswire
- three sentence summary per release

if no results, try: `{{company_name}} site:prnewswire.com`

### step 5: year-filtered press releases

search: `{{company_name}} press release 2026`

extract from results:

- any recent releases not found in previous steps
- three sentence summary per release

## do not search

- `{{company_name}} media release` — american tech companies don't use this phrase
- `{{company_name}} official announcement` — weaker duplicate of "announces"
- `{{company_name}} annual report` — private companies don't publish these
- `site:apollo.io {{company_name}}` — gated data, returns SEO blog posts

## output

```
## PR and releases for {{company_name}}

**communication style:** [active PR machine / regular blogger / occasional announcements / mostly dark]

**channels found:**
- blog: [url or "not found"]
- newsroom: [url or "not found"]
- wire services: [businesswire / prnewswire / none]

**recent releases:**

1. [date] — [source: blog/wire/newsroom] — [three sentence summary of what was announced, the key details, and why it matters]

2. [date] — [source] — [three sentence summary]

3. [date] — [source] — [three sentence summary]

(continue for all releases found)

**last known communication:** [date or "unknown"]
```
