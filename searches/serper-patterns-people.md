# serper people-finding patterns — validated reference

**validated:** 2026-03-11 (round 1 baseline + round 2 combo optimization)
**total queries tested:** 710 (470 round 1 + 240 round 2 combos)
**total cost:** ~$0.07
**cost per search:** $0.0001 via Serper vs $2-5 per lead via data vendors
**categories:** 17 role levels from founder to individual contributor
**PRIMARY patterns:** 39 variants across 15/17 categories

---

## how to use in Clay

each pattern below is a Clay HTTP API column:

1. add column > HTTP API
2. method: `POST`
3. URL: `https://google.serper.dev/search`
4. headers: `X-API-KEY: {{SERPER_API_KEY}}` and `Content-Type: application/json`
5. body: `{"q": "[pattern with your variables]", "gl": "us", "hl": "en", "num": 10}`
6. map response: `{{http_response.organic[0].title}}` or `{{http_response.organic[0].link}}`

**variables:** replace `{{company_name}}` with column reference `/Company Name/`, `{{domain}}` with `/Domain/`

---

## key findings from 710 searches

1. **LinkedIn profile searches dominate** — `site:linkedin.com/in` is the most reliable source across all role categories
2. **General keywords beat exact titles** — `"VP" sales OR revenue` outperforms `"VP Sales"` because it catches title variations
3. **Full title phrases work for C-suite** — `"chief technology" OR "chief product"` beats `CTO OR CPO` (less ambiguity)
4. **Exclusion operators are essential** — `-jobs -careers -salary` prevents job board noise from dominating results
5. **ZoomInfo is the only reliable data platform** — Apollo, TheOrg, AngelList all fail for smaller companies
6. **Company size matters** — patterns that work for SpaceX/ClickUp may fail for startups like Lovable/Cursor
7. **Media patterns surface undiscoverable names** — podcast/interview queries find people not in any database

---

## Founders / CEO / President

**best:** `{{company_name}} CEO OR founder interview OR podcast`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** founder names, CEO identity, co-founder profiles, founding stories, media appearances
**Clay body:** `{"q": "/Company Name/ CEO OR founder interview OR podcast", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "founded by" OR "co-founded" OR "started by"` (Q4.0)
**useful sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (2 more)

- `{{company_name}} "founded by" OR "co-founded" OR "started by"` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `{{company_name}} CEO OR founder OR "co-founder" interview OR podcast OR "founded by" -jobs` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (7)

- `{{company_name}} CEO OR founder site:rocketreach.co OR site:zoominfo.com` — avg Q3.8
- `{{company_name}} founder site:wellfound.com OR site:theorg.com` — avg Q3.6
- `site:linkedin.com/in {{company_name}} founder OR CEO OR "co-founder" -jobs -careers` — avg Q3.4
- *...and 4 more*

### KILL (1 patterns below Q3.0)

- ~~`{{company_name}} founder OR CEO OR president -jobs -careers -salary`~~ — avg Q1.6

---

## C-Suite Technical (CTO / CPO / CISO)

**best:** `{{company_name}} "chief technology" OR "chief product" OR "chief security" -jobs -careers`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** CTO, CPO, CISO names and profiles, technical leadership, architecture owners
**Clay body:** `{"q": "/Company Name/ "chief technology" OR "chief product" OR "chief security" -jobs -careers", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} CTO OR CPO interview OR podcast OR talk` (Q3.4)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### FALLBACK (6)

- `{{company_name}} CTO OR CPO interview OR podcast OR talk` — avg Q3.4
- `site:linkedin.com/in {{company_name}} "chief" technology OR product OR security OR information` — avg Q3.4
- `{{company_name}} CTO OR CPO OR CISO OR CIO -jobs -careers -salary` — avg Q3.4
- *...and 3 more*

### KILL (4 patterns below Q3.0)

- ~~`{{company_name}} CTO OR "chief technology officer" interview OR podcast OR "said" -jobs`~~ — avg Q2.6
- ~~`{{company_name}} CTO OR "chief technology officer" OR CPO -jobs -careers`~~ — avg Q2.2
- ~~`{{company_name}} CTO OR "chief technology" site:github.com OR site:linkedin.com/in`~~ — avg Q2.2
- *...and 1 more*

---

## C-Suite Commercial (CMO / CRO / CFO / COO)

