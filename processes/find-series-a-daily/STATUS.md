---
status: monitoring
last_validated: 2026-04-20
searches_run: 10
---
# find-series-a-daily -- Status

## Validation Summary
SerperDev Search + tbs:qdr:d = 7/8 (88%) GT hit rate across 10 queries at ~0.01/run.

## Category Mapping
- funding_financial (monitoring variant -- date-in, company-list-out)

## Deployment
- Target: TriggerDev cron (daily 7am ET)
- Cost: ~0.008-0.02/day

## Next Steps
- [ ] Migrate to isolated worktree (monitor/series-a-daily branch)
