# Handoff — Structural Hardening + Continuous GT (2026-04-27)

**Session goal:** kill the band-aid surfaces flagged in the prior handoff and replace the manual GT re-harvest cycle with a runnable script. **Status:** all done. 4 commits on `master`, none pushed.

```
32c8dbc feat(stage2): wire graduated v004 prompt into extract_companies_batch
139c888 feat(prompts): graduate extract-companies-batch (gpt-4o-mini, 0.76 -> 1.00)
85e4220 feat(gt-validation): continuous Supabase -> verify-agent -> KNOWN_GOOD promotion
b07f638 fix(validate_domain): conservative gate — only real_company verdict accepts
```

---

## TL;DR for the dev

1. **Pull master, push when reviewed.** Nothing is on remote yet.
2. **Set up a recurring runner for `gt_validation.py`.** Weekly, with `--apply`, default sample 10. Route the conflict report somewhere visible (see "Open decision" below). This is the only thing left to make the new infra self-sustaining.
3. **Triage two open conflicts** the script already surfaced (Mosaic 3-way, Kajaani-vs-Iiwari). Stored values in Supabase need correcting.

Total session cost: ~$0.13 OpenAI + Serper.

---

## What changed (in order of structural importance)

### 1. `validate_domain` LOW branch is now classifier-gated (`b07f638`)

The runtime classifier was wired into `validate_domain` last session, but the LOW-confidence path still had a permissive fall-through: if the classifier returned anything other than `real_company` (incl. `unknown` / API error / no key), the code accepted the domain as `valid=True, confidence=low`. That fall-through was the actual cause of `BLOCKED_DOMAINS` accreting hand-curated entries — every band-aid was a manual override of a verdict the classifier shrugged on.

**New rule:** `real_company` accepts. Anything else rejects. Conservative by design — picks false-negatives over false-positives.

Three new test cases lock the contract (`scripts/test_resolver_unit.py::test_classifier_conservative_branch`). Use a deterministic cache seed so no API call.

**Knock-on effect:** future "this domain slipped through" bug reports should not be fixed by appending to `BLOCKED_DOMAINS`. They should be fixed by either (a) the classifier learning the correct category (which happens automatically on next run + cache hit) or (b) seeding the cache via `py scripts/domain_classifier.py --seed-from-resolver`.

### 2. `extract_companies_batch` now uses an annealed prompt (`139c888` + `32c8dbc`)

The Stage 2 single-pass GPT extractor's prompt was annealed against 32 hand-labeled cases from `output/stages/stage1-2026-04-26.json`. Score went from 0.76 baseline -> 1.00 graduated (mean 0.99 across reruns). Cost-per-batch ~2x baseline tokens but still $0.0012, trivial vs the +0.24 quality lift.

**Where the prompt lives now:** `prompts/extract-companies-batch/`
- `prompt.md` — human-readable graduated prompt
- `metadata.json` — model / scores / cost / token counts
- `candidates/v00{1..5}.json` — every attempted prompt (anneal log)
- `score.py` — re-runnable scorer; you can hit it any time:
  ```bash
  py prompts/extract-companies-batch/score.py --prompt prompts/extract-companies-batch/candidates/v004.json
  ```
- `test_cases.json` — the 32 hand-labeled GT cases (the contract)

**Where it's called from:** `scripts/pipeline_base.py` — top of file has `_EXTRACT_COMPANIES_BATCH_SYSTEM` and `_EXTRACT_COMPANIES_BATCH_USER_TEMPLATE` constants. The extractor method does `.replace("{items}", payload)` — single braces in the template are intentional (no f-string, no `.format()`), the JSON examples need them.

**Subtle contract change:** items are now formatted with **1-based local idx within each batch**, not the global idx. The model returns local idx; `extract_companies_batch` maps `batch[local_idx-1]["idx"]` back to the global key. This matches the scorer in `prompts/extract-companies-batch/score.py`. **If you re-anneal, keep this contract** — otherwise the scorer's score will not transfer to production.

