# Series A Query Audit — 2026-04-29

> **Purpose:** Systematic audit of the 10 current Serper queries in `series_a_pipeline.py`.
> Tests each against `/search` and `/news` endpoints with `tbs:qdr:d`. Signal rate = results passing all pipeline filters / total results.
> Also tests 10 replacement candidate queries.

## Current Query Results

| ID | Desc | Endpoint | Total | Passing | Signal Rate | Status |
|----|----- |----------|-------|---------|-------------|--------|
| q3 | TheSaaSNews | /search | 5 | 3 | 60% | HEALTHY |
| q3 | TheSaaSNews | /news | 2 | 0 | 0% | DEAD |
| q4 | FinSMEs | /search | 9 | 9 | 100% | HEALTHY |
| q4 | FinSMEs | /news | 10 | 7 | 70% | HEALTHY |
| q5 | AlleyWatch | /search | 2 | 2 | 100% | HEALTHY |
| q5 | AlleyWatch | /news | 3 | 2 | 67% | HEALTHY |
| q9 | VCNewsDaily | /search | 0 | 0 | 0% | DEAD |
| q9 | VCNewsDaily | /news | 0 | 0 | 0% | DEAD |
| q10 | InfotechLead | /search | 1 | 1 | 100% | HEALTHY |
| q10 | InfotechLead | /news | 1 | 0 | 0% | DEAD |
| q1 | broad sweep | /search | 9 | 9 | 100% | HEALTHY |
| q1 | broad sweep | /news | 10 | 7 | 70% | HEALTHY |
| q2 | announcement language | /search | 9 | 9 | 100% | HEALTHY |
| q2 | announcement language | /news | 10 | 9 | 90% | HEALTHY |
| q6 | press wires | /search | 9 | 9 | 100% | HEALTHY |
| q6 | press wires | /news | 10 | 6 | 60% | HEALTHY |
| q7 | VC language | /search | 10 | 6 | 60% | HEALTHY |
| q7 | VC language | /news | 5 | 1 | 20% | DEAD |
| q8 | European | /search | 4 | 4 | 100% | HEALTHY |
| q8 | European | /news | 7 | 5 | 71% | HEALTHY |

## Per-Query Detail

### q3 — TheSaaSNews
**Query:** `site:thesaasnews.com Series A`

- **/search:** 5 results, 3 passing, 60% signal — **HEALTHY**
- **/news:** 2 results, 0 passing, 0% signal — **DEAD**

**Good results (/search):**
- Windmill Raises $12 Million in Funding | The SaaS News
- Segura Raises $8 Million Seed Round | The SaaS News
- Copperhelm Secures $7M Seed Funding | The SaaS News

**Noise slipping through (/search):**
- SPREAD AI Raises $30M in Series B | The SaaS News [non-Series A in title]
- Actively Raises $45 Million Series B | The SaaS News [non-Series A in title]

### q4 — FinSMEs
**Query:** `site:finsmes.com Series A`

- **/search:** 9 results, 9 passing, 100% signal — **HEALTHY**
- **/news:** 10 results, 7 passing, 70% signal — **HEALTHY**

**Good results (/search):**
- Clarasight Raises $11.5M in Series A Funding - FinSMEs
- IC Realtime Raises $2M in Series A Funding - FinSMEs
- Performativ Raises $14M in Series A Funding - FinSMEs

### q5 — AlleyWatch
**Query:** `site:alleywatch.com funding report`

- **/search:** 2 results, 2 passing, 100% signal — **HEALTHY**
- **/news:** 3 results, 2 passing, 67% signal — **HEALTHY**

**Good results (/search):**
- Shade Raises $14M as Creative Teams Replace Fragmented ...
- Zamp Raises $30M to Scale AI-Driven Sales Tax Compliance ...

### q9 — VCNewsDaily
**Query:** `site:vcnewsdaily.com Series A`

- **/search:** 0 results, 0 passing, 0% signal — **DEAD**
- **/news:** 0 results, 0 passing, 0% signal — **DEAD**

