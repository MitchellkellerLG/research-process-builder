---
status: validated
last_validated: 2026-03-18
searches_run: 3357
---
# find-profiles -- Status

## Validation Summary
**validated:** 25 companies across 4 tiers (3,357 searches). company_profile: multi-platform site: queries ENRICHMENT Q3.8 (T3-T4 actually strong at Q3.8-4.0). funding_financial: `{{company_name}} {{category}} funding` PRIMARY Q4.0 all tiers.

## Category Mapping
- company_profile
- funding_financial
- social_media

## Champion Patterns
- `company_profile`: `site:rocketreach.co {{company_name}}` -- avg_q 4.0
- `funding_financial`: `{{company_name}} funding` -- avg_q 4.0
- `social_media`: `site:linkedin.com/company/{{company_name}}` -- avg_q 4.0

## Annealment History
- `company_profile`: initial 0.2064 -> final 0.3468 (+0.1404)
- `funding_financial`: initial 0.6560 -> final 0.6667 (+0.0107)

## Ground Truth Companies
10 companies: attio, baseten, clickup, datadog, gumloop, hubspot, notion, salesforce, stripe, tinybird
