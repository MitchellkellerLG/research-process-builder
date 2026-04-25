# Monitor Architecture

Research processes that run on a schedule live as **isolated orphan branches** mounted via git worktrees.

## Why Isolation

- Independent git history per monitor (daily commits don't clutter master)
- Own versioning cadence (monitors evolve at runtime speed, not development speed)
- Can archive/delete a monitor without touching master
- Clean `git log` per monitor shows run history

## Structure

```
monitors/                          ← gitignored on master
  series-a-daily/                  ← worktree → branch monitor/series-a-daily
    config/monitor.json            ← schedule, sources, costs
    output/YYYY-MM-DD/             ← daily outputs
    runs/run-log.json              ← execution history
    scripts/                       ← pipeline code
    README.md
```

## Creating a New Monitor

```bash
# 1. Create orphan branch (no parent commits)
git checkout --orphan monitor/[name]
git rm -rf --cached .

# 2. Add monitor-specific files
mkdir -p config output runs scripts
# ... create config/monitor.json, README.md, etc.

# 3. Commit and return to master
git add . && git commit -m "feat: initialize [name] monitor"
git checkout master

# 4. Mount as worktree
git worktree add monitors/[name] monitor/[name]
```

## Active Monitors

| Monitor | Branch | Schedule | Status |
|---------|--------|----------|--------|
| series-a-daily | `monitor/series-a-daily` | Daily 7am ET | 88% GT hit rate |

## Graduating a Process to Monitor

When a validated research process (from `processes/`) needs scheduled execution:

1. Create its orphan branch following the pattern above
2. Copy relevant pipeline scripts into the monitor's `scripts/`
3. Configure `config/monitor.json` with schedule and sources
4. Deploy to TriggerDev via `/graduate-to-trigger`
5. Update `processes/[name]/STATUS.md` to `status: monitoring`
