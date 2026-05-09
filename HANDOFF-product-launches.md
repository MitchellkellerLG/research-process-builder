# Handoff: Product Launch Signal Pipeline

**Date:** 2026-05-05
**Status:** Deployed to Trigger.dev, needs enrichment stage + Supabase migration

## What's Done

Two pipelines discovering product launches daily:

### Product Hunt Pipeline (`product-launches-ph-daily`, 9 AM ET)
- Scrapes PH leaderboard via date-parameterized URL
- Classifies new_product vs new_feature using postsCount from product pages
- Flags is_ai from categories/tagline
- **Validated:** 100% recall, 90% launch_type accuracy, 90% is_ai accuracy

### News Pipeline (`product-launches-news-daily`, 10 AM ET)
- Hybrid: direct TC date page + HN Show scrape (primary, 100% GT recall) + 4 Serper queries (supplement)
- GPT-4o-mini classifies launch_type, is_ai, extracts company/product names
- **Validated:** 92% recall, 100% launch_type, 100% is_ai

### Deployed
- Trigger.dev version `20260506.1` — both tasks live, cron scheduled
- TypeScript pipeline modules in `trigger/src/pipeline/product-launches-{ph,news}.ts`
- Types in `trigger/src/pipeline/product-launch-types.ts`

## What's NOT Done

### 1. Supabase Migration (morning task)
Run `trigger/supabase/migrations/003_product_launches.sql` in Supabase dashboard.
Without it, tasks run but data doesn't persist.

### 2. Enrichment Stage (next session)
Pipeline outputs `company_domain` but doesn't enrich. Plan:
- Pass each domain through **Clay CLI waterfall enrichment** (CloudFlare funnel)
- Get full company info: employee count, industry, tech stack, LinkedIn URL, funding stage
- Add `linkedin_url`, `employee_count`, `industry` columns to `product_launches` table
- Check domain against `funding_discoveries` table — flag companies already in funding pipeline

### 3. Website Deployment
User wants this data published on the website for free public access. Needs:
- API endpoint serving `product_launches` table (Supabase REST or Edge Function)
- Frontend page on leadgrow.ai showing daily launches

### 4. Quality Gate
Last ~10% accuracy gap. Options:
- PH: fetch product page for every product (currently only for launch_type, could verify is_ai too)
- News: Xteink X3 missed because TC ran it as a "review" not a "launch" — edge case, acceptable

## Key Files

| File | Purpose |
|------|---------|
| `processes/find-product-launches-ph/process.md` | Process spec |
| `processes/find-product-launches-news/process.md` | Process spec |
| `processes/find-product-launches-*/ground_truth.json` | GT data |
| `processes/find-product-launches-news/query_test_results.md` | Query pattern validation |
| `scripts/product_launch_ph_pipeline.py` | Python pipeline (dev/testing) |
| `scripts/product_launch_news_pipeline.py` | Python pipeline (dev/testing) |
| `trigger/src/product-launches-ph-daily.ts` | Trigger.dev cron task |
| `trigger/src/product-launches-news-daily.ts` | Trigger.dev cron task |
| `trigger/src/pipeline/product-launches-ph.ts` | TS pipeline module |
| `trigger/src/pipeline/product-launches-news.ts` | TS pipeline module |
| `trigger/src/pipeline/product-launch-types.ts` | TypeScript types |
| `trigger/supabase/migrations/003_product_launches.sql` | DB migration |

## Key Design Decisions
- `is_ai` is a column, not a filter — all launches captured regardless
- Direct page scraping >> Serper keyword queries (100% vs 25% recall on news GT)
- PH postsCount extracted from HTML via regex — zero extra GPT cost for launch_type
- News pipeline runs after PH (10 AM vs 9 AM) for dedup potential
