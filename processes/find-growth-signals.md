# find growth signals

surface indicators of active investment and growth: content output, marketing infrastructure, social presence, event activity, and monetization maturity. this tells you whether a company is actively investing in growth or coasting.

## inputs

- `{{company_name}}` — the company to research
- `{{domain}}` — their website domain (required for site: searches)
- `{{category}}` — what they do in 2-3 words. required if the company name is a common word or 6 characters or fewer.
- `{{current_year}}` — the current year (e.g. 2026). in Clay, use a formula column: `YEAR({Created At})`.

## steps

### step 1: website infrastructure sweep

search: `site:{{domain}} blog OR pricing OR newsletter OR demo OR "free trial" OR "book a call"`

this single query detects multiple growth signals at once: do they have a blog, a pricing page, a newsletter, a demo flow? tested Q5/C4 for T2+ companies. thinner for T3 but still finds something if it exists.

extract from results:

- blog URL and most recent post title (if visible)
- pricing page URL and model (freemium, free trial, enterprise-only, custom)
- any lead capture mechanisms (newsletter signup, demo booking, free trial, gated content)
- any webinar or event pages
- three sentence summary of their marketing infrastructure maturity

companies with blog + pricing + demo booking + newsletter = mature growth engine. companies with just a homepage and contact form = early stage or services-oriented.

**stop if:** you found a blog, pricing page, and at least one lead capture mechanism. you have a clear picture of their infrastructure. continue to step 2 for content depth.

### step 2: blog and content activity

search: `{{company_name}} {{category}} blog {{current_year}}`

this catches both the company's own blog posts AND third-party coverage about them. the year filter ensures recency.

extract from results:

- recent blog posts from the company itself (titles, dates, topics)
- posting frequency signal (multiple posts in recent months = active, nothing = dormant)
- third-party blog coverage (reviews, mentions, comparisons)
- three sentence summary of content output and recency

a company actively publishing blog content is investing in organic growth. a company only appearing in third-party blogs is getting attention but may not be investing in owned content.

### step 3: social media presence

search: `{{company_name}} {{category}} site:twitter.com OR site:x.com OR site:instagram.com OR site:linkedin.com`

extract from results:

- every social account found (handle and platform)
- follower count if visible in search snippet
- most recent post topic if visible
- three sentence summary of social presence and activity level

**stop if:** combined with steps 1-2, you have a clear picture of their marketing investment across content, infrastructure, and social. skip to output if you only need a high-level growth signal.

### step 4: newsletter and community

search: `{{company_name}} {{category}} newsletter`

extract from results:

- newsletter name and platform (substack, beehiiv, mailchimp, custom)
- subscriber count if visible
- posting frequency if visible
- any community platforms (discord, slack, forum, etc.)
- three sentence summary

companies that run newsletters are investing in owned audience. this is a stronger growth signal than social media because it requires consistent effort and indicates long-term thinking.

### step 5: podcast, webinar, and event activity

search: `{{company_name}} podcast OR webinar OR event OR conference {{current_year}}`

extract from results:

- any podcast appearances by founders/execs (name of podcast, topic)
- any webinars hosted or co-hosted
- any conference appearances or sponsorships
- three sentence summary of event-based growth activity

companies appearing on podcasts and hosting webinars = active demand gen. this is especially strong signal for B2B companies.

**stop if:** you have enough data across content, social, newsletter, and events to assess their overall growth investment. skip to output.

### step 6: year-filtered activity fallback (only if steps 1-2 were thin)

search: `{{company_name}} {{category}} {{current_year}}`

extract from results:

- any content, press, or activity from the current year
- this is a blunt instrument — if a company has ZERO mentions in the current year, that's a significant signal of inactivity
- three sentence summary

## do not search

- `{{company_name}} social media twitter youtube instagram` — returns product feature content, not the company's own accounts. tested Q1/C0 across all tiers.
- `{{company_name}} youtube channel` — returns unrelated channels for ambiguous names (clay art channels, scam warnings, etc.)
- `{{company_name}} marketing strategy` — returns generic marketing advice articles, not company-specific data
- `{{company_name}} google ads` — returns the company's ad-related product features, not whether they run ads
- `site:facebook.com/ads/library {{company_name}}` — facebook ad library is not indexed by search engines

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
```
