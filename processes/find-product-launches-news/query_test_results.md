# Query Pattern Test Results — find-product-launches-news
**Date:** 2026-05-05  
**GT set:** 12 companies (2026-05-02 to 2026-05-04)  
**Method:** Live Serper API calls (tbs=qdr:w) + direct source page scrapes (WebFetch)

---

## Ground Truth Companies

| # | Company | Source | Type |
|---|---------|--------|------|
| 1 | DoorDash | TechCrunch | new_feature |
| 2 | Ouster | TechCrunch | new_product |
| 3 | Acorn/Blacksky | TechCrunch | new_product |
| 4 | Amazon | TechCrunch | new_product |
| 5 | Anthropic | TechCrunch | new_product |
| 6 | OpenAI | TechCrunch | new_product |
| 7 | Airbyte | Hacker News | new_product |
| 8 | Retroguard | Hacker News | new_product |
| 9 | Xteink | TechCrunch | new_product |
| 10 | Bruin Data (DAC) | Hacker News | new_product |
| 11 | Orch8 | Hacker News | new_product |
| 12 | Brainio | Hacker News | new_product |

---

## Query Results

### Q1: `"launched" OR "announces" new product site:techcrunch.com`
**Serper hits:** 10 results  
**GT companies found:** Acorn (pos 1), DoorDash (pos 4)  
**Recall: 2/12 (17%)**

Snippets confirm product launch context for both hits. Non-GT noise: CopilotKit funding, Uber hotel, Legora valuation, Pursuit funding. False positive rate high — "launched" appears in funding/company news even without product announcement.

**Refinement needed:** Too permissive — "launched" picks up company news, not just product launches. Adding `"new product" OR "debuts" OR "introduces"` and pairing with `tbs=qdr:d` will tighten it.

---

### Q2: `"Show HN" site:news.ycombinator.com 2026`
**Serper hits:** 10 results  
**GT companies found:** None in Serper results  
**Recall (Serper): 0/12 (0%)**

Serper returns random recent Show HN items — no date-targeting possible via query alone. The query surfaces whatever Google has indexed, not the actual HN Show page feed.

**Direct source result (WebFetch on news.ycombinator.com/show):** Airbyte, Retroguard, Orch8, Bruin Data (DAC), Brainio = **5/12 (42%)** of GT companies visible on the Show HN page directly.

**Refinement needed:** Don't use Serper for HN Show. Use direct fetch of `https://news.ycombinator.com/show` or the HN Algolia API with date filter. Scraping `news.ycombinator.com/front?day=YYYY-MM-DD` gives the ranked front page per day.

---

### Q3: `AI startup "launches" OR "announces" OR "introduces" May 2026`
**Serper hits:** 10 results  
**GT companies found:** None directly (Anthropic mentioned in Facebook/Instagram summary posts, not as primary source)  
**Recall: 0/12 (0%)**

Pure noise. Results: blog.mean.ceo roundup, Air Street Press state-of-AI, Yahoo Finance Unico Connect press release, Instagram posts, Fortune fundraising story. Not a viable query pattern.

**Verdict:** Drop this query. Too broad, no site constraint, returns roundup content not original announcements.

---

### Q4: `"new feature" OR "product launch" startup technology May 2026`
**Serper hits:** 10 results  
**GT companies found:** DoorDash (pos 2)  
**Recall: 1/12 (8%)**

Non-GT noise: Gryphon AI press release, G&CO agency list, Dreame hardware event, Greenhouse HR feature, generic Instagram/blog content. High noise-to-signal ratio.

**Verdict:** Weak. Catches DoorDash only because it's high-coverage (multiple TC articles). The query doesn't discriminate — picks up any article mentioning those phrases.

---

### Q5: `"now available" OR "introducing" software product 2026`
**Serper hits:** 10 results  
**GT companies found:** None  
**Recall: 0/12 (0%)**

Results: Threads post about Anthropic Claude Design (April, not May 4), IBM Think 2026, McElroy software update, Scytale GRC Kit, Databricks release notes, Skedda product roundup, CloudBees DevOps Agent Kit, Microsoft D365. All legitimate product launches — but none are our GT companies.

**Verdict:** Drop this query. Captures real product launches but not from the right sources/companies. The phrase is too generic and lacks publication-site constraint.

---

