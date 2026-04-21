# Research Process Graduation System — Plan

**created:** 2026-04-21
**status:** plan only, not built yet
**goal:** any research process in `processes/` can graduate through defined levels into a live OpenAI Agent or TriggerDev workflow

## The Problem

We manually walked find-series-a-daily through: spec → test harness → validated queries → pipeline script → API integrations → deployment. That took a full session of bespoke work. Every process in `processes/` should be able to follow the same path with minimal custom code.

## Graduation Levels

```
L0: SPEC          processes/find-*.md — queries, inputs, outputs defined
     ↓
L1: TESTED        test harness validates queries against ground truth
     ↓
L2: PIPELINE      staged Python script (discover → filter → enrich → output)
     ↓
L3: GRADUATED     deployed as one of:
                   ├── L3a: OpenAI Agent (on-demand, conversational)
                   └── L3b: TriggerDev Task (scheduled, automated)
```

### L0: Spec (what we already have)

Every `processes/find-*.md` file is an L0 process. Contains:
- Search queries with SerperDev parameters
- Input/output schema
- Source tiering
- Known failure modes

**Exists for:** find-series-a-daily, find-funding, find-news, find-founders, find-competitors, find-top-competitors, ~15 more

**Graduation criteria → L1:** ground truth dataset exists (minimum 5 known-good results to validate against)

### L1: Tested

A test harness (`scripts/test_*.py`) that:
- Runs all queries from the L0 spec against SerperDev
- Scores results against ground truth
- Reports hit rate per query
- Identifies best/worst queries
- Outputs comparison report to `searches/`

**Template:** `scripts/test_news_discovery.py` is the reference implementation

**Graduation criteria → L2:** >70% GT hit rate on best query combination, cost per run calculated

### L2: Pipeline

A staged Python script (`scripts/*_pipeline.py`) with:
- Stage 1: Discovery (parallel SerperDev queries)
- Stage 2: Filter/Dedup (regex + heuristics, process-specific rules)
- Stage 3: Enrich (Spider Cloud scrape → GPT-4o-mini extract)
- Stage 4: Output (CSV + JSON + Supabase)

**Template:** `scripts/series_a_pipeline.py` is the reference implementation

**Key design:** stages 1-2 are process-specific (different queries, different filter rules). Stage 3-4 are generic (scrape + extract + store). The graduation system should only require custom code for stages 1-2.

**Graduation criteria → L3:** successful end-to-end run with real data, all API integrations working

### L3a: OpenAI Agent

For processes that make sense **on-demand** (user asks a question, agent runs the pipeline).

**Architecture:**
```
OpenAI Agent (gpt-4o-mini)
├── Tool: serper_search (SerperDev API)
├── Tool: spider_scrape (Spider Cloud API)
├── Tool: supabase_store (Supabase REST)
├── Instructions: from processes/find-*.md (the L0 spec)
└── Output: structured JSON matching the process schema
```

**When to use L3a vs L3b:**
- L3a (Agent): lookup processes — "find competitors for X", "find C-suite at Y", "who raised Series A this week?"
- L3b (TriggerDev): monitoring processes — "check every day for new Series A", "track competitor news daily"

**Good candidates for L3a:**
- find-founders (company-in → people-out)
- find-competitors (company-in → competitor list)
- find-c-suite (company-in → leadership list)
- find-funding (company-in → funding history)
- find-top-competitors (industry-in → ranked competitor list)

### L3b: TriggerDev Task

For processes that run **on a schedule** without human input.

**Architecture:**
```
TriggerDev Task (TypeScript wrapper)
├── Calls: py scripts/*_pipeline.py (or native TS reimplementation)
├── Schedule: cron expression from process spec
├── Storage: Supabase (upsert with dedup)
├── Notification: Telegram/Slack on completion
└── Error handling: retry 3x with backoff
```

**Good candidates for L3b:**
- find-series-a-daily (monitoring, daily cron)
- find-news (monitoring, could be daily per-client)
- find-growth-signals (monitoring, weekly per-client)
- find-pr-releases (monitoring, daily per-client)

## Shared Infrastructure

### Supabase Tables

Each graduated process gets its own table following a naming convention:

