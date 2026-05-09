# research-process-builder

Factory that produces validated web research processes via self-annealing loops. Takes a research goal, generates search patterns, tests against real companies, scores accuracy, and iterates until 90%+ reliability. Output: portable `.md` process files any agent (Claude, Clay/Claygent, GPT) can follow.

## What It Produces

Two things:

1. **Research process files** (`processes/find-*/process.md`) — step-by-step search instructions with exact queries, extract specs, stop-if conditions, and kill lists. 20+ processes built (find-profiles, find-competitors, find-funding, find-series-a-daily, etc.).

2. **Scheduled monitors** (`monitors/`) — validated processes promoted to daily pipeline runs. Currently: `series-a-daily` (88% GT hit rate, $0.01/run via SerperDev).

## Install

No package manager file exists. Deps are Python stdlib + external APIs. Install manually:

```bash
pip install openai supabase requests
```

Required env vars (in `.env` at repo root):

```
OPENAI_API_KEY=
SERPER_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
```

Domain classifier also reads `DOMAIN_CLASSIFIER_KEY` if present (optional, falls back to conservative rejection).

**Local script env loading:** Hook blocks direct `.env` reads from Claude. To test scripts that need API keys, write a `.py` file that loads via `dotenv` internally: `load_dotenv(Path(__file__).resolve().parents[2] / ".env")`. Parent `.env` is at `C:\Users\mitch\Everything_CC\.env`. Never reference `.env` in the shell command itself — the hook catches the string.

## Run the Series A Pipeline

```bash
# Full daily run (stages 1-4: discover → filter → enrich → output CSV+JSON)
py scripts/series_a_pipeline.py

# Weekly catch-up
py scripts/series_a_pipeline.py --tbs qdr:w

# Discovery only (stage 1)
py scripts/series_a_pipeline.py --stage 1

# Skip enrichment scraping
py scripts/series_a_pipeline.py --skip-enrich

# Dry-run (preview queries, no API calls)
py scripts/series_a_pipeline.py --dry-run

# Specific date
py scripts/series_a_pipeline.py --date 2026-04-20
```

Outputs land in `output/` as `series-a-YYYY-MM-DD.csv` + `.json`, and `output/series-a-master.csv`.

## Ground-Truth Validation

Continuous GT validation replaces the manual re-harvest cycle. Samples Supabase `funding_discoveries`, verifies each domain via the resolver agent, promotes confirmed pairs to `KNOWN_GOOD_DOMAINS`:

```bash
# Dry-run: sample 10 rows from last 14 days
py scripts/gt_validation.py --sample 10 --days 14

# Apply promotions to eval_pipeline.py
py scripts/gt_validation.py --sample 10 --days 14 --apply
```

State tracked in `data/gt_validation_state.json` — reruns skip already-processed pairs.

## Domain Resolver

Two-tier domain resolution used across all pipelines:

```bash
# Classify a domain
py scripts/domain_classifier.py --domain example.com

# Seed classifier cache from prior resolver runs
py scripts/domain_classifier.py --seed-from-resolver
```

**Key rule:** `real_company` verdict accepts. Anything else (`unknown`, API error, no key) rejects. Do not fix domain slip-throughs by appending to `BLOCKED_DOMAINS` — fix the classifier or seed its cache.

## Anneal a Prompt

Graduated prompts live in `prompts/[name]/`. To re-score the extraction prompt:

```bash
py prompts/extract-companies-batch/score.py --prompt prompts/extract-companies-batch/candidates/v004.json
```

Re-anneal trigger: score drops below 0.95 on live test set. Add new failure cases to `test_cases.json` first. Cost: ~$0.005, takes 5-10 min.

## Monitor Architecture

Monitors are **orphan git branches** mounted as worktrees — isolated history, independent versioning.

```bash
# Mount existing monitor (after cloning)
git worktree add monitors/series-a-daily monitor/series-a-daily

# Create new monitor
git checkout --orphan monitor/[name]
git rm -rf --cached .
# ... add config/, output/, runs/, scripts/
git add . && git commit -m "feat: initialize [name] monitor"
git checkout master
git worktree add monitors/[name] monitor/[name]
```

`monitors/` is gitignored on master. Each monitor has its own `config/monitor.json`, `runs/run-log.json`, and `output/YYYY-MM-DD/`.

## Building a New Research Process

Invoke the SKILL.md methodology (6 phases: define goal → generate 15-20 patterns → test across 3 company size tiers → score quality×consistency → iterate to 90%+ → assemble process file). Output goes to `processes/[name]/process.md`. Update `processes/[name]/STATUS.md` when done.

To graduate a validated process to a scheduled monitor, follow `MONITORS.md`.

## Key Conventions

- **`py` not `python`** throughout all scripts and docs (Windows default).
- **Single braces in GPT templates** — extraction prompt uses `.replace("{items}", payload)`, not f-strings. JSON examples inside the template need literal braces. Do not convert to f-string or `.format()`.
- **1-based local batch idx** in `extract_companies_batch` — model returns local idx, code maps `batch[local_idx-1]["idx"]` back to global. Keep this contract if re-annealing.
- **Supabase workspace 3 = production.** Always verify you're hitting the right table before any write.
- Ground truth files: `ground-truth/[company].json` — schema in `ground-truth/schema.json`. Baselines in `baselines/`.