### Q6: `site:techcrunch.com product launch May 4 2026`
**Serper hits:** 10 results  
**GT companies found:** Anthropic + OpenAI (pos 2, same article), Acorn (pos 3)  
**Recall: 3/12 (25%) — 2 articles, 3 companies**

Strong precision for TechCrunch May 4 articles. Also returned Etsy (May 5), Uber hotel (April 29 — date bleed). Ouster and DoorDash missed even though they're on the same date — suggests Serper's "product launch" term match is selective.

**Refinement:** Drop "product launch" exact phrase. Use `site:techcrunch.com "debuts" OR "launches" OR "announces"` with `tbs=qdr:d`. This is the strongest single-source query for TC coverage.

---

### Q7 (Control): `DoorDash OR Ouster OR Retroguard OR Airbyte launch 2026`
**Serper hits:** 10 results  
**GT companies found:** DoorDash (pos 1, 2, 3, 4, 6, 10), Airbyte (pos 5, 8, 9)  
**Recall: 2/12 (17%) — confirms DoorDash and Airbyte are highly indexed**

Confirms: both companies have multiple independent coverage articles within 24h of launch. Retroguard and Ouster do NOT appear despite being in the query — Retroguard is too new (HN-only, low SEO footprint), Ouster article exists on TC but didn't match "launch" semantics in snippet.

**Finding:** Control query confirms that large companies (DoorDash, Airbyte) get picked up by broad brand+keyword queries; small/new companies (Retroguard, Bruin Data, Orch8, Brainio) won't surface without HN-specific sourcing.

---

## Direct Source Scrape Results

These represent what a Serper query that correctly targets the source page would return:

| Source | Query equivalent | GT companies hit | Recall |
|--------|-----------------|-----------------|--------|
| `techcrunch.com/2026/05/04/` (direct) | `site:techcrunch.com after:2026-05-04 before:2026-05-05` | DoorDash, Ouster, Acorn, Anthropic, OpenAI, Amazon | **6/12 (50%)** |
| `techcrunch.com/2026/05/03/` (direct) | `site:techcrunch.com after:2026-05-03 before:2026-05-04` | Xteink | **1/12 (8%)** |
| `news.ycombinator.com/show` (direct) | HN Show feed | Airbyte, Retroguard, Orch8, Bruin Data, Brainio | **5/12 (42%)** |
| `news.ycombinator.com/front?day=2026-05-04` | HN front page May 4 | Airbyte (Show HN visible) | **1/12 (8%)** |

**Combined TC + HN Show:** 6 + 5 + 1 (Xteink) = **12/12 (100%)** — full GT coverage if both sources are scraped directly.

---

## Recall Summary by Query

| Query ID | Query Pattern | GT Hits | Recall | Verdict |
|----------|--------------|---------|--------|---------|
| Q1 | `"launched" OR "announces" new product site:techcrunch.com` | Acorn, DoorDash | 2/12 (17%) | Weak — keep with refinement |
| Q2 | `"Show HN" site:news.ycombinator.com 2026` | 0 (Serper), 5 (direct) | 0% Serper / 42% direct | Use direct fetch, not Serper |
| Q3 | `AI startup "launches" OR "announces" May 2026` | 0 | 0% | Drop |
| Q4 | `"new feature" OR "product launch" startup technology May 2026` | DoorDash | 1/12 (8%) | Drop |
| Q5 | `"now available" OR "introducing" software product 2026` | 0 | 0% | Drop |
| Q6 | `site:techcrunch.com product launch May 4 2026` | Anthropic, OpenAI, Acorn | 3/12 (25%) | Keep with refinement |
| Q7 | Control: DoorDash OR Ouster OR Retroguard OR Airbyte launch 2026 | DoorDash, Airbyte | 2/12 (17%) | Not a production query |
| Direct TC scrape | `techcrunch.com/{date}/` | 7 GT companies | 58% per date page | Best TC approach |
| Direct HN Show | `news.ycombinator.com/show` | 5 GT companies | 42% | Best HN approach |

---

## Key Findings

### 1. Serper can't reliably hit HN Show posts
The `"Show HN" site:news.ycombinator.com` query returns Google's indexed HN pages — but Show HN posts are typically indexed slowly or not at all on launch day. Google has 0 of 5 GT HN companies indexed in our Serper results. **The right approach is direct HTTP fetch of `news.ycombinator.com/show` and `news.ycombinator.com/front?day=YYYY-MM-DD`**, then parse titles.