> **/news endpoint returns 0 results for this query.**

### q10 — InfotechLead
**Query:** `site:infotechlead.com venture capital funding`

- **/search:** 1 results, 1 passing, 100% signal — **HEALTHY**
- **/news:** 1 results, 0 passing, 0% signal — **DEAD**

**Good results (/search):**
- Latest tech trends, technology in enterprises - InfotechLead

### q1 — broad sweep
**Query:** `"Series A" raises OR raised OR funding OR round million`

- **/search:** 9 results, 9 passing, 100% signal — **HEALTHY**
- **/news:** 10 results, 7 passing, 70% signal — **HEALTHY**

**Good results (/search):**
- OpenLight Secures $50 Million in Series A-1 Funding to Accelerate…
- Manifest OS Raises $60 Million Series A at $750 Million Valuation
- Exchange startup Liquid raises $18 million Series A for leveraged ...

### q2 — announcement language
**Query:** `"Series A" announces OR secures OR closes OR completes funding`

- **/search:** 9 results, 9 passing, 100% signal — **HEALTHY**
- **/news:** 10 results, 9 passing, 90% signal — **HEALTHY**

**Good results (/search):**
- Gaming FinTech PvX Partners closes $10.5m Series A
- mbiomics Announces Third Closing of Series A, Reaching €30 ...
- Gaming FinTech PvX Partners closes $10.5m Series A - LinkedIn

### q6 — press wires
**Query:** `"Series A" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com`

- **/search:** 9 results, 9 passing, 100% signal — **HEALTHY**
- **/news:** 10 results, 6 passing, 60% signal — **HEALTHY**

**Good results (/search):**
- Scout AI Raises $100M Series A to Build the AI Brain for Unmanned ...
- Cybord Raises $7M Extended Series A; Establishes U.S. Sales ...
- IC Realtime Secures $2 Million Series A Funding Round

### q7 — VC language
**Query:** `"led the round" OR "led the Series A" OR "led a" Series A investment startup`

- **/search:** 10 results, 6 passing, 60% signal — **HEALTHY**
- **/news:** 5 results, 1 passing, 20% signal — **DEAD**

**Good results (/search):**
- Goldman Sachs and Bain Lead Investment in AI Marketing Startup
- AI-powered recruiting startup Dex raises $5.3 million seed round
- @mojro_technologies has raised $5.5 million in a Series A round ...

**Noise slipping through (/search):**
- From Plumbers to Moonshots, AI Investors Left Nothing Unfunded [no Series A mention and no funding amount]
- Wealth management firms are crashing the venture-capital party [non-Series A round, no Series A mention]

### q8 — European
**Query:** `"Series A" startup funding site:eu-startups.com OR site:tech.eu OR site:techround.co.uk`

- **/search:** 4 results, 4 passing, 100% signal — **HEALTHY**
- **/news:** 7 results, 5 passing, 71% signal — **HEALTHY**

**Good results (/search):**
- As Europe pushes for AI sovereignty, Germany's SPREAD raises ...
- European HealthTech Is Using AI To Catch Cancer Earlier
- Málaga's Freepik relaunches as Maginific with €200 million ARR

## Replacement Candidate Results

| ID | Desc | Endpoint | Total | Passing | Signal Rate |
|----|------|----------|-------|---------|-------------|
| rA1 | TechCrunch Series A | /search | 9 | 9 | 100% |
| rA2 | TheSaaSNews + year anchor | /search | 2 | 1 | 50% |
| rA3 | FinSMEs + year anchor | /search | 10 | 10 | 100% |
| rA4 | EU sources + year anchor | /search | 3 | 2 | 67% |
| rB1 | broad sweep + 2026 year anchor | /search | 9 | 7 | 78% |
| rB1_news | broad sweep + 2026 year anchor | /news | 10 | 8 | 80% |
| rB2 | Series B broad sweep | /search | 9 | 0 | 0% |
| rB2_news | Series B broad sweep | /news | 10 | 2 | 20% |
| rB3 | VC language + year anchor | /search | 10 | 10 | 100% |
| rB4 | press wires + year anchor | /search | 10 | 9 | 90% |
| rB5 | announcement + 2026 | /search | 10 | 9 | 90% |
| rB5_news | announcement + 2026 | /news | 10 | 8 | 80% |
| rB6 | Series B press wires | /search | 9 | 1 | 11% |
| rB6_news | Series B press wires | /news | 10 | 2 | 20% |

