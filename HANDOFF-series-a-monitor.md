# Series A Daily Monitor — Handoff

**last session:** 2026-04-21
**status:** pipeline built and validated end-to-end. all 4 stages working. ready for Supabase table creation + TriggerDev deployment.

## what's done

1. **Full 4-stage pipeline built** — `scripts/series_a_pipeline.py`
2. **Stage 1: Discovery** — 10 SerperDev queries in parallel (ThreadPoolExecutor), ~61 raw results
3. **Stage 2: Filter/Dedup** — title-priority round detection, VC name disambiguation, noise filtering. 61 raw -> 13-15 companies
4. **Stage 3: Enrich** — Spider Cloud primary scraper, GPT-4o-mini extraction (company name, domain, amount, lead investors, round reasoning). GPT also filters false positives via NOT_SERIES_A signal
5. **Stage 4: Output** — daily CSV + JSON + master CSV + Supabase upsert (with dedup on company_name + date)
6. **Supabase integration** — code complete, schema written. Needs table creation in SQL Editor
7. **Ground truth validated** — 88% hit rate (April 20), 75% on April 21 (GT aging out of 24h window)
8. **Live test results** — 13 real Series A companies discovered April 21 with lead investors and round reasoning

## what's NOT done

### 1. Create Supabase table

**Action:** Run `scripts/supabase_schema.sql` in Supabase SQL Editor (supabase.com/dashboard -> SQL Editor -> paste and run). Then test with:
```
py scripts/series_a_pipeline.py --skip-enrich --stage 4
```
Should show "Supabase: 13/13 rows upserted" or similar.

**Note:** Pipeline uses SUPABASE_ANON_KEY (from .env). RLS is disabled on this table. If you enable RLS later, switch to a service role key.

### 2. TriggerDev Deployment

**Build:** TypeScript wrapper that calls the Python pipeline or reimplements in TS.

**Architecture options:**
- **Option A (recommended):** TriggerDev task shells out to `py scripts/series_a_pipeline.py` — fastest to ship, Python pipeline already validated
- **Option B:** Rewrite pipeline in TypeScript native — cleaner for TriggerDev but duplicates validated logic

**Schedule:**
- Daily: 7am ET (`0 7 * * *`)
- Weekly catch-up: Monday 8am ET (`0 8 * * 1`) with `--tbs qdr:w`

**Notification:** Add Telegram/Slack message on completion with count of new companies found.

**Needs:** TriggerDev project structure, SDK version, how existing tasks are defined. Mitch to provide docs.

### 3. EU Coverage Gap Fix

**Status:** Partially fixed. q8 (European queries) caught VisioLab ($11M) and Smart Robotics (EUR10M) on April 21. Wamo and Archangel Lightworks still missed in daily window (found in weekly).

**Remaining fix options:**
- Add `site:sifted.eu Series A raised` query
- Try `gl: "gb"` or `gl: "de"` for EU-biased results
- Add dedicated Sifted/TechFunding.eu queries

### 4. Pipeline Polish

**Minor issues for future iteration:**
- DinoTecia/Dnotitia duplicate (different source pages, OCR-variant names). Could add fuzzy dedup on domain match
- Master CSV appends on every run — needs dedup or replace logic for reruns
- Amount normalization inconsistent ("$8.5 Million" vs "$8.5M" vs "EUR10M")
- `--stage 4` flag only stops at that stage, doesn't resume from cached stage 3. Would need `--from-stage` flag

## files reference

| file | purpose |
|------|---------|
| `scripts/series_a_pipeline.py` | main pipeline — all 4 stages |
| `scripts/test_news_discovery.py` | test harness — runs queries against GT |
| `scripts/supabase_schema.sql` | Supabase table creation SQL |
| `processes/find-series-a-daily.md` | full pipeline spec with validated queries |
| `output/series-a-YYYY-MM-DD.csv` | daily output CSV |
| `output/series-a-YYYY-MM-DD.json` | daily output JSON |
| `output/series-a-master.csv` | running master CSV |
| `output/stages/stage1-*.json` | cached discovery results |
| `output/stages/stage2-*.json` | cached scored/filtered results |
| `output/stages/stage3-*.json` | cached enriched results |
| `searches/news-discovery-comparison.md` | endpoint comparison report |