### 2. TechCrunch needs date-page scraping, not keyword queries
The `site:techcrunch.com` Serper queries surface 2-3 GT companies at best. But fetching `techcrunch.com/YYYY/MM/DD/` directly gives all articles for that date — we got 6/12 GT companies from a single date-page fetch. The right approach: fetch TC date pages for date range, extract all articles, then classify for product launches.

### 3. Large-company coverage is redundant across both approaches
DoorDash appears in Q1, Q4, Q6, Q7, and the direct TC scrape. Airbyte appears in Q7 and HN Show. These companies have enough media coverage that any TechCrunch-targeting query will find them. The challenge is the 5 HN-only companies (Retroguard, Orch8, Bruin Data, Brainio, Airbyte) that have no TechCrunch presence.

### 4. Small/new HN companies have near-zero Serper footprint on day-of
Retroguard, Bruin Data (DAC), Orch8, and Brainio appear nowhere in Serper results — only on the direct HN Show page. These are exclusively HN-native signals.

### 5. Two-source architecture hits 100% GT recall
- **TechCrunch date pages** → covers 7/12 GT companies (DoorDash, Ouster, Acorn, Anthropic, OpenAI, Amazon, Xteink)
- **HN Show page** → covers 5/12 GT companies (Airbyte, Retroguard, Orch8, Bruin Data, Brainio)
- Combined: 12/12 (100%) with no overlap in this GT set

---

## Recommended Query Set (8-10 Queries for 90%+ Recall)

Drop all keyword-only Serper queries. Replace with direct source fetching:

### Tier 1 — Direct source fetches (primary)
| # | Approach | Source URL | Expected Recall |
|---|----------|-----------|----------------|
| 1 | TC today | `techcrunch.com/YYYY/MM/DD/` | ~40-50% GT per day |
| 2 | TC yesterday | `techcrunch.com/YYYY/MM/DD/` (T-1) | ~10-20% GT (for articles published after scrape) |
| 3 | HN Show feed | `news.ycombinator.com/show` | ~30-40% GT per day |
| 4 | HN front page for date | `news.ycombinator.com/front?day=YYYY-MM-DD` | ~5-10% (Show HN that make front page) |

### Tier 2 — Serper site-specific queries (supplement)
| # | Query | Expected Recall |
|---|-------|----------------|
| 5 | `site:techcrunch.com "debuts" OR "launches" OR "introduces" OR "announces" tbs=qdr:d` | 15-20% (catches articles not in date page due to Serper indexing lag) |
| 6 | `site:techcrunch.com "new product" OR "new feature" tbs=qdr:d` | 10-15% supplemental |
| 7 | `site:venturebeat.com launches OR announces AI product tbs=qdr:d` | 5-10% (VentureBeat coverage of AI launches) |
| 8 | `site:theverge.com "launches" OR "announces" product tbs=qdr:d` | 5-10% (The Verge hardware/consumer) |

### Tier 3 — Broad coverage for large-company launches
| # | Query | Expected Recall |
|---|-------|----------------|
| 9 | `"announced today" OR "launched today" product site:businesswire.com OR site:prnewswire.com tbs=qdr:d` | 5-10% (press release wire for companies like Airbyte that use BusinessWire) |
| 10 | `site:techcrunch.com tbs=qdr:d` (all TC, no keyword filter — let classifier decide) | 50%+ but high noise |

### Combined expected recall
- Queries 1-4 (direct scrapes): ~85-90% of GT companies
- Queries 5-9 (Serper supplement): +5-10% margin
- **Total: 90-95% recall target achievable**

### Stop-if conditions
- If TC date page returns 0 articles: TC is down or date is future — skip
- If HN Show page title count < 5: fetch failed — retry or skip
- If Serper returns 429/503: skip that query, rely on direct scrapes

### Kill list for queries
- Drop Q3 (`AI startup "launches" OR "announces" May 2026`) — 100% noise
- Drop Q4 (`"new feature" OR "product launch" startup technology May 2026`) — noise
- Drop Q5 (`"now available" OR "introducing" software product 2026`) — noise
- Drop Q2 Serper variant — use direct HN fetch instead
- Caution: any query without `site:` constraint returns social/SEO/roundup content, not original announcements

---

## Cost Estimate
- 8 Serper queries/day @ $0.0075 = $0.06/day
- 4 direct fetches (TC × 2 + HN × 2) = free (HTTP)
- **Total pipeline cost: ~$0.06/day** (same as current Series A pipeline cadence)