**Re-anneal trigger:** if the score on the live test set drops below 0.95 over a couple production runs, or if a new failure class appears (you'd see it in `extraction-diff-*.json` in `output/`). Re-anneal cost is ~$0.005, takes 5-10 min via the `prompt-annealer` agent — it's not a heavy lift, just don't do it without first adding the new failure case(s) to `test_cases.json`.

### 3. Continuous GT validation (`85e4220`)

Replaces the "re-harvest every 2-3 weeks" TODO with a runnable script.

**What it does:**
1. Fetches recent rows from Supabase `funding_discoveries`
2. Filters out anything already in `KNOWN_GOOD_DOMAINS` or already in the local state file (`data/gt_validation_state.json`)
3. Samples N rows (default 10)
4. For each row: runs `resolve_domain_agent(company_name)` (the Tier 4 GPT agent + Serper, ~$0.02/call)
5. Three verdicts:
   - **confirmed** (agent matches stored, high/medium confidence) → eligible for promotion to `KNOWN_GOOD_DOMAINS`
   - **conflict** (agent disagrees with stored) → logged for human triage
   - **skipped** (agent returns not_found / low conf) → no signal, not promoted
6. With `--apply`, confirmed promotions get inserted between marker comments inside `KNOWN_GOOD_DOMAINS` in `eval_pipeline.py`. Idempotent — existing pairs are not re-added.

**Promotion markers** (don't remove these):
```python
KNOWN_GOOD_DOMAINS = [
    ...existing entries...
    {"company": "inploi", "domain": "inploi.com"},
    # === AUTO-PROMOTED BY gt_validation.py BEGIN ===
    # === AUTO-PROMOTED BY gt_validation.py END ===
]
```

**Usage:**
```bash
py scripts/gt_validation.py --sample 10 --days 14            # dry-run
py scripts/gt_validation.py --sample 10 --days 14 --apply    # write promotions
py scripts/gt_validation.py --show                           # state stats
py scripts/gt_validation.py --reset-conflicts                # re-verify only prior conflicts
```

**Cost:** ~$0.20 per 10-row run. Hard-cap via `--max-cost` (default $0.50).

**Live test today (2 rows):** filtered out 2 already-in-KNOWN_GOOD entries (VisioLab, Nox Mobility), then verified Kajaani + Mosaic. Both came back as conflicts (see "Open conflicts" below).

**Knock-on:** the classifier cache extends opportunistically. Today's run added `kitkagames.com → real_company` to `data/domain_classifications.json` for free. Both caches (KNOWN_GOOD + classifier) are committed to git → shared learning across machines / CI / your local box.

---

## Open conflicts to triage (manual, ~10 min)

These were surfaced by today's run, both look like real production data quality issues:

### Kajaani

- Stored in Supabase: `iiwari.com` (correct per `BAD_DOMAIN_CASES` — Kajaani is the city name, the company is Iiwari)
- Agent returned: `kitkagames.com`
- Verdict: agent confused company-vs-city. Stored value is correct. **No action needed in DB**, but consider whether the source row's `company_name` should be `Iiwari` not `Kajaani` to prevent future agent confusion.

### Mosaic

- Stored in Supabase: `mosaic.ai`
- Agent returned: `mosaic.pe`
- Existing KNOWN_GOOD entry: `mosaic.pe`
- This is the 3-way Mosaic problem flagged in the prior handoff (mosaic.pe / mosaic.ai / mosaicco.com are 3 different companies). Pick one canonical; if the Supabase row is actually a different Mosaic, leave stored as-is and add a disambiguation strategy. Probably needs a one-off Stage 1 source-URL inspection to know which company the article was actually about.

After resolving, you can re-trigger the check with:
```bash
py scripts/gt_validation.py --reset-conflicts
```

---

## Open decision: where does the recurring conflict report go?

The script is built for recurring use but I did NOT set up a runner. Three options, your call:

| Option | Setup | Pros | Cons |
|---|---|---|---|
| **A. Markdown log file** | Add `--log-md` flag that appends conflicts to `output/gt-validation-log.md` | Zero infra, lives in git, you'll see it in `git status` | Easy to ignore |
| **B. Telegram ping** | The Telegram MCP has a `reply` tool (Mitch's bot is wired) | Push notification when conflicts > 0; ignored on quiet weeks | Needs the MCP/CLI to be reachable from cron context |
| **C. stdout only** | Wrap in PowerShell scheduled task; output goes to a log dir | Simplest | Only seen if Mitch grep's the log — i.e. never |

Mitch's hint was "hand off to dev" — pick what fits your runner. My recommendation: **A + run weekly via PowerShell scheduled task**. The `--apply` does the auto-promotions silently; the markdown log surfaces just the conflicts that need triage. If conflicts pile up, the log grows → impossible to miss next time it's opened.

Sample wrapper:
```powershell
# weekly-gt-validation.ps1
cd C:\Users\mitch\Everything_CC\research-process-builder
py scripts/gt_validation.py --sample 10 --days 14 --apply --log-md > output\gt-validation-stdout.log 2>&1
```

(Implementing `--log-md` is a 10-line addition — not done; you decide whether you want it before adding.)

---

## What's still on the band-aid list

From prior handoff, still untouched (lower priority but they're the next layer):

1. **`_is_bad_extraction` hardcoded phrase list** in `series_a_pipeline.py` — same band-aid pattern as old BLOCKED_DOMAINS but for extracted name strings. Could be replaced with a small GPT classifier on (candidate name, article context) → valid/invalid.

2. **`_clean_extracted_name` prefix/possessive strip rules** — the Stage 2 anneal mostly handled this via the prompt (possessive examples in v004), so this band-aid is mostly defanged. Audit whether the rules still earn their keep, or delete.

3. **`FUNDING_VERBS` regex list in `series_a_pipeline.py`** — Stage 2 GPT extractor reads natural language now, so this regex is only used in Stage 1 keyword scoring. Either keep for cheap pre-filter (current state) or delete and let GPT do all the work.

4. **`tracxn.com` source filter** — Stage 3 scrape on Tracxn returns garbage. Should filter Tracxn URLs at Stage 1 instead of post-extraction. ~5 min change.

5. **WhoaZone Equine / Facebook URL filter** — agent resolved a Facebook page as `wzequine.com`. Probably tighten Facebook URL filtering at Stage 1 to drop the source entirely.

---

## How to verify everything works on your box

```bash
# Unit tests (no API)
py scripts/test_resolver_unit.py
py scripts/test_name_extraction.py

# Eval (offline — no API)
py scripts/eval_pipeline.py --offline

# Full eval (live — ~$0.04, hits Serper)
py scripts/eval_pipeline.py

# Anneal scorer on graduated prompt (~$0.001)
py prompts/extract-companies-batch/score.py --prompt prompts/extract-companies-batch/candidates/v004.json

# GT validation dry-run (~$0.20 if there are fresh rows)
py scripts/gt_validation.py --sample 10 --days 14
```

If `eval_pipeline.py` doesn't show 100% domain accuracy, something regressed. The most likely break point is the LOW branch test if `OPENAI_API_KEY` isn't loaded (the test mocks the cache so it shouldn't matter, but check).

---

## Files you should read first

| File | Why |
|---|---|
| `scripts/domain_resolver.py` lines 164-225 | The new conservative `validate_domain` LOW branch |
| `scripts/domain_classifier.py` | The runtime classifier (entire file, ~250 lines) |
| `scripts/gt_validation.py` | The new validation pipeline |
| `prompts/extract-companies-batch/prompt.md` | The graduated extraction prompt |
| `scripts/pipeline_base.py` lines 70-130 + the `extract_companies_batch` method | The wiring contract |

Skip for now unless touching:
- `scripts/series_a_pipeline.py` — subclass with funding-specific logic, mostly unchanged this session
- `scripts/anneal.py` — different anneal (Serper search patterns), not LLM prompts
- `prompts/extract-companies-batch/score.py` and `iter.py` — annealer's harness, don't run by hand unless re-annealing

---

## Contact

Catch-up on history: read the prior handoff `HANDOFF-domain-resolver-anneal.md` (still accurate as the "before" state). The "Band-aid vs Structural Audit" section there explains the design philosophy — this session crossed off rows 1, 2, and 4 of the band-aid table.
