# serper search patterns — validated reference

**validated:** 2026-03-06 (round 2)
**total queries tested:** 1,604 (944 round 1 + 175 do-not-search + 485 combo optimization)
**total cost:** ~$0.16
**cost per search:** $0.0001 via Serper vs ~$0.50 native Clay enrichment = **5000x savings**

---

## how to use in Clay

each pattern below is a Clay HTTP API column:

1. add column > HTTP API
2. method: `POST`
3. URL: `https://google.serper.dev/search`
4. headers: `X-API-KEY: {{SERPER_API_KEY}}` and `Content-Type: application/json`
5. body: see each pattern below
6. map response: `{{http_response.organic[0].title}}` or `{{http_response.organic[0].link}}`

---

## Company Profile

**best:** `site:rocketreach.co {{company_name}}`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** company overview, employee count, revenue estimate, industry classification
**Clay body:** `{"q": "site:rocketreach.co /Company Name/", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} company overview` (Q3.8)
**replaces:** Company Overview enrichment — saves $0.4999/search

---

## Funding / Financial

**best:** `{{company_name}} funding`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** funding rounds, amounts raised, investors, valuation, Crunchbase profiles
**Clay body:** `{"q": "/Company Name/ funding", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} {{category}} funding` (Q4.0)
**replaces:** Funding Finder — saves $0.4999/search

---

## Hiring Signals

**best:** `{{company_name}} careers`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** careers pages, open roles count, ATS platform (greenhouse/lever/ashby), hiring departments
**Clay body:** `{"q": "/Company Name/ careers", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} {{category}} careers` (Q4.0)
**replaces:** Hiring Activity — saves $0.4999/search

---

## Competitor Identification

**best:** `{{company_name}} {{category}} alternatives OR competitors OR "vs" OR "compared to"`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** competitor lists, comparison articles, G2/Capterra alternatives pages
**Clay body:** `{"q": "/Company Name/ /Category/ alternatives OR competitors OR \"vs\" OR \"compared to\"", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} competitors` (Q4.0)
**replaces:** Competitor Finder — saves $0.4999/search

---

## Reviews / Sentiment

**best:** `{{company_name}} review`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** G2 reviews, Trustpilot, editorial reviews, ProductHunt, honest assessments
**Clay body:** `{"q": "/Company Name/ review", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} glassdoor reviews` (Q4.0)
**replaces:** Review Finder — saves $0.4999/search

---

## News / Press Coverage

**best:** `{{domain}} news`
**avg Q:** 3.6 | **min Q:** 3 | tested across 5 companies
**what it surfaces:** company news, press coverage, TechCrunch/Forbes mentions. weakest category — inconsistent for startups.
**Clay body:** `{"q": "/domain/ news", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} news announcement -jobs -careers -glassdoor -salary` (Q3.4)
**note:** news is inherently noisy. for better results, use the Serper news endpoint: `POST https://google.serper.dev/news`

---

## Press Releases

