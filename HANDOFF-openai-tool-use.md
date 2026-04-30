# Handoff: OpenAI Tool Use for Autoresearch Loop

## Goal

Run the autoresearch optimization loop on OpenAI models with Serper + Spider as callable tools. Currently the loop is driven by Claude Code (agent reads `research_prompt.md`, mutates `master_test_config.json`, runs `pattern_tester.py`). This handoff specs moving the loop to OpenAI's tool-calling API so it runs autonomously, cheaper, and faster.

## Why OpenAI

- Cheaper per-iteration than Claude Code sessions for a tight mutation loop
- Native tool use = the model calls Serper/Spider directly instead of shelling out to Python scripts
- Faster iteration cycles (API calls vs interactive CLI)
- Can run unattended (cron, scheduled agent, CI)

## What Exists

| Component | Path | Status |
|---|---|---|
| Serper search wrapper | `leadgrow-hq/tools/shared-scripts/serper_search.py` | Working. `search(query, news, tbs)` returns Serper JSON |
| Spider scrape wrapper | `leadgrow-hq/tools/spider/scrape.py` | Working. `scrape_url(url, return_format, readability)` returns markdown |
| Spider config | `leadgrow-hq/tools/spider/_config.py` | Working. API key, defaults, premium proxy config |
| OpenRouter tool-calling agent | `leadgrow-hq/tools/shared-scripts/call_llm_openrouter.py` | Working. Already has Serper + Spider as tools via OpenAI SDK against OpenRouter. Self-annealing protected sites. |
| Pattern tester | `research-process-builder/scripts/pattern_tester.py` | Working. Tests query templates against 25 companies via Serper |
| GT evaluator | `research-process-builder/scripts/gt_evaluator.py` | Working. Scores results against ground truth JSON files |
| Baseline manager | `research-process-builder/scripts/autoresearch.py` | Working. Save/compare/history for GT baselines |
| Domain briefing | `research-process-builder/domain-briefing.md` | NEW. Platform-specific approaches, dead ends, benchmark targets |
| Warm-start config | `research-process-builder/best_config.json` | NEW. Best variants, dead ends, untested approaches, cost limits |
| Deploy skill | `.claude/skills/auto-research-deploy/SKILL.md` | NEW. Pre-flight + steering companion |

## Architecture

```
┌─────────────────────────────────────┐
│  OpenAI Tool-Calling Agent          │
│  (gpt-4o or gpt-4.1)               │
│                                     │
│  System prompt: research_prompt.md  │
│  + domain-briefing.md               │
│  + best_config.json                 │
│                                     │
│  Loop:                              │
│    1. Read current GT scores        │
│    2. Pick worst category           │
│    3. Propose new query variant     │
│    4. Call serper_search tool        │
│    5. Score result vs ground truth   │
│    6. Keep or revert                │
│    7. Repeat until budget exhausted  │
└──────────┬──────────┬───────────────┘
           │          │
     ┌─────▼──┐  ┌────▼────┐
     │ Serper │  │ Spider  │
     │ Search │  │ Scrape  │
     └────────┘  └─────────┘
```

## Two Tools to Register

### 1. `serper_search`

```json
{
  "type": "function",
  "function": {
    "name": "serper_search",
    "description": "Search Google via Serper.dev API. Returns SERP results with titles, snippets, links. Use for testing query patterns against real search results.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Google search query. Supports operators: site:, intitle:, OR, quotes for exact match, -exclusion"
        },
        "news": {
          "type": "boolean",
          "description": "Search news instead of web. Default false.",
          "default": false
        },
        "tbs": {
          "type": "string",
          "description": "Time filter. qdr:d (day), qdr:w (week), qdr:m (month), qdr:y (year). Optional."
        }
      },
      "required": ["query"]
    }
  }
}
```

**Implementation:** Call `serper_search.search(query, news, tbs)` from `leadgrow-hq/tools/shared-scripts/serper_search.py`. Returns full Serper JSON (organic results, knowledge graph, related searches).

**Cost:** ~$0.001/query. Budget cap in `best_config.json`: 75 queries/iteration, $0.25/session.

### 2. `spider_scrape`

```json
{
  "type": "function",
  "function": {
    "name": "spider_scrape",
    "description": "Scrape a web page and return its content as markdown. Use when SERP snippets don't contain the data and you need to visit the actual page. Good for: tech stack pages, integration directories, customer lists, team/about pages.",
    "parameters": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "Full URL to scrape"
        },
        "root_selector": {
          "type": "string",
          "description": "CSS selector to scope extraction. Optional. E.g. 'article', '.team-section', '#integrations'"
        }
      },
      "required": ["url"]
    }
  }
}
```

**Implementation:** Call `scrape_url(url, return_format='markdown', readability=True, root_selector=root_selector)` from `leadgrow-hq/tools/spider/scrape.py`. Returns markdown content.