## API integrations

| Service | Env Var | Role | Cost/Run |
|---------|---------|------|----------|
| SerperDev | `SERPER_API_KEY` | Discovery queries + domain lookup | $0.020 |
| Spider Cloud | `SPIDER_API_KEY` | Primary web scraper | $0.013 |
| OpenAI | `OPENAI_API_KEY` | GPT-4o-mini extraction | $0.019 |
| Supabase | `SUPABASE_URL` + `SUPABASE_ANON_KEY` | Data storage | free tier |

**Total: ~$0.052/run, ~$2/month, ~$25/year**

## pipeline CLI reference

```bash
# Full daily run
py scripts/series_a_pipeline.py

# Weekly catch-up
py scripts/series_a_pipeline.py --tbs qdr:w

# Skip enrichment (fast, no scraping/GPT)
py scripts/series_a_pipeline.py --skip-enrich

# Run specific stage (loads cached prior stages)
py scripts/series_a_pipeline.py --stage 2

# Limit enrichment to top N companies
py scripts/series_a_pipeline.py --max-enrich 10

# Preview queries without running
py scripts/series_a_pipeline.py --dry-run
```

## model routing

| stage | model | why |
|-------|-------|-----|
| discovery (search) | SerperDev API | $0.001/query, no LLM needed |
| scoring/filtering | regex + heuristics | free, no LLM needed for round type detection |
| scraping | Spider Cloud | handles 403s, returns clean markdown |
| extraction | GPT-4o-mini | cheapest with structured output quality. correctly filters non-Series A |
| domain lookup | SerperDev API | simple search, no LLM needed |

## key decisions made

1. **Spider Cloud primary, requests fallback** — Spider handles 403s (FinSMEs, paywalled sites) and returns clean markdown
2. **GPT-4o-mini for extraction** — cheap ($0.001/call), accurate enough for structured data extraction, correctly filters false positives
3. **Title-priority round detection** — snippets contain text from adjacent articles on aggregator pages. Title is authoritative for round type
4. **NOT_SERIES_A GPT signal** — extraction prompt tells GPT to flag non-Series A articles. Caught Vertical Aerospace (financing package) and Aspire Biopharma (private placement)
5. **Supabase with ANON_KEY** — works for inserts with RLS disabled. Switch to service role key if RLS enabled later
6. **Parallel query execution** — ThreadPoolExecutor with 4 workers. All 10 queries complete in ~3 seconds

## validated April 21 output (13 companies)

| Company | Domain | Amount | Lead Investors |
|---------|--------|--------|----------------|
| VisioLab | visiolab.io | $11M | eCAPITAL, Simon Capital |
| Smart Robotics | smart-robotics.io | EUR10M | Rotterdamse Havendraken |
| Ethermed | ethermed.ai | $8.5M | not_stated |
| Hata | hata.io | $8M | Bybit |
| Cerca Magnetics | cercamagnetics.com | GBP3.8M | Guinness Ventures |
| Ideally | goideally.com | $13.4M | Shearwater Capital |
| Dnotitia | dnotitia.com | KRW 90B | Elohim Partners |
| Nas.com | nas.com | $27M | Vinod Khosla |
| CreaoAI | creao.ai | $10M | Prosperity7 Ventures |
| INVIA | invia.live | $1.2M | not_stated |
| RIIG/HOOTL | hootl.com | $6M | Family Offices |
| Dnotitia (dupe) | dnotitia.com | KRW 90B | not_stated |
| Rivan Industries | rivan.com | GBP25M | IQ Capital |