**best:** `{{company_name}} "press release" OR "announces" OR "newsroom"`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** official announcements, partnerships, product launches, newsroom pages
**Clay body:** `{"q": "/Company Name/ \"press release\" OR \"announces\" OR \"newsroom\"", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `site:{{domain}} news OR press OR announcements` (Q3.6)
**replaces:** PR Finder — saves $0.4999/search

---

## Social Media Presence

**best:** `site:linkedin.com/company/{{company_name}}`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** LinkedIn company page with employee count, follower count, industry, headquarters
**Clay body:** `{"q": "site:linkedin.com/company//Company Name/", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} social media accounts` (Q3.8)
**note:** round 1 social_media scored Q2.8 avg. `site:linkedin.com/company/` combo pattern fixed this completely.

---

## Community Platforms

**best:** `{{company_name}} {{category}} discord OR slack OR community`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Discord servers, Slack communities, forum links, member counts
**Clay body:** `{"q": "/Company Name/ /Category/ discord OR slack OR community", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} discord` (Q4.0)

---

## Growth / Marketing Infrastructure

**best:** `site:{{domain}} blog OR pricing OR demo` + `tbs: qdr:y`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** blog activity, pricing pages, demo pages, newsletter signups — all from company's own site, filtered to past year
**Clay body:** `{"q": "site:/domain/ blog OR pricing OR demo", "gl": "us", "hl": "en", "num": 10, "tbs": "qdr:y"}`
**runner-up:** `site:{{domain}} "subscribe" OR "newsletter" OR "sign up" OR "book a demo"` (Q3.8)
**note:** round 1 growth_marketing scored Q2.5 avg. the `tbs: qdr:y` time filter fixed the multi-keyword site: pattern that was returning zero results.

---

## Tech Stack

**best:** `{{company_name}} tech stack`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** technology discussions, StackShare profiles, job descriptions inferring stack, API docs
**Clay body:** `{"q": "/Company Name/ tech stack", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} {{category}} tech stack OR technology` (Q4.0)
**replaces:** BuiltWith / StackShare lookups — saves $0.4999/search

---

## Leadership / People

**best:** `{{company_name}} CEO OR founder`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** founder names, CEO interviews, LinkedIn profiles, podcast appearances
**Clay body:** `{"q": "/Company Name/ CEO OR founder", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} leadership team` (Q4.0)
**replaces:** People Finder — saves $0.4999/search

---

## Customer Case Studies

**best:** `{{company_name}} {{category}} case study OR customer story`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** case study pages, customer success stories, logos/testimonials
**Clay body:** `{"q": "/Company Name/ /Category/ case study OR customer story", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `site:{{domain}} customers` (Q4.0)

---

## Pricing Intelligence

**best:** `{{company_name}} pricing`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** pricing pages, plan comparison articles, cost breakdowns
**Clay body:** `{"q": "/Company Name/ pricing", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} {{category}} pricing plans` (Q4.0)

---

## Partnerships / Integrations

**best:** `{{company_name}} partnerships OR integrations`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** integration pages, partner programs, Zapier/Make connections, API marketplaces
**Clay body:** `{"q": "/Company Name/ partnerships OR integrations", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} {{category}} integrations` (Q4.0)

---

## Content / Blog Activity

**best:** `site:{{domain}} resources OR guides OR whitepapers`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** resource centers, blog posts, guides, whitepapers — all owned content
**Clay body:** `{"q": "site:/domain/ resources OR guides OR whitepapers", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "how to" guide OR tutorial` (Q3.8)

---

## Newsletter / Email Marketing

**best:** `site:{{domain}} "subscribe" OR "newsletter" OR "sign up"`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** newsletter signup pages, email capture forms, subscription CTAs
**Clay body:** `{"q": "site:/domain/ \"subscribe\" OR \"newsletter\" OR \"sign up\"", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "subscribe" OR "weekly update" OR "monthly digest" OR newsletter -product` (Q4.0)

---

## Events / Conferences

**best:** `{{company_name}} meetup OR community event`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** community events, meetups, hackathons, conference appearances
**Clay body:** `{"q": "/Company Name/ meetup OR community event", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} conference OR event 2026` (Q3.8)

---

## Customer Complaints / Negativity

**best:** `{{company_name}} problems OR issues OR complaints -careers -jobs -site:{{domain}}`
**avg Q:** 3.8 | **min Q:** 3 | tested across 5 companies
**what it surfaces:** complaint threads, negative reviews, problem reports — excludes company's own site and job noise
**Clay body:** `{"q": "/Company Name/ problems OR issues OR complaints -careers -jobs -site:/domain/", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} intitle:honest OR intitle:cons OR intitle:problems OR intitle:issues` (Q3.2)
**note:** round 1 customer_complaints scored Q2.1. the exclusion-based combo pattern raised it to Q3.8 — biggest improvement of any category.

---

## Awards / Recognition

**best:** `{{company_name}} top OR best {{category}} company`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** "best of" lists, industry rankings, G2 awards, Forbes/Inc lists
**Clay body:** `{"q": "/Company Name/ top OR best /Category/ company", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} named OR ranked OR recognized` (Q4.0)

---

## key findings from round 2

**operators that work:**
- `-` exclusion: biggest accuracy gains. removing job/career/salary noise from results raised Q scores by 1-2 points
- `site:` multi-domain OR: `site:linkedin.com/company/` fixed social media from Q2.8 to Q4.0
- `tbs: qdr:y`: time-based filtering fixed growth_marketing from Q2.5 to Q4.0
- simple OR combos: `alternatives OR competitors OR "vs"` consistently Q4+

**operators that KILL results:**
- `intitle:` — too aggressive, returns Q1 in 60%+ of tests. Google strips too many results.
- `after:YYYY-MM-DD` — universally Q1. Serper may not support this Google operator.
- `AROUND(n)` — not tested, but `after:` failure suggests advanced operators are unreliable via API
- `inurl:` — inconsistent, Q1-Q4 wildly. works for `inurl:blog` on some domains, zero results on others.

**do-not-search validation:**
- 37 patterns tested across 5 companies (175 searches)
- 37/37 scored Q1-Q2 — every single "do not search" pattern is correctly killed
- most common failure: returns irrelevant content (marketing content, SEO articles, wrong entity)

**round 2 improvements vs round 1:**
| category | round 1 avg Q | round 2 best Q | delta |
|---|---|---|---|
| customer_complaints | 2.1 | 3.8 | **+1.7** |
| growth_marketing | 2.5 | 4.0 | **+1.5** |
| social_media | 2.8 | 4.0 | **+1.2** |
| news_press | 2.6 | 3.6 | +1.0 |
| content_blog | 3.2 | 4.0 | +0.8 |
| newsletter_email | 3.0 | 4.0 | +1.0 |
| events_conferences | 3.2 | 4.0 | +0.8 |