## Proposed Replacement Query Set

Based on audit findings. Drop dead/degraded queries, add TechCrunch, add year anchor to broad queries, add Series B signal layer.

```python
AGENT_A_QUERIES = [
    {"id": "q1", "query": "site:techcrunch.com \"Series A\"", "num": 20, "desc": "TechCrunch"},
    {"id": "q3", "query": "site:thesaasnews.com Series A", "num": 30, "desc": "TheSaaSNews"},
    {"id": "q4", "query": "site:finsmes.com Series A", "num": 30, "desc": "FinSMEs"},
    {"id": "q5", "query": "site:alleywatch.com funding report", "num": 10, "desc": "AlleyWatch"},
    {"id": "q10", "query": "site:infotechlead.com venture capital funding", "num": 10, "desc": "InfotechLead"},
]

AGENT_B_QUERIES = [
    {"id": "q1b", "query": "\"Series A\" raises OR raised OR funding OR round million", "num": 30, "desc": "broad sweep"},
    {"id": "q2b", "query": "\"Series A\" announces OR secures OR closes OR completes funding", "num": 20, "desc": "announcement language"},
    {"id": "q6b", "query": "\"Series A\" site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com", "num": 10, "desc": "press wires"},
    {"id": "q7b", "query": "\"led the round\" \"Series A\" 2026", "num": 20, "desc": "VC language 2026"},
]
```

## Endpoint Recommendations

For each query, whether to use `/search` or `/news`:

| Query ID | Desc | Recommended Endpoint | Reason |
|----------|------|---------------------|--------|
| q3 | TheSaaSNews | /search | /search 60% vs /news 0% |
| q4 | FinSMEs | /search | /search 100% vs /news 70% |
| q5 | AlleyWatch | /search | /search 100% vs /news 67% |
| q9 | VCNewsDaily | /search | /search sufficient |
| q10 | InfotechLead | /search | /search 100% vs /news 0% |
| q1 | broad sweep | /search | /search 100% vs /news 70% |
| q2 | announcement language | /search | /search 100% vs /news 90% |
| q6 | press wires | /search | /search 100% vs /news 60% |
| q7 | VC language | /search | /search 60% vs /news 20% |
| q8 | European | /search | /search 100% vs /news 71% |
| rA1 | TechCrunch Series A | /search | /search sufficient |
| rA2 | TheSaaSNews + year anchor | /search | /search sufficient |
| rA3 | FinSMEs + year anchor | /search | /search sufficient |
| rA4 | EU sources + year anchor | /search | /search sufficient |
| rB1 | broad sweep + 2026 year anchor | /search | /search 78% vs /news 80% |
| rB2 | Series B broad sweep | /news | /news signal 20% vs /search 0% |
| rB3 | VC language + year anchor | /search | /search sufficient |
| rB4 | press wires + year anchor | /search | /search sufficient |
| rB5 | announcement + 2026 | /search | /search 90% vs /news 80% |
| rB6 | Series B press wires | /search | /search 11% vs /news 20% |

## Key Findings

- **DEAD (1):** q9 (VCNewsDaily)
- **DEGRADED (0):** none
- **HEALTHY (9):** q3 (TheSaaSNews), q4 (FinSMEs), q5 (AlleyWatch), q10 (InfotechLead), q1 (broad sweep), q2 (announcement language), q6 (press wires), q7 (VC language), q8 (European)

- **Year anchor (2026) improved signal:** rB3 (VC language + year anchor): +40%
- **Series B queries:** signal rate too low — not adding
- **TechCrunch:** 9 results, 100% signal — adding to AGENT_A

---
*Generated by `scripts/query_audit.py`*