**best:** `{{company_name}} "chief marketing" OR "chief revenue" OR "chief operating" -careers`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** CMO, CRO, CFO, COO names and profiles, commercial leadership team
**Clay body:** `{"q": "/Company Name/ "chief marketing" OR "chief revenue" OR "chief operating" -careers", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "chief marketing" OR "chief revenue" OR "chief financial" OR "chief operating" -jobs -careers` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (1 more)

- `{{company_name}} "chief marketing" OR "chief revenue" OR "chief financial" OR "chief operating" -jobs -careers` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (4)

- `{{company_name}} CMO OR CRO OR "chief marketing" OR "chief revenue" -jobs` — avg Q3.2
- `{{company_name}} CMO OR CRO OR CFO interview OR podcast` — avg Q3.2
- `site:linkedin.com/in {{company_name}} CMO OR CRO OR CFO OR COO` — avg Q3.2
- *...and 1 more*

### KILL (2 patterns below Q3.0)

- ~~`{{company_name}} CMO OR CRO site:crunchbase.com OR site:rocketreach.co`~~ — avg Q2.4
- ~~`site:linkedin.com/in {{company_name}} CMO OR CRO OR CFO OR COO -jobs -careers`~~ — avg Q1.8

---

## VP Sales / Revenue / Business Development

**best:** `{{company_name}} "VP" sales OR revenue OR partnerships -careers -salary`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** VP Sales, VP Revenue, VP BD names, sales leadership structure, partnership leads
**Clay body:** `{"q": "/Company Name/ "VP" sales OR revenue OR partnerships -careers -salary", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "VP" OR "Vice President" sales OR revenue OR partnerships OR "business development" -jobs -careers -salary` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (1 more)

