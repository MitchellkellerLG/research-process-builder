---
status: validated
last_validated: 2026-03-18
searches_run: 3357
---
# find-negativity -- Status

## Validation Summary
**validated:** 25 companies across 4 tiers (3,357 searches). FALLBACK at Q3.4. T1:Q4.0, T2:Q3.4, T3:Q3.5, T4:Q2.8. structurally limited: micro companies rarely have indexed complaints. all combo patterns (reddit, negative review) scored KILL. the current approach is the best available.

## Category Mapping
- customer_complaints
- reviews_sentiment

## Champion Patterns
- `customer_complaints`: `{{company_name}} problems OR issues OR complaints -careers -jobs -site:{{domain}}` -- avg_q 3.8
- `reviews_sentiment`: `{{company_name}} review` -- avg_q 4.0

## Annealment History
No baseline data available.

## Ground Truth Companies
10 companies: attio, baseten, clickup, datadog, gumloop, hubspot, notion, salesforce, stripe, tinybird
