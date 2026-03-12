# data source tiering by company size

reliability matrix based on 3,357 searches across 25 companies in 4 size tiers. only Q3+ results included (results that returned relevant, actionable data).

## test set

| tier | companies | description |
|------|-----------|-------------|
| T1 Enterprise | SpaceX, Salesforce, Stripe, HubSpot, Datadog | household names, extensive web presence |
| T2 Growth | Clay, Cursor, ClickUp, Lovable, Notion, Figma, Ramp, Mercury | Series A-D, growing press coverage |
| T3 Early | Baseten, Hyperbound, Tavus, Tinybird, Vapi, Causal, Rewatch | seed/Series A, limited press, 10-100 employees |
| T4 Micro | Hoo.be, Cluely, Gumloop, Attio, Grain | <50 employees, minimal web footprint |

## source reliability matrix

frequency each source appears in Q3+ search results, by company tier. higher = more reliable at that tier.

| source | T1 Enterprise | T2 Growth | T3 Early | T4 Micro | overall | notes |
|--------|:---:|:---:|:---:|:---:|:---:|-------|
| linkedin.com | 35% | 42% | 46% | 42% | 41% | most reliable source across ALL tiers. even T4 companies have LinkedIn profiles. |
| youtube.com | 25% | 33% | 23% | 30% | 28% | strong across tiers. podcast/interview content surfaces people names. |
| reddit.com | 20% | 25% | 10% | 23% | 20% | drops at T3 (niche companies not discussed on reddit) but recovers at T4 (community buzz). |
| zoominfo.com | 11% | 11% | 11% | 9% | 11% | remarkably consistent across tiers. even tiny companies indexed. |
| rocketreach.co | 11% | 9% | 11% | 8% | 10% | consistent coverage, similar to zoominfo. slightly better for T3. |
| facebook.com | 10% | 8% | 10% | 9% | 9% | noise floor. rarely the primary signal. |
| instagram.com | 5% | 5% | 8% | 14% | 7% | spikes at T4. micro companies often have stronger social presence than web presence. |
| x.com | 7% | 5% | 6% | 10% | 7% | similar pattern to instagram. more useful for T4 micro. |
| theorg.com | 8% | 3% | 7% | 3% | 5% | org chart data. useful for T1 and T3 but inconsistent. |
| medium.com | 2% | 7% | 3% | 7% | 5% | growth-stage and micro companies publish on medium more than enterprise. |
| g2.com | 2% | 2% | 7% | 4% | 4% | better for T3 software companies with early adopters writing reviews. |
| crunchbase.com | 2% | 2% | 5% | 4% | 3% | surprisingly low overall. funding data exists but Serper doesn't surface it well. |
| comparably.com | 9% | 1% | 0% | 0% | 3% | enterprise-only. zero coverage for T3-T4. |

## source tiers

### tier S: always search (40%+ frequency)
- **linkedin.com** — profiles, company pages, people titles. works at every company size.

### tier A: reliable (20-39% frequency)
- **youtube.com** — interviews, podcasts, product demos. surfaces names.
- **reddit.com** — community discussions, reviews, complaints. weaker for T3 niche.

### tier B: useful supplement (10-19% frequency)
- **zoominfo.com** — company intel, org charts, people data. consistent across tiers.
- **rocketreach.co** — people data, titles, company info. domain is `.co` not `.com`.
- **instagram.com** — T4 micro companies over-index here.

### tier C: situational (5-9% frequency)
- **x.com** — better for micro companies and founder-led brands.
- **theorg.com** — org chart data. inconsistent coverage.
- **medium.com** — authored content. growth-stage companies publish here.
- **facebook.com** — rarely the primary signal for anything.

### tier D: unreliable (<5% frequency)
- **g2.com** — software reviews only. only useful if company has G2 presence.
- **crunchbase.com** — funding data exists but rarely surfaces via Serper search.
- **comparably.com** — enterprise companies only. zero coverage below T2.

## key findings

1. **linkedin dominates every tier.** 41% overall, never drops below 35%. the single most reliable source regardless of company size.

2. **zoominfo and rocketreach are tier-agnostic.** 9-11% across all tiers. not dominant but reliably present even for T4 micro companies. use `site:zoominfo.com` and `site:rocketreach.co` queries for people data at any company size.

3. **social platforms spike at T4.** instagram (14%) and x.com (10%) are more useful for micro companies than enterprise. founder-led brands live on social.

4. **crunchbase is overrated for Serper.** only 3% overall despite being the go-to funding database. the data exists but Serper search doesn't reliably surface crunchbase pages. direct site: queries work better.

5. **comparably is enterprise-only.** 9% at T1, literally 0% at T3-T4. do not use for smaller companies.

6. **reddit drops at T3 but not T4.** niche B2B startups (T3) aren't discussed on reddit, but micro companies with consumer or developer communities (T4) get reddit mentions.

## pattern implications

- for T3-T4 companies, prefer `site:zoominfo.com` and `site:rocketreach.co` over general web queries
- for T4 micro companies, add social platform checks (`site:x.com`, `site:instagram.com`)
- for T1-T2 companies, general queries work well. platform-specific searches are supplementary
- `site:crunchbase.com {{company_name}}` should be used explicitly rather than hoping crunchbase surfaces organically
- never use `site:comparably.com` for T3-T4 companies

## validation

- 3,357 total searches across 25 companies
- Q3+ results analyzed: T1: 628, T2: 946, T3: 640, T4: 436
- 37 search categories (20 company intel + 17 people finding)
- cost: ~$0.33 total ($0.20 Round 1 + $0.13 Round 2)
