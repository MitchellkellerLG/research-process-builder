# Handoff: Domain Resolver Annealing

**Status:** Foundation shipped, ready for annealing
**Date:** 2026-04-26
**Budget:** $8 (API costs: Serper $0.0075/search, GPT-4o-mini $0.002/call, Spider $0.001/scrape)
**Goal:** Push domain resolution accuracy from 97% to 99%+ on expanding ground truth

## What Exists

### New module: `scripts/domain_resolver.py`
- 3-tier waterfall: article regex → GPT extract → Serper search
- `validate_domain()` gate with 70+ blocked domains across 6 categories
- `resolve_domain_agent()` — GPT agent with tool-calling (higher accuracy, ~$0.02/call)
- `fuzzy_dedup_companies()` — token-overlap + Levenshtein + domain-based merge
- Score threshold (≥3) prevents low-confidence domains from leaking

### Wired into pipeline
- `pipeline_base.py` — validation gate on GPT-extracted domains, waterfall fallback, post-enrichment dedup
- `series_a_pipeline.py` — fuzzy dedup in Stage 2, hardened extraction prompt, Supabase field fix

### Test infrastructure
- `eval_pipeline.py` — 39 test cases, 97% accuracy, exits non-zero on regression
- `test_resolver_unit.py` — 27 unit tests for validate_domain, names_are_similar, fuzzy_dedup
- Backfill ground truth: 19 corrections (backfill-committed-20260425) + 16 agent tests (domain-agent-20260425)

### Production state
- 95 rows in Supabase `funding_discoveries`
- 17 bad domains fixed in latest backfill run (0 failures)
- 74 OK, 4 unchanged (correct name-mismatch), 0 blocked, 0 missing

## What Needs Annealing

### 1. Expand ground truth (most important)
Current: 35 companies. Need: 80+.

**How:**
- Run pipeline on 5 historical dates: `py scripts/series_a_pipeline.py --tbs qdr:w --date 2026-04-20 --skip-enrich`
- Take the Stage 2 output, manually verify company names
- Run domain resolver on each, compare to Crunchbase/manual lookup
- Add to `eval_pipeline.py` KNOWN_GOOD_DOMAINS and BAD_DOMAIN_CASES

**Budget:** ~$0.50 (50 searches for 5 days × 10 queries)

### 2. Reduce not_found rate
Current pipeline returns `not_found` when all 3 tiers fail. The agent fallback (Tier 4) catches most of these but costs ~$0.02/company.

**Anneal approach:**
- Run `py scripts/series_a_pipeline.py --tbs qdr:w --date 2026-04-21 --domain-agent` (weekly catchup with agent fallback)
- Compare waterfall-only vs agent results
- For each case where agent succeeds but waterfall fails, analyze WHY:
  - Was it a search query construction issue? → improve `_find_domain_serper()` query templates
  - Was it a blocked domain that shouldn't be blocked? → trim block list
  - Was it a regex miss in article text? → add pattern to DOMAIN_PATTERNS
  - Was it an obscure company that needs Crunchbase snippet mining? → boost Crunchbase search weight
- Patch the waterfall, re-run eval, confirm no regression

**Budget:** ~$3.00 (agent calls on ~50 companies + search iterations)

### 3. Tighten name extraction (Stage 2) — DONE 2026-04-26

**Shipped:**
- `FUNDING_VERBS` regex expanded — added `eyes`, `scores`, `pockets`, `wraps up`, `picks up`, `pulls in`, `hauls in`, `snags`, `grabs`, `locks in`, `banks`. Catches headlines like "Lumio eyes Series A" that previously got filtered.
- `_clean_extracted_name()` — strips article-style prefixes (`AI Startup`, `Fintech Startup`, `Identity Authentication Startup`, etc.). "Identity Authentication Startup Auth0 Raises…" → `Auth0`.
- `_is_bad_extraction()` — heuristic filter for column headers, post slugs, generic phrases. Catches: colons in name, `'s Post`, `'s Newsletter`, `Deal Closing`, `Fund Managers`, `Weekly News`, mostly-lowercase fragments.
- Fallback path also runs cleaning + bad-extraction filter.
- Bad rows now get filtered_out reason (`extracted name flagged as bad pattern`) instead of leaking to Stage 3 enrichment.
- `test_name_extraction.py` — 18 tests (all pass): verb expansion, prefix strip, bad-pattern reject.