- `{{company_name}} "VP" OR "Vice President" sales OR revenue OR partnerships OR "business development" -jobs -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (4)

- `site:linkedin.com/in {{company_name}} "VP" OR "Vice President" sales OR revenue` — avg Q3.8
- `{{company_name}} "VP Sales" OR "VP Revenue" OR "VP Business Development" -jobs` — avg Q3.6
- `{{company_name}} "VP Sales" OR "head of sales" speaker OR conference` — avg Q3.4
- *...and 1 more*

### KILL (2 patterns below Q3.0)

- ~~`site:linkedin.com/in {{company_name}} "VP Sales" OR "VP Revenue" OR "VP Business Development"`~~ — avg Q2.6
- ~~`{{company_name}} "VP Sales" OR "VP Revenue" site:rocketreach.co OR site:apollo.io`~~ — avg Q2.0

---

## VP Marketing / Growth / Demand Gen

**best:** `{{company_name}} "VP" marketing OR growth OR brand OR content -careers`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** VP Marketing, VP Growth names, marketing leadership, brand owners, demand gen leads
**Clay body:** `{"q": "/Company Name/ "VP" marketing OR growth OR brand OR content -careers", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "VP" OR "Vice President" marketing OR growth OR brand OR "demand gen" -jobs -careers -salary` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (1 more)

- `{{company_name}} "VP" OR "Vice President" marketing OR growth OR brand OR "demand gen" -jobs -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (3)

- `{{company_name}} "VP Marketing" OR "VP Growth" OR "VP Demand Gen" -jobs` — avg Q3.8
- `{{company_name}} "VP Marketing" OR "VP Growth" OR "Head of Marketing" OR "Head of Growth" -jobs -careers` — avg Q3.8
- `site:linkedin.com/in {{company_name}} "VP" marketing OR growth OR brand` — avg Q3.4

### KILL (3 patterns below Q3.0)

- ~~`{{company_name}} "VP Marketing" OR "VP Growth" podcast OR interview`~~ — avg Q2.8
- ~~`{{company_name}} "VP Marketing" OR "VP Growth" site:rocketreach.co OR site:apollo.io`~~ — avg Q2.6
- ~~`site:linkedin.com/in {{company_name}} "VP Marketing" OR "VP Growth" OR "VP Demand"`~~ — avg Q2.6

---

## VP Engineering / Product / Design

**best:** `{{company_name}} "VP" OR "Vice President" engineering OR product -jobs -careers`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** VP Engineering, VP Product names, technical leadership below C-suite
**Clay body:** `{"q": "/Company Name/ "VP" OR "Vice President" engineering OR product -jobs -careers", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "VP Engineering" OR "VP Product" OR "Head of Engineering" OR "Head of Product" -jobs -careers` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (1 more)

- `{{company_name}} "VP Engineering" OR "VP Product" OR "Head of Engineering" OR "Head of Product" -jobs -careers` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (5)

- `{{company_name}} "VP Engineering" OR "VP Product" OR VPE -jobs -careers` — avg Q3.8
- `{{company_name}} "VP Engineering" OR "VP Product" OR "VP Design" OR VPE -jobs -careers -salary` — avg Q3.8
- `site:linkedin.com/in {{company_name}} "VP" OR "Vice President" engineering OR product OR design` — avg Q3.8
- *...and 2 more*

### KILL (2 patterns below Q3.0)

- ~~`{{company_name}} "VP Engineering" OR "VP Product" site:rocketreach.co OR site:apollo.io`~~ — avg Q2.6
- ~~`{{company_name}} "VP Engineering" OR "VP Product" site:github.com OR site:linkedin.com/in`~~ — avg Q2.6

---

## Director Sales / BD / Partnerships

**best:** `site:linkedin.com/in {{company_name}} "Director" sales OR "business development"`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Director of Sales, BD Directors, Partnership Directors, revenue team structure
**Clay body:** `{"q": "site:linkedin.com/in /Company Name/ "Director" sales OR "business development"", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "Director" sales OR revenue OR partnerships -careers -salary` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (3 more)

- `{{company_name}} "Director" sales OR revenue OR partnerships -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `site:linkedin.com/in {{company_name}} "Director" account OR partnerships OR revenue` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `{{company_name}} "Director" OR "Senior Director" sales OR revenue OR partnerships -jobs -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (3)

- `{{company_name}} "Director of Sales" OR "Sales Director" OR "Director of BD" -jobs` — avg Q3.8
- `{{company_name}} "Director" sales site:rocketreach.co OR site:apollo.io` — avg Q3.2
- `site:linkedin.com/in {{company_name}} "Director" OR "Senior Director" sales OR "business development" OR partnerships OR revenue -jobs` — avg Q3.2

---

## Director Marketing / Content / Demand Gen

**best:** `site:linkedin.com/in {{company_name}} "Director" marketing OR content OR "demand gen"`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Director of Marketing, Content Directors, Brand Directors, demand gen leads
**Clay body:** `{"q": "site:linkedin.com/in /Company Name/ "Director" marketing OR content OR "demand gen"", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "Director of Marketing" OR "Marketing Director" OR "Director of Content" -jobs` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (3 more)

- `{{company_name}} "Director of Marketing" OR "Marketing Director" OR "Director of Content" -jobs` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `{{company_name}} "Director" marketing OR brand OR growth -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `{{company_name}} "Director" OR "Senior Director" marketing OR content OR growth OR brand -jobs -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (2)

- `{{company_name}} "Director" marketing conference OR speaker OR podcast` — avg Q3.8
- `{{company_name}} "Director" marketing site:rocketreach.co OR site:apollo.io` — avg Q3.0

### KILL (1 patterns below Q3.0)

- ~~`site:linkedin.com/in {{company_name}} "Director" marketing OR content OR "demand gen" OR brand -jobs`~~ — avg Q2.8

---

## Director Engineering / Product / Design

**best:** `site:linkedin.com/in {{company_name}} "Director" engineering OR product OR design`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Director of Engineering, Product Directors, Design Directors, platform leads
**Clay body:** `{"q": "site:linkedin.com/in /Company Name/ "Director" engineering OR product OR design", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "Director" engineering OR product OR platform -careers -salary` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (2 more)

- `{{company_name}} "Director" engineering OR product OR platform -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `{{company_name}} "Director" engineering OR product OR design OR platform -jobs -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (4)

- `{{company_name}} "Director of Engineering" OR "Engineering Director" OR "Director of Product" -jobs` — avg Q3.8
- `{{company_name}} "Director" engineering OR product site:github.com OR site:linkedin.com/in` — avg Q3.4
- `site:linkedin.com/in {{company_name}} "Director" OR "Senior Director" engineering OR product OR design -jobs` — avg Q3.4
- *...and 1 more*

---

## Head of Department (Growth / CS / Ops / Revenue)

**best:** `site:linkedin.com/in {{company_name}} "Head of" growth OR revenue OR operations`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Department heads across Growth, CS, Ops, Revenue, Partnerships
**Clay body:** `{"q": "site:linkedin.com/in /Company Name/ "Head of" growth OR revenue OR operations", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "Head of Growth" OR "Head of Revenue" OR "Head of Operations" -jobs` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (3 more)

- `{{company_name}} "Head of Growth" OR "Head of Revenue" OR "Head of Operations" -jobs` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `site:linkedin.com/in {{company_name}} "Head of" growth OR revenue OR operations OR "customer success" OR partnerships` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `{{company_name}} "Head of" growth OR revenue OR operations OR partnerships OR "customer success" -jobs -careers` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (3)

- `site:linkedin.com/in {{company_name}} "Head of" -jobs -careers` — avg Q3.8
- `{{company_name}} "Head of" site:rocketreach.co OR site:apollo.io` — avg Q3.2
- `{{company_name}} "Head of Customer Success" OR "Head of Partnerships" -careers` — avg Q3.0

---

## Sales Ops / SDR Managers / RevOps

**best:** `site:linkedin.com/in {{company_name}} "SDR Manager" OR "BDR Manager" OR "Sales Manager"`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** SDR/BDR Managers, Sales Managers, RevOps leads, Account Executive leadership
**Clay body:** `{"q": "site:linkedin.com/in /Company Name/ "SDR Manager" OR "BDR Manager" OR "Sales Manager"", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `site:linkedin.com/in {{company_name}} "Account Executive" OR "Sales Lead" OR "Sales Manager"` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (1 more)

- `site:linkedin.com/in {{company_name}} "Account Executive" OR "Sales Lead" OR "Sales Manager"` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (4)

- `site:linkedin.com/in {{company_name}} "SDR Manager" OR "BDR Manager" OR "Sales Manager" OR "Revenue Operations" OR RevOps` — avg Q3.8
- `{{company_name}} "SDR Manager" OR "Sales Manager" OR RevOps OR "Revenue Operations" -jobs -careers` — avg Q3.8
- `{{company_name}} "SDR Manager" OR "Sales Operations" OR "Revenue Operations" -jobs` — avg Q3.4
- *...and 1 more*

### KILL (1 patterns below Q3.0)

- ~~`{{company_name}} "SDR Manager" OR RevOps site:rocketreach.co OR site:apollo.io`~~ — avg Q1.0

---

## HR / People / Talent Leadership

**best:** `{{company_name}} "Head of Recruiting" OR "Talent Acquisition" OR "VP HR" -careers`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Head of Recruiting, VP People, Talent Acquisition leads, HR leadership
**Clay body:** `{"q": "/Company Name/ "Head of Recruiting" OR "Talent Acquisition" OR "VP HR" -careers", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "Head of Recruiting" OR "Head of Talent" OR "Talent Acquisition" OR "VP People" -jobs -careers` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (1 more)

- `{{company_name}} "Head of Recruiting" OR "Head of Talent" OR "Talent Acquisition" OR "VP People" -jobs -careers` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (3)

- `{{company_name}} people OR HR OR talent director OR VP -careers -jobs -salary` — avg Q3.8
- `site:linkedin.com/in {{company_name}} "Head of" OR "VP" people OR talent OR recruiting OR HR` — avg Q3.6
- `{{company_name}} "VP People" OR "Chief People Officer" OR "Head of Talent" -jobs` — avg Q3.4

### KILL (2 patterns below Q3.0)

- ~~`site:linkedin.com/in {{company_name}} "VP People" OR "Head of People" OR "HR Director"`~~ — avg Q2.8
- ~~`{{company_name}} "VP People" OR "Head of HR" site:rocketreach.co OR site:apollo.io`~~ — avg Q2.2

---

## Finance / Legal / Operations Leadership

**best:** `site:linkedin.com/in {{company_name}} finance OR operations OR legal VP OR director`
**avg Q:** 3.8 | **min Q:** 3 | tested across 5 companies
**what it surfaces:** VP Finance, VP Operations, General Counsel, Controller, financial leadership
**Clay body:** `{"q": "site:linkedin.com/in /Company Name/ finance OR operations OR legal VP OR director", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "Director of Finance" OR RevOps OR "Revenue Operations" -careers` (Q3.6)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q3 WEAK
- SpaceX: Q4 OK

### FALLBACK (5)

- `site:linkedin.com/in {{company_name}} finance OR operations OR legal VP OR director` — avg Q3.8
- `{{company_name}} "Director of Finance" OR RevOps OR "Revenue Operations" -careers` — avg Q3.6
- `{{company_name}} "VP Finance" OR "General Counsel" OR "VP Operations" -jobs` — avg Q3.0
- *...and 2 more*

### KILL (4 patterns below Q3.0)

- ~~`site:linkedin.com/in {{company_name}} "VP Finance" OR "Controller" OR "VP Operations"`~~ — avg Q2.6
- ~~`site:linkedin.com/in {{company_name}} "VP" OR "Director" finance OR operations OR legal -jobs -careers`~~ — avg Q2.4
- ~~`{{company_name}} CFO OR "VP Finance" OR Controller site:crunchbase.com OR site:rocketreach.co`~~ — avg Q2.0
- *...and 1 more*

---

## Technical Leads / Staff Engineers / Architects

**best:** `{{company_name}} "Engineering Manager" OR "Staff Engineer" OR "Architect" -jobs -careers`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Engineering Managers, Staff/Principal Engineers, Architects, Tech Leads
**Clay body:** `{"q": "/Company Name/ "Engineering Manager" OR "Staff Engineer" OR "Architect" -jobs -careers", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "Engineering Manager" OR "Staff Engineer" OR "Principal Engineer" OR "Architect" OR "Tech Lead" -jobs -careers -salary` (Q4.0)
**dominant sources:** linkedin.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (2 more)

- `{{company_name}} "Engineering Manager" OR "Staff Engineer" OR "Principal Engineer" OR "Architect" OR "Tech Lead" -jobs -careers -salary` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `site:linkedin.com/in {{company_name}} "Engineering Manager" OR "Staff Engineer" OR "Principal" OR "Architect"` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (3)

- `site:linkedin.com/in {{company_name}} "Engineering Manager" OR "Staff" OR "Principal"` — avg Q3.8
- `site:linkedin.com/in {{company_name}} "Staff Engineer" OR "Principal Engineer" OR "Tech Lead"` — avg Q3.4
- `{{company_name}} "Staff" OR "Principal" OR "Lead" engineer -junior -intern -jobs` — avg Q3.2

### KILL (2 patterns below Q3.0)

- ~~`{{company_name}} engineer OR developer site:stackoverflow.com OR site:dev.to`~~ — avg Q2.0
- ~~`{{company_name}} engineer OR developer site:github.com`~~ — avg Q1.8

---

## People Discovery via Media / Events

**best:** `{{company_name}} podcast guest OR interview OR episode`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Anyone at the company who appears on podcasts, conferences, interviews, keynotes
**Clay body:** `{"q": "/Company Name/ podcast guest OR interview OR episode", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} "said" OR "according to" OR "told" -jobs -careers` (Q3.8)
**dominant sources:** youtube.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### FALLBACK (6)

- `{{company_name}} "said" OR "according to" OR "told" -jobs -careers` — avg Q3.8
- `{{company_name}} "said" OR "according to" OR interview OR podcast -jobs -careers` — avg Q3.8
- `{{company_name}} site:youtube.com interview OR talk OR keynote` — avg Q3.6
- *...and 3 more*

### KILL (1 patterns below Q3.0)

- ~~`{{company_name}} "joins" OR "appointed" OR "promoted" OR "hires" -jobs`~~ — avg Q2.0

---

## People Discovery via Data Platforms

**best:** `{{company_name}} site:zoominfo.com -jobs`
**avg Q:** 4.0 | **min Q:** 4 | tested across 5 companies
**what it surfaces:** Employee profiles via ZoomInfo, RocketReach, Wellfound, org chart data
**Clay body:** `{"q": "/Company Name/ site:zoominfo.com -jobs", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `{{company_name}} site:zoominfo.com OR site:rocketreach.co -jobs` (Q4.0)
**useful sources:** zoominfo.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q4 OK

### also PRIMARY (3 more)

- `{{company_name}} site:zoominfo.com OR site:rocketreach.co -jobs` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `{{company_name}} site:zoominfo.com OR site:wellfound.com` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)
- `{{company_name}} site:zoominfo.com OR site:rocketreach.co OR site:wellfound.com -jobs` — avg Q4.0 (Clay Q4, ClickUp Q4, Cursor Q4, Lovable Q4, SpaceX Q4)

### FALLBACK (4)

- `{{company_name}} site:wellfound.com` — avg Q3.4
- `{{company_name}} site:rocketreach.co -jobs` — avg Q3.2
- `{{company_name}} site:theorg.com` — avg Q3.2
- *...and 1 more*

### KILL (2 patterns below Q3.0)

- ~~`{{company_name}} site:pitchbook.com OR site:craft.co`~~ — avg Q2.8
- ~~`{{company_name}} site:apollo.io`~~ — avg Q2.2

---

## People Discovery via Authored Content

**best:** `site:{{domain}} blog author OR "by" OR "written by"`
**avg Q:** 3.6 | **min Q:** 2 | tested across 5 companies
**what it surfaces:** Authors and contributors via company blogs, Medium, Substack, LinkedIn Pulse
**Clay body:** `{"q": "site:/Domain/ blog author OR "by" OR "written by"", "gl": "us", "hl": "en", "num": 10}`
**runner-up:** `site:{{domain}} blog OR news team OR "by" OR author` (Q3.4)
**useful sources:** medium.com

**per-company scores:**
- Clay: Q4 OK
- ClickUp: Q4 OK
- Cursor: Q4 OK
- Lovable: Q4 OK
- SpaceX: Q2 FAIL

### FALLBACK (4)

- `site:{{domain}} blog author OR "by" OR "written by"` — avg Q3.6
- `site:{{domain}} blog OR news team OR "by" OR author` — avg Q3.4
- `{{company_name}} site:medium.com OR site:substack.com OR site:linkedin.com/pulse` — avg Q3.2
- *...and 1 more*

### KILL (6 patterns below Q3.0)

- ~~`{{company_name}} author OR "written by" OR "published by" blog OR article OR post -jobs -careers`~~ — avg Q2.6
- ~~`{{company_name}} author OR "written by" blog OR article -jobs`~~ — avg Q2.4
- ~~`{{company_name}} site:dev.to OR site:hackernoon.com`~~ — avg Q2.0
- *...and 3 more*

---

## quick reference — ONE BEST per category

| Category | Best Pattern | Avg Q | Status |
|----------|-------------|-------|--------|
| Founders / CEO / President | `{{company_name}} CEO OR founder interview OR podcast` | 4.0 | PRIMARY |
| C-Suite Technical (CTO / CPO / CISO) | `{{company_name}} "chief technology" OR "chief product" OR "chief security" -jobs -careers` | 4.0 | PRIMARY |
| C-Suite Commercial (CMO / CRO / CFO / COO) | `{{company_name}} "chief marketing" OR "chief revenue" OR "chief operating" -careers` | 4.0 | PRIMARY |
| VP Sales / Revenue / Business Development | `{{company_name}} "VP" sales OR revenue OR partnerships -careers -salary` | 4.0 | PRIMARY |
| VP Marketing / Growth / Demand Gen | `{{company_name}} "VP" marketing OR growth OR brand OR content -careers` | 4.0 | PRIMARY |
| VP Engineering / Product / Design | `{{company_name}} "VP" OR "Vice President" engineering OR product -jobs -careers` | 4.0 | PRIMARY |
| Director Sales / BD / Partnerships | `site:linkedin.com/in {{company_name}} "Director" sales OR "business development"` | 4.0 | PRIMARY |
| Director Marketing / Content / Demand Gen | `site:linkedin.com/in {{company_name}} "Director" marketing OR content OR "demand gen"` | 4.0 | PRIMARY |
| Director Engineering / Product / Design | `site:linkedin.com/in {{company_name}} "Director" engineering OR product OR design` | 4.0 | PRIMARY |
| Head of Department (Growth / CS / Ops / Revenue) | `site:linkedin.com/in {{company_name}} "Head of" growth OR revenue OR operations` | 4.0 | PRIMARY |
| Sales Ops / SDR Managers / RevOps | `site:linkedin.com/in {{company_name}} "SDR Manager" OR "BDR Manager" OR "Sales Manager"` | 4.0 | PRIMARY |
| HR / People / Talent Leadership | `{{company_name}} "Head of Recruiting" OR "Talent Acquisition" OR "VP HR" -careers` | 4.0 | PRIMARY |
| Finance / Legal / Operations Leadership | `site:linkedin.com/in {{company_name}} finance OR operations OR legal VP OR director` | 3.8 | FALLBACK |
| Technical Leads / Staff Engineers / Architects | `{{company_name}} "Engineering Manager" OR "Staff Engineer" OR "Architect" -jobs -careers` | 4.0 | PRIMARY |
| People Discovery via Media / Events | `{{company_name}} podcast guest OR interview OR episode` | 4.0 | PRIMARY |
| People Discovery via Data Platforms | `{{company_name}} site:zoominfo.com -jobs` | 4.0 | PRIMARY |
| People Discovery via Authored Content | `site:{{domain}} blog author OR "by" OR "written by"` | 3.6 | FALLBACK |
