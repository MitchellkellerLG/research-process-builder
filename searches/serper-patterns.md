# serper search pattern reference

**validated:** 2026-03-06
**queries tested:** 944
**cost of validation:** ~$0.09
**cost per search:** $0.0001 via Serper vs ~$0.50 native Clay enrichment = **5000x savings**

---

## how to use this in Clay

each pattern below can be used as a Clay HTTP API column:

1. add column > HTTP API
2. method: `POST`
3. URL: `https://google.serper.dev/search`
4. headers: `X-API-KEY: {{SERPER_API_KEY}}` and `Content-Type: application/json`
5. body: `{"q": "[pattern with your variables]", "gl": "us", "hl": "en", "num": 10}`
6. map response: `{{http_response.organic[0].title}}` or `{{http_response.organic[0].link}}`

---

## Company Profile / Overview
**replaces:** Company Overview (Claygent)

### PRIMARY (Q4+ / C4+)

**`site:rocketreach.co {{company_name}}`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Information - RocketReach

### FALLBACK (Q3+)

`{{company_name}} company overview` — avg Q3.8
`site:crunchbase.com {{company_name}}` — avg Q3.8
`site:zoominfo.com {{company_name}}` — avg Q3.8
`{{domain}} about company` — avg Q3.8
`site:pitchbook.com {{company_name}}` — avg Q3.8
`site:zoominfo.com OR site:rocketreach.co OR site:crunchbase.com {{company_name}}` — avg Q3.6
`{{company_name}} {{category}} company overview` — avg Q3.0

### KILL

~~`site:linkedin.com/company {{company_name}}`~~ — avg Q2.6
~~`what does {{company_name}} do {{category}}`~~ — avg Q2.4

---

## Funding / Financial Signals
**replaces:** Funding Finder

### PRIMARY (Q4+ / C4+)

**`{{company_name}} funding`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Vibe-coding startup Lovable raises $330M at a $6.6B valuation

**`{{company_name}} {{category}} funding`**
- scores: ClickUp Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: SpaceX Funding Rounds: Key Investors by Stage

**`site:crunchbase.com {{company_name}} funding`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable - Crunchbase Company Profile & Funding

**`{{company_name}} funding OR raised OR series OR valuation`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Vibe-coding startup Lovable raises $330M at a $6.6B valuation

**`{{company_name}} funding 2026`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable raises $330M to power the age of the builder

**`{{domain}} funding`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable raises $330M to power the age of the builder

**`how much has {{company_name}} raised`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable raises $330M to power the age of the builder

**`{{company_name}} "series A" OR "series B" OR "series C"`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable raises $330M to power the age of the builder

**`{{company_name}} revenue OR ARR OR valuation`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable raises $330M to power the age of the builder

### FALLBACK (Q3+)

`"{{company_name}}" raised` — avg Q3.8

---

## Hiring Signals
**replaces:** Hiring Activity

### PRIMARY (Q4+ / C4+)

**`{{company_name}} careers`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Careers at Lovable - The last piece of software

**`{{company_name}} {{category}} careers`**
- scores: ClickUp Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Careers - SpaceX