```
research_{process_name}
  - id (bigint, auto)
  - discovered_date (date)
  - ... process-specific columns from output schema
  - pipeline_version (text)
  - created_at (timestamptz)
  - unique constraint on natural key
```

### Shared Tools (for OpenAI Agents)

```
tools/
  agent_tools/
    serper_search.json      # OpenAI function schema for SerperDev
    spider_scrape.json      # OpenAI function schema for Spider Cloud
    supabase_store.json     # OpenAI function schema for Supabase upsert
```

These are reusable across all L3a agents. Each agent only differs in:
1. System prompt (from the L0 process spec)
2. Output schema (from the process output definition)

### Pipeline Base Class (for L2/L3b)

```python
# scripts/pipeline_base.py
class ResearchPipeline:
    """Base class for all graduated pipelines."""

    # Override in subclass
    QUERIES = []           # SerperDev query definitions
    FILTER_RULES = {}      # Process-specific filter config
    OUTPUT_SCHEMA = []     # Column names for CSV/Supabase
    SUPABASE_TABLE = ""    # Target table name

    def discover(self, tbs): ...      # Stage 1 — generic, uses self.QUERIES
    def filter(self, raw): ...        # Stage 2 — uses self.FILTER_RULES
    def enrich(self, scored): ...     # Stage 3 — generic (Spider + GPT)
    def output(self, enriched): ...   # Stage 4 — generic (CSV + Supabase)
    def run(self, tbs, **kwargs): ... # Full pipeline orchestration
```

A new pipeline only needs to define QUERIES, FILTER_RULES, OUTPUT_SCHEMA, and optionally override filter() for custom logic.

## Graduation Workflow

```
1. Pick a process from processes/find-*.md
2. Create ground truth dataset (5+ known-good results)
3. Run: py scripts/graduate.py test processes/find-X.md
   → generates test harness, runs against GT, reports hit rate
4. Run: py scripts/graduate.py pipeline processes/find-X.md
   → generates pipeline script from template + process spec
5. Run: py scripts/graduate.py deploy processes/find-X.md --target agent|triggerdev
   → generates OpenAI Agent config OR TriggerDev task definition
```

## Implementation Plan (next session)

### Phase 1: Pipeline Base Class
- Extract common logic from series_a_pipeline.py into pipeline_base.py
- Make series_a_pipeline.py inherit from base
- Verify it still works identically

### Phase 2: Graduation CLI
- `scripts/graduate.py` with subcommands: test, pipeline, deploy
- Template-based generation (Jinja2 or string formatting)
- Reads process spec to auto-generate query definitions and filter rules

### Phase 3: Agent Tool Definitions
- Create OpenAI function schemas for shared tools
- Build agent config generator from process spec
- Test with find-competitors or find-founders as first L3a agent

### Phase 4: TriggerDev Templates
- TypeScript task template that wraps Python pipeline
- Schedule configuration from process spec
- Notification integration (Telegram)

## Cost Model at Scale

| Graduated Processes | Daily Runs | Monthly Cost |
|---------------------|-----------|--------------|
| 1 (Series A only) | 1/day | ~$2 |
| 5 (+ competitors, news, funding, PR) | 5/day | ~$10 |
| 10 (+ per-client monitors) | 15/day | ~$25 |
| 20 (full coverage) | 30/day | ~$50 |

Still absurdly cheap. SerperDev is the bottleneck on free tier (2,500 queries/mo). At 20 queries/process × 30 runs/day = 600 queries/day → need paid tier ($50/mo for 30K queries).

## Decision: Agent vs TriggerDev

| Factor | OpenAI Agent (L3a) | TriggerDev (L3b) |
|--------|-------------------|-------------------|
| Trigger | User asks question | Cron schedule |
| Input | Dynamic (company name, industry, etc.) | Static (date-based) |
| Output | Conversational + structured | CSV/Supabase + notification |
| Cost per run | Higher (agent loop) | Lower (single script) |
| Best for | Lookup processes | Monitoring processes |
| Examples | find-founders, find-competitors | find-series-a-daily, find-news |

Some processes graduate to BOTH — find-funding could be:
- L3a: "What funding has Company X raised?" (on-demand lookup)
- L3b: "Track all new funding daily" (monitoring sweep)