**Validated against 2026-04-26 stage2:** 5 bad extractions identified pre-fix would now be filtered (TechCrunch Mobility column header, AI Market Watch's Post, Latest tech trends, Warehoused Deal Closing, Identity Authentication Startup Auth0 stripped to Auth0). 4 false-negatives ("Lumio eyes…", "GobbleCube snags…") would now extract correctly.

### 4. Cross-day dedup (Supabase level) — DONE 2026-04-26

**Shipped:**
- `match_existing_company()` in `domain_resolver.py` — domain-exact + fuzzy-name match (with www-prefix normalization)
- `fetch_recent_companies(days=30)` in `pipeline_base.py` — single GET to load recent rows once per push
- `push_to_supabase()` rewritten — PATCHes existing row (bumps source_count, max score, fills missing domain) instead of duplicate insert
- Within-batch + cross-day dedup combined in one Stage 4 pass
- 8 new unit tests in `test_resolver_unit.py` (all pass)
- Bonus: `names_are_similar` extended with prefix-token match — "Strider Tech" ↔ "Strider Technologies" now merges (min-len-4 guard prevents `ai`/`io` false positives)

**Verify on next live run:**
- Run pipeline on 3 consecutive days, confirm no duplicate company rows in DB
- Watch for `Cross-day merged: N` log line — proof it's firing
- Spot-check a merged row: source_count should reflect cumulative cross-day appearances

### 5. Block list expansion from production data — DONE 2026-04-26 (offline pass)

**Shipped:**
- Audited 7 backfill JSONs in `output/`. Found 7 candidate bad-domain patterns.
- Added to NEWS_DOMAINS: `ai-market-watch.com`, `oled-info.com` (industry newsletters/aggregators)
- New `LEGAL_SERVICES_DOMAINS` category added (law firms appearing in funding press as advisors): `gunder.com`, `wsgr.com`, `cooley.com`, `fenwick.com`, `lw.com`, `sidley.com`, `orrick.com`, `dlapiper.com`, `morganlewis.com`, `skadden.com`, `kirkland.com`, `morrisonforester.com`, `mofo.com`. Pre-loaded common funding-counsel domains beyond what backfill surfaced.
- `anu.edu.au` already caught by EDU_PATTERN — no change needed.
- 4 new test cases in `test_resolver_unit.py` (all pass).

**Eval impact: 38/39 (97%) → 39/39 (100%).** gunder.com was the failing case.

**Next pass:** re-run audit weekly against new backfill JSONs, append new bad domains.

### 6. Prompt annealing for GPT extraction
The extraction prompt in `series_a_pipeline.py:get_extraction_prompt()` can be formally annealed using the anneal loop system.

**Anneal approach:**
- Build test cases: 20 articles with known-correct extraction (company, domain, amount, investors)
- Run through `/anneal-prompt` targeting gpt-4o-mini
- Graduate when 95%+ accuracy
- Replace current prompt with graduated version

**Budget:** ~$2.50 (anneal loop runs ~10 iterations × ~$0.25 each)

## Commands

```bash
# Set env
$env:SHARED_SCRIPTS_PATH = "C:\Users\mitch\Everything_CC\leadgrow-hq\tools\shared-scripts"
cd C:\Users\mitch\Everything_CC\research-process-builder\scripts

# Run eval (no API cost)
py eval_pipeline.py --offline

# Run eval with live domain resolution (~$0.03)
py eval_pipeline.py

# Run unit tests
py test_resolver_unit.py

# Run pipeline (daily)
py series_a_pipeline.py --tbs qdr:d

# Run pipeline (weekly catchup, with agent fallback)
py series_a_pipeline.py --tbs qdr:w --domain-agent

# Run backfill audit (read-only)
py backfill_domains.py

# Run backfill fix (dry run)
py backfill_domains.py --fix

# Run backfill fix (commit to DB)
py backfill_domains.py --fix --commit
```

## Success Criteria

- eval_pipeline.py passes at 99%+ (currently 100% as of 2026-04-26)
- Ground truth expanded to 80+ companies
- not_found rate < 10% on weekly pipeline runs
- Zero wrong domains on any run
- Cross-day dedup prevents Supabase duplicates
- Extraction prompt graduated through anneal loop

## Budget Breakdown

| Task | Est. Cost |
|------|-----------|
| Expand ground truth | $0.50 |
| Reduce not_found (agent comparison) | $3.00 |
| ~~Name extraction tightening~~ DONE | $0 (offline) |
| ~~Cross-day dedup testing~~ DONE | $0 (offline) |
| ~~Block list expansion~~ DONE | $0 (offline) |
| Prompt annealing | $2.50 |
| **Total** | **$7.50** |

## Key Files

| File | Purpose |
|------|---------|
| `scripts/domain_resolver.py` | Unified domain resolution module (THE source of truth) |
| `scripts/pipeline_base.py` | Base pipeline class (Stage 3 enrichment, Stage 4 output) |
| `scripts/series_a_pipeline.py` | Series A subclass (queries, filters, extraction prompt) |
| `scripts/eval_pipeline.py` | Eval harness (must pass before any change ships) |
| `scripts/test_resolver_unit.py` | Unit tests |
| `scripts/backfill_domains.py` | Supabase domain backfill agent |
| `output/backfill-committed-*.json` | Backfill change logs (ground truth source) |
| `output/domain-agent-*.json` | Agent test results (ground truth source) |

## Rules

1. Run `py eval_pipeline.py --offline` after EVERY change. Must stay ≥ 97%.
2. Run `py test_resolver_unit.py` after any change to domain_resolver.py.
3. Never remove a domain from BLOCKED_DOMAINS without evidence it caused a false positive.
4. Add new ground truth cases for every failure you fix.
5. Commit after each successful annealing iteration with clear message.