**Cost:** ~$0.001-0.002/scrape (standard), ~$0.005 (premium/JS-rendered). Budget: 20 scrapes/iteration max.

**When to use Spider vs Serper:**
- Serper: test if a query pattern surfaces the right data in SERP snippets (titles + 155-char snippets)
- Spider: visit the actual page when snippets are insufficient. Three SERP-capped categories confirmed: `tech_stack`, `partnerships_integrations`, `customer_case_studies`

## System Prompt Structure

The agent's system prompt is assembled from existing files:

```
1. research_prompt.md          — loop protocol, rules, mutation strategies
2. domain-briefing.md          — platform-specific approaches, dead ends
3. best_config.json            — warm-start (best variants, cost limits)
4. Current GT scores           — output of `py scripts/validate.py --score`
5. master_test_config.json     — current variant config (the thing being mutated)
```

Static context (1-3) loads first for cache efficiency. Dynamic context (4-5) appends.

## What the Agent Does Per Iteration

1. **Read GT scores** — identify 3 worst categories
2. **Read best_config.json** — check dead ends, promising untested
3. **Propose 1-3 new variants** — informed by domain-briefing + warm-start
4. **Test each variant** — call `serper_search` with template expanded for 5 companies (1 per tier)
5. **Quick gate** — if GT < 0.15 on 5-company sample, prune immediately
6. **Full test** — if GT > 0.25 on sample, expand to all 25 companies
7. **Score** — compare snippet content against ground truth
8. **For SERP-capped categories** — call `spider_scrape` on top URLs to extract data from page body
9. **Decide** — keep variant if GT improved, revert otherwise (unless exploration mode)
10. **Update best_config.json** — record new best variants, add dead ends
11. **Save baseline** — `py scripts/autoresearch.py --save-baseline iter-N`

## Key Constraints

- **75 queries/iteration, $0.25/session hard cap** (from `best_config.json`)
- **20 Spider scrapes/iteration max** (Spider is 2-5x Serper cost)
- **Never modify `gt_evaluator.py`, `validate.py`, or ground truth files**
- **Only mutate `master_test_config.json`**
- **Exploration mode after 3 consecutive no-improvement** (accept 5% worse if different result set)

## Env Vars Required

```
OPENAI_API_KEY=        # or OPENROUTER_API_KEY for OpenRouter
SERPER_API_KEY=        # Serper.dev
SPIDER_API_KEY=        # Spider Cloud
```

All already in `C:\Users\mitch\Everything_CC\.env`.

## Implementation Path

### Option A: Extend `call_llm_openrouter.py` (fastest)

Already has Serper + Spider tools wired. Add:
- System prompt assembly from research_prompt.md + domain-briefing.md + best_config.json
- GT scoring inline (port `gt_evaluator.py` logic or shell out)
- Baseline save after each improvement
- Cost tracking + budget enforcement

### Option B: New standalone script `autoresearch_agent.py`

Cleaner separation. Lives in `research-process-builder/scripts/`. Uses OpenAI SDK directly (not OpenRouter). Two registered tools. Reads all config from RPB directory. Outputs to RPB baselines/searches.

**Recommendation: Option B.** `call_llm_openrouter.py` is a general-purpose agent. The autoresearch loop has specific state management (baselines, warm-start, exploration budget) that would bloat the general tool.

### Skeleton

```python
# research-process-builder/scripts/autoresearch_agent.py

from openai import OpenAI
import json

client = OpenAI()  # or OpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)

tools = [SERPER_TOOL_SCHEMA, SPIDER_TOOL_SCHEMA]

system_prompt = assemble_prompt()  # research_prompt.md + domain-briefing + best_config + GT scores

messages = [{"role": "system", "content": system_prompt}]

for iteration in range(max_iterations):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    # Handle tool calls
    for tool_call in response.choices[0].message.tool_calls or []:
        if tool_call.function.name == "serper_search":
            result = serper_search.search(**json.loads(tool_call.function.arguments))
        elif tool_call.function.name == "spider_scrape":
            result = scrape_url(**json.loads(tool_call.function.arguments))

        messages.append(tool_call_result_message(tool_call.id, result))

    # Check budget
    if query_count >= 75 or cost >= 0.25:
        break
```

## What NOT to Build

- No custom eval framework — `gt_evaluator.py` already works, shell out to it
- No custom baseline system — `autoresearch.py --save-baseline` already works
- No web UI — terminal output + baselines JSON is the interface
- No parallel agents yet — Phase 5 gate from deploy skill not met

## Success Criteria

- Agent runs 10 iterations autonomously
- At least 1 category GT improves >0.05
- Cost stays under $0.25/session
- Spider successfully extracts data for 1+ SERP-capped category
- best_config.json updated with findings