**`{{company_name}} site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Engineer - Agents & Evals @ Lovable - Jobs

**`{{company_name}} hiring engineering OR sales OR marketing`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Careers at Lovable - The last piece of software

### FALLBACK (Q3+)

`{{company_name}} hiring 2026` — avg Q3.8
`{{company_name}} "we're hiring" OR "join our team"` — avg Q3.8
`site:wellfound.com {{company_name}}` — avg Q3.6
`site:{{domain}}/careers` — avg Q3.2
`site:{{domain}} careers OR jobs OR "open positions"` — avg Q3.0

### KILL

~~`{{company_name}} hiring OR "open roles" OR careers`~~ — avg Q1.4

---

## Competitor Identification
**replaces:** Competitor Finder

### PRIMARY (Q4+ / C4+)

**`{{company_name}} {{category}} alternatives OR competitors OR "vs" OR "compared to"`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Found some Lovable alternatives that are actually new (and worth a ...

**`{{company_name}} competitors`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Alternatives for 2026 - Builder.io

**`{{company_name}} {{category}} competitors`**
- scores: ClickUp Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: The New Space Race: 7 Companies Battling Musk - Yahoo Finance

**`{{company_name}} vs`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: I Ranked Every AI App Builder for 2026: Lovable vs. Bolt ...

**`who competes with {{company_name}} {{category}}`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Found some Lovable alternatives that are actually new (and worth a ...

**`{{domain}} competitors`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: 10 Best Lovable AI Alternatives for Different Use-Cases - Banani

**`alternatives to {{company_name}}`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Found some Lovable alternatives that are actually new (and worth a ...

### FALLBACK (Q3+)

`site:g2.com {{company_name}} alternatives` — avg Q3.6

### KILL

~~`best {{category}} tools`~~ — avg Q1.6
~~`{{category}} market landscape comparison`~~ — avg Q1.0

---

## Reviews / Sentiment
**replaces:** Review Finder

### PRIMARY (Q4+ / C4+)

**`{{company_name}} review`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Review 2026: Best AI App Builder? (Tested & Rated)

**`{{company_name}} glassdoor reviews`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Reviews (11): Pros & Cons of Working At Lovable | Glassdoor

**`{{company_name}} honest review`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: An honest lovable review (2025): Pros, Cons & Pricing

**`{{company_name}} complaints`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: The Problem with Lovable - Reddit

### FALLBACK (Q3+)

`{{company_name}} {{category}} review 2026` — avg Q3.6
`{{company_name}} reviews site:g2.com` — avg Q3.6
`{{company_name}} reviews site:trustpilot.com` — avg Q3.4
`{{company_name}} reviews site:producthunt.com` — avg Q3.2
`{{company_name}} {{category}} reddit discussion` — avg Q3.0

### KILL

~~`{{company_name}} reviews site:capterra.com`~~ — avg Q2.4

---

## News / Press Coverage
**replaces:** News Finder

### FALLBACK (Q3+)

`{{domain}} news` — avg Q3.6
`{{company_name}} {{category}} recent news` — avg Q3.2
`{{company_name}} site:techcrunch.com` — avg Q3.0
`{{company_name}} news OR announcement OR press release 2026` — avg Q3.0

### KILL

~~`{{company_name}} acquisition OR funding 2026`~~ — avg Q2.8
~~`{{company_name}} partnership OR integration`~~ — avg Q2.8
~~`{{company_name}} news 2026`~~ — avg Q2.8
~~`{{company_name}} launches OR "new feature" OR expansion 2026`~~ — avg Q2.2
~~`{{company_name}} site:bloomberg.com`~~ — avg Q2.2
~~`{{company_name}} CEO interview OR "new hire" OR leadership`~~ — avg Q1.6
~~`{{company_name}} {{category}}`~~ — avg Q1.0

---

## Press Releases / Official Announcements
**replaces:** PR Finder

### PRIMARY (Q4+ / C4+)

**`{{company_name}} "press release" OR "announces" OR "newsroom"`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Kira and Lovable Launch Vibe Coding Course, Bringing AI-Powered ...

### FALLBACK (Q3+)

`site:{{domain}} news OR press OR announcements` — avg Q3.6
`{{company_name}} {{category}} announces` — avg Q3.4

### KILL

~~`site:{{domain}}/blog`~~ — avg Q2.6
~~`{{company_name}} press release 2026`~~ — avg Q2.6
~~`{{company_name}} site:businesswire.com`~~ — avg Q2.2
~~`{{company_name}} site:prnewswire.com`~~ — avg Q2.2
~~`site:{{domain}}/press`~~ — avg Q1.8
~~`site:{{domain}}/newsroom`~~ — avg Q1.0
~~`{{company_name}} announces`~~ — avg Q1.0

---

## Social Media Presence
**replaces:** Social Profile Finder

### FALLBACK (Q3+)

`{{company_name}} social media accounts` — avg Q3.8
`{{company_name}} site:linkedin.com` — avg Q3.6
`{{company_name}} site:instagram.com` — avg Q3.4
`{{company_name}} site:twitter.com OR site:x.com` — avg Q3.0
`{{company_name}} site:facebook.com` — avg Q3.0

### KILL

~~`{{company_name}} {{category}} site:twitter.com OR site:x.com OR site:instagram.com OR site:linkedin.com`~~ — avg Q2.8
~~`{{company_name}} site:tiktok.com`~~ — avg Q2.4
~~`{{company_name}} site:youtube.com`~~ — avg Q2.0
~~`{{company_name}} youtube channel`~~ — avg Q2.0
~~`{{company_name}} site:youtube.com OR site:tiktok.com`~~ — avg Q2.0

---

## Community Platforms

### PRIMARY (Q4+ / C4+)

**`{{company_name}} {{category}} discord OR slack OR community`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Join the Lovable Community | Lovable Discord or Browse Events

**`{{company_name}} discord`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Join the Lovable Community | Lovable Discord or Browse Events

**`{{company_name}} forum OR community forum`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Stop Using Lovable for Everything, Here's a Smarter Way to Build ...

**`{{company_name}} "join our community" OR "join our slack" OR "join our discord"`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Join the Lovable Community | Lovable Discord or Browse Events

### FALLBACK (Q3+)

`{{company_name}} slack community` — avg Q3.8
`{{company_name}} community members` — avg Q3.8
`site:{{domain}} community OR forum` — avg Q3.6
`site:discord.com {{company_name}}` — avg Q3.2
`{{company_name}} site:github.com discussions` — avg Q3.0

### KILL

~~`{{company_name}} reddit discussion`~~ — avg Q2.5

---

## Growth / Marketing Infrastructure
**replaces:** Growth Signal

### FALLBACK (Q3+)

`site:{{domain}} "subscribe" OR "newsletter" OR "sign up" OR "book a demo"` — avg Q3.8
`{{company_name}} content marketing OR blog strategy` — avg Q3.6

### KILL

~~`{{company_name}} {{category}} blog`~~ — avg Q2.8
~~`site:{{domain}} case study OR customer story OR testimonial`~~ — avg Q2.6
~~`{{company_name}} {{category}} SEO OR organic traffic`~~ — avg Q2.4
~~`{{company_name}} podcast OR webinar OR event OR conference`~~ — avg Q2.2
~~`{{company_name}} {{category}} site:producthunt.com OR site:wellfound.com`~~ — avg Q2.0
~~`site:{{domain}} blog OR pricing OR newsletter OR demo OR "free trial" OR "book a call"`~~ — avg Q1.6
~~`{{company_name}} advertising OR sponsored OR "paid media"`~~ — avg Q1.6

---

## Tech Stack Detection
**replaces:** BuiltWith / StackShare

### PRIMARY (Q4+ / C4+)

**`{{company_name}} tech stack`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Tech Stack & Dev Workflows - Reddit

**`{{company_name}} {{category}} tech stack OR technology`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: AI Solutions for Websites, Apps, and Businesses - Lovable

**`{{company_name}} "built with" OR "powered by"`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Cloud & AI | Build Apps Faster

**`{{company_name}} API documentation OR developer docs`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable API

### FALLBACK (Q3+)

`{{company_name}} technology OR infrastructure OR "tech stack"` — avg Q3.8
`site:stackshare.io {{company_name}}` — avg Q3.6
`{{company_name}} engineer job description python OR react OR node OR java` — avg Q3.0

### KILL

~~`{{company_name}} engineering blog OR technical blog`~~ — avg Q2.8
~~`site:github.com {{company_name}}`~~ — avg Q2.8
~~`site:builtwith.com {{domain}}`~~ — avg Q1.6

---

## Leadership / People Intelligence
**replaces:** People Finder

### PRIMARY (Q4+ / C4+)

**`{{company_name}} CEO OR founder`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable CEO, Anton Osika: The State of Foundation Models, Grok vs ...

**`{{company_name}} leadership team`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Building Lovable: $10M ARR in 60 days with 15 people - YouTube

**`{{company_name}} {{category}} founder CEO`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Building Lovable: $10M ARR in 60 days with 15 people - YouTube

### FALLBACK (Q3+)

`{{company_name}} board of directors OR investors OR advisors` — avg Q3.8
`site:{{domain}} team OR about OR leadership` — avg Q3.6
`"{{company_name}}" founder interview OR podcast` — avg Q3.6
`{{company_name}} "VP Sales" OR "Head of Sales" OR "CRO"` — avg Q3.4
`{{company_name}} {{category}} site:linkedin.com/in` — avg Q3.0

### KILL

~~`{{company_name}} CTO OR "VP Engineering" OR "Head of Engineering"`~~ — avg Q2.2

---

## Customer Case Studies / Logos

### PRIMARY (Q4+ / C4+)

**`{{company_name}} {{category}} case study OR customer story`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable.dev's Rapid Success Story - by Design Monks

**`site:{{domain}} customers`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Revenue & Customers - Lovable

**`{{company_name}} customers OR "trusted by" OR "used by"`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable.dev's Rapid Success Story - by Design Monks

### FALLBACK (Q3+)

`{{company_name}} case study` — avg Q3.8
`{{company_name}} {{category}} enterprise customer OR client` — avg Q3.4
`{{company_name}} success story OR results` — avg Q3.0

### KILL

~~`"{{company_name}}" customer review OR testimonial`~~ — avg Q2.6
~~`who uses {{company_name}}`~~ — avg Q2.4
~~`{{company_name}} ROI OR results OR impact`~~ — avg Q2.2

---

## Pricing Intelligence

### PRIMARY (Q4+ / C4+)

**`{{company_name}} pricing`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

**`{{company_name}} {{category}} pricing plans`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

**`{{company_name}} pricing vs cost OR comparison`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

**`{{company_name}} free plan OR free tier OR freemium`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

**`{{company_name}} enterprise pricing OR custom pricing`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

**`{{company_name}} pricing 2026`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

**`{{company_name}} "per seat" OR "per user" OR "per month" pricing`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

**`{{company_name}} pricing page breakdown`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

**`{{company_name}} discount OR coupon OR annual pricing`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable Pricing

### FALLBACK (Q3+)

`site:{{domain}} pricing` — avg Q3.8

---

## Partnerships / Integrations

### PRIMARY (Q4+ / C4+)

**`{{company_name}} partnerships OR integrations`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Partner with Lovable | Build Apps Faster

**`{{company_name}} {{category}} integrations`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable integrations: Connect tools, MCP servers, and APIs

**`site:{{domain}} integrations`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Lovable integrations: Connect tools, MCP servers, and APIs

**`{{company_name}} partner program`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Partner with Lovable | Build Apps Faster

**`{{company_name}} integration OR partnership OR plugin OR marketplace`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Partner with Lovable | Build Apps Faster

### FALLBACK (Q3+)

`{{company_name}} API OR developer platform` — avg Q3.8
`{{company_name}} ecosystem OR technology partners` — avg Q3.8
`{{company_name}} integrates with OR "connects with"` — avg Q3.4
`{{company_name}} site:zapier.com` — avg Q3.4
`{{company_name}} marketplace OR app store OR plugins` — avg Q3.2

---

## Content / Blog Activity

### PRIMARY (Q4+ / C4+)

**`site:{{domain}} resources OR guides OR whitepapers`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Guides for Building Apps and Websites with AI | Lovable

### FALLBACK (Q3+)

`{{company_name}} "how to" guide OR tutorial` — avg Q3.8
`{{company_name}} content hub OR resource center OR learning` — avg Q3.4
`site:{{domain}} blog OR news OR updates` — avg Q3.2
`{{company_name}} guest post OR contributed article` — avg Q3.2

### KILL

~~`{{company_name}} {{category}} blog 2026`~~ — avg Q2.8
~~`{{company_name}} founder blog OR CEO blog OR thought leadership`~~ — avg Q2.8
~~`{{company_name}} vs OR comparison OR alternative blog`~~ — avg Q2.2

---

## Newsletter / Email Marketing

### PRIMARY (Q4+ / C4+)

**`site:{{domain}} "subscribe" OR "newsletter" OR "sign up"`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Build Newsletter Platforms with AI - Lovable

### FALLBACK (Q3+)

`{{company_name}} "subscribe" OR "get updates" OR "join" newsletter` — avg Q3.8
`{{company_name}} {{category}} newsletter` — avg Q3.5
`{{company_name}} newsletter` — avg Q3.2
`{{company_name}} substack OR beehiiv OR newsletter` — avg Q3.2
`{{company_name}} linkedin newsletter` — avg Q3.2
`{{company_name}} weekly digest OR monthly digest OR roundup` — avg Q3.2
`site:beehiiv.com {{company_name}}` — avg Q3.0

### KILL

~~`site:substack.com {{company_name}}`~~ — avg Q2.2
~~`{{company_name}} email list OR "sign up for updates"`~~ — avg Q1.0

---

## Events / Conferences

### PRIMARY (Q4+ / C4+)

**`{{company_name}} meetup OR community event`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Join the Lovable Community | Lovable Discord or Browse Events

### FALLBACK (Q3+)

`{{company_name}} conference OR event 2026` — avg Q3.8
`{{company_name}} hackathon OR developer event` — avg Q3.8
`{{company_name}} sponsors OR sponsorship conference` — avg Q3.8
`{{company_name}} founder OR CEO podcast` — avg Q3.2
`{{company_name}} site:lu.ma OR site:luma.com` — avg Q3.2
`{{company_name}} site:eventbrite.com` — avg Q3.0

### KILL

~~`{{company_name}} speaking OR keynote OR panel`~~ — avg Q2.2
~~`{{company_name}} webinar OR "live demo" OR workshop`~~ — avg Q1.6

---

## Customer Complaints / Negativity
**replaces:** Sentiment Analysis

### KILL

~~`{{company_name}} {{category}} downsides OR limitations OR drawbacks`~~ — avg Q2.6
~~`{{company_name}} controversy OR scandal OR backlash`~~ — avg Q2.6
~~`{{company_name}} {{category}} problems reddit discussion`~~ — avg Q2.4
~~`{{company_name}} {{domain}} honest review`~~ — avg Q2.2
~~`{{company_name}} {{category}} complaints OR "negative reviews" OR problems OR issues`~~ — avg Q2.0
~~`{{company_name}} site:bbb.org OR site:complaintsboard.com`~~ — avg Q2.0
~~`{{company_name}} "do not recommend" OR "waste of money"`~~ — avg Q1.8
~~`"switched from {{company_name}}" OR "left {{company_name}}"`~~ — avg Q1.4

---

## Awards / Recognition

### PRIMARY (Q4+ / C4+)

**`{{company_name}} top OR best {{category}} company`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: Best AI App Builders | Lovable

**`{{company_name}} named OR ranked OR recognized`**
- scores: Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4 | avg Q4.0 C5.0
- example: I Ranked Every AI App Builder for 2026: Lovable vs. Bolt ... - YouTube

### FALLBACK (Q3+)

`{{company_name}} {{category}} award OR best` — avg Q3.8
`{{company_name}} awards OR recognition` — avg Q3.6
`{{company_name}} {{category}} industry award OR winner` — avg Q3.6
`{{company_name}} award OR recognition 2026` — avg Q3.4
`{{company_name}} "fastest growing" OR Inc 5000 OR deloitte fast 500` — avg Q3.0
`{{company_name}} "best place to work" OR "great place to work"` — avg Q3.0

### KILL

~~`{{company_name}} site:forbes.com OR site:inc.com`~~ — avg Q2.4
~~`{{company_name}} G2 leader OR "market leader" OR "category leader"`~~ — avg Q1.6

---
