# find growth signals

surface indicators of active investment and growth: content output, marketing infrastructure, social presence, event activity, and monetization maturity. this tells you whether a company is actively investing in growth or coasting.

## inputs

- `{{company_name}}` — the company to research
- `{{domain}}` — their website domain (required for site: searches)
- `{{category}}` — what they do in 2-3 words. required if the company name is a common word or 6 characters or fewer.

## steps

### step 1: blog activity check

search: `site:{{domain}}/blog`

if no results, try: `{{company_name}} {{category}} blog 2026`

extract from results:

- blog URL (or "not found")
- most recent post title and approximate date
- posting frequency signal (multiple recent posts = active, nothing recent = dormant)
- blog categories or topics covered
- three sentence summary of content focus and recency

a company that blogs weekly is investing in content marketing. one that hasn't posted in 6+ months is either resource-constrained or has deprioritized content.

**stop if:** you already have a clear picture of their content investment level and want to check other signal types. continue to step 2.

### step 2: lead magnets and conversion infrastructure

search: `site:{{domain}} ebook OR whitepaper OR guide OR webinar OR demo OR "free trial" OR "book a call" OR newsletter`

extract from results:

- every lead capture mechanism found (gated content, demos, free trials, webinars, newsletter signups)
- pricing page existence and structure (freemium, free trial, enterprise-only, custom pricing)
- three sentence summary of their conversion funnel maturity

companies with multiple lead magnets, a clear pricing page, and demo booking = mature growth engine. companies with just a contact form = early or services-oriented.

### step 3: social media presence

search: `{{company_name}} {{category}} site:twitter.com OR site:x.com OR site:instagram.com OR site:linkedin.com`

do NOT search `{{company_name}} social media twitter youtube` — this returns results about the company's product features, not their actual social accounts. tested Q1/C0.

extract from results:

- every social account found (handle and platform)
- follower count if visible in search snippet
- most recent post topic if visible
- three sentence summary of social presence

**stop if:** combined with steps 1-2, you have a clear picture of their marketing investment. skip to output if you only need a high-level growth signal.

### step 4: newsletter and community

search: `{{company_name}} {{category}} newsletter`

extract from results:

- newsletter name and platform (substack, beehiiv, mailchimp, custom)
- subscriber count if visible
- posting frequency if visible
- any community platforms (discord, slack, forum, etc.)
- three sentence summary

companies that run newsletters are investing in owned audience. this is a stronger growth signal than social media because it requires consistent effort.

### step 5: podcast, webinar, and event activity

search: `{{company_name}} podcast OR webinar OR event OR conference 2026`

extract from results:

- any podcast appearances by founders/execs (name of podcast, topic)
- any webinars hosted or co-hosted
- any conference appearances or sponsorships
- three sentence summary of event-based growth activity

companies appearing on podcasts and hosting webinars = active demand gen. this is especially strong signal for B2B companies.

**stop if:** you have enough data across content, social, newsletter, and events to assess their growth investment level. skip to output.

### step 6: pricing and monetization signals

search: `site:{{domain}} pricing`

if no results, try: `{{company_name}} pricing`

extract from results:

- pricing model (freemium, free trial, paid only, enterprise/custom, contact sales)
- price points if visible
- plan tiers (how many, what's included)
- three sentence summary of monetization maturity

### step 7: year-filtered content recency (only if steps 1-2 were inconclusive)

search: `{{company_name}} {{category}} 2026`

extract from results:

- any content, press, or activity from the current year
- this is a blunt instrument — if a company has ZERO mentions in the current year, that's a significant signal of inactivity
- three sentence summary

## what search CANNOT detect

be honest about these limitations in your output:

- **google ads / paid search presence** — standard search APIs return organic results only. you cannot determine if a company is running google ads, facebook ads, or other paid campaigns through web search alone. facebook ad library is not indexed by search engines, and tools like semrush/similarweb require authenticated access.
- **exact follower counts** — search snippets sometimes show these but not reliably.
- **posting frequency on social media** — you can find accounts but not measure activity cadence without visiting each platform.
- **website traffic volume** — requires tools like similarweb or semrush.

## do not search

- `{{company_name}} social media twitter youtube instagram` — returns product feature content, not the company's own accounts. tested Q1/C0 across all tiers.
- `{{company_name}} youtube channel` — returns unrelated channels for ambiguous names (clay art channels, scam warnings, etc.)
- `site:facebook.com/ads/library {{company_name}}` — facebook ad library is not indexed by search engines
- `"{{domain}}" google ads paid search` — returns the company's ad-related product features, not whether they run ads
- `{{company_name}} marketing strategy` — returns generic marketing advice articles, not company-specific data

## output

```
## growth signals for {{company_name}}

**overall growth investment:** [heavy / moderate / light / minimal]

**content signals:**
- blog: [active (X posts/month) / sporadic / dormant / not found] — [url]
- newsletter: [name, platform, frequency] or "not found"
- podcast/events: [appearances or hosted events] or "none found"

**marketing infrastructure:**
- lead magnets: [list what was found: ebooks, webinars, guides, etc.] or "none found"
- conversion flow: [free trial / freemium / demo booking / contact form only / unclear]
- pricing page: [public pricing / enterprise-only / custom / not found]

**social presence:**
- [platform]: [handle] — [follower count if visible]
- [platform]: [handle]
(list all found)

**what this tells us:**
[three sentences. what growth stage are they in based on these signals? are they actively investing in demand gen, or is growth happening through other channels (product-led, partnerships, word of mouth)? what's the gap between their product maturity and their marketing maturity?]

**not detectable via search:** [note any signals the user asked about that couldn't be verified — e.g. "google ads presence cannot be determined through web search"]
```
