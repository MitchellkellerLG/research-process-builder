"""
Autoresearch Agent — OpenAI tool-calling loop for search pattern optimization.

Standalone agent that runs the Karpathy-style optimization loop autonomously.
Uses OpenAI SDK with two registered tools (serper_search, spider_scrape).
Reads all config from RPB directory. Shells out to existing scripts for
testing, scoring, and baseline management.

Usage:
    py scripts/autoresearch_agent.py                    # run with defaults
    py scripts/autoresearch_agent.py --max-iterations 5 # limit iterations
    py scripts/autoresearch_agent.py --model gpt-4.1    # model override
    py scripts/autoresearch_agent.py --dry-run           # no API calls, print plan
    py scripts/autoresearch_agent.py --budget 0.50       # raise budget cap
"""

import json
import sys
import os
import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_FILE = PROJECT_DIR.parent / ".env"

load_dotenv(ENV_FILE)

# Add shared-scripts to path for serper + spider imports
SHARED_SCRIPTS = PROJECT_DIR.parent / "leadgrow-hq" / "tools" / "shared-scripts"
SPIDER_DIR = PROJECT_DIR.parent / "leadgrow-hq" / "tools" / "spider"
sys.path.insert(0, str(SHARED_SCRIPTS))
sys.path.insert(0, str(SPIDER_DIR))

import serper_search
from scrape import scrape_url

# ── Tool schemas ─────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "serper_search",
            "description": (
                "Search Google via Serper.dev API. Returns SERP results with titles, "
                "snippets, links. Use for testing query patterns against real search results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Google search query. Supports operators: site:, intitle:, OR, quotes, -exclusion",
                    },
                    "news": {
                        "type": "boolean",
                        "description": "Search news instead of web. Default false.",
                        "default": False,
                    },
                    "tbs": {
                        "type": "string",
                        "description": "Time filter. qdr:d (day), qdr:w (week), qdr:m (month), qdr:y (year). Optional.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spider_scrape",
            "description": (
                "Scrape a web page and return content as markdown. Use when SERP snippets "
                "don't contain the data and you need to visit the actual page. Good for: "
                "tech stack pages, integration directories, customer lists, team/about pages."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to scrape",
                    },
                    "root_selector": {
                        "type": "string",
                        "description": "CSS selector to scope extraction. Optional. E.g. 'article', '.team-section'",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_pattern_test",
            "description": (
                "Run pattern_tester.py against real companies via Serper. Tests all variants "
                "in a category (or all categories) and stores results. Costs Serper credits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category ID to test (e.g. 'tech_stack'). Omit for all categories.",
                    },
                    "company": {
                        "type": "string",
                        "description": "Single company name to test. Omit for all companies.",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview queries without making API calls.",
                        "default": False,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_gt_evaluation",
            "description": (
                "Run GT evaluation (gt_evaluator.py --json) to score current search results "
                "against ground truth. Returns per-company, per-category, per-variant scores. "
                "No API cost — purely local computation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category to evaluate. Omit for all.",
                    },
                    "company": {
                        "type": "string",
                        "description": "Company to evaluate. Omit for all.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_validate_score",
            "description": (
                "Run validate.py --score to get the full GT accuracy report. "
                "Shows per-category GT averages and overall mean. No API cost."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_baseline",
            "description": "Save current GT scores as a named baseline snapshot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Baseline name (e.g. 'iter-3'). Auto-generated if omitted.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_baseline",
            "description": "Compare current GT scores against a saved baseline. Shows improvements and regressions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Baseline name to compare against. Uses most recent if omitted.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_master_config",
            "description": "Read the current master_test_config.json (the thing you mutate).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_master_config",
            "description": (
                "Write updated master_test_config.json. Use this to add/remove/modify "
                "query variants. Pass the FULL config JSON."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "config_json": {
                        "type": "string",
                        "description": "Full JSON string of the updated master_test_config.json",
                    },
                },
                "required": ["config_json"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_best_config",
            "description": (
                "Update best_config.json with new findings. Pass the FULL config JSON."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "config_json": {
                        "type": "string",
                        "description": "Full JSON string of the updated best_config.json",
                    },
                },
                "required": ["config_json"],
            },
        },
    },
]


# ── Tool implementations ─────────────────────────────────────────────────────

class ToolTracker:
    def __init__(self, budget: float, max_queries: int, max_scrapes: int):
        self.budget = budget
        self.max_queries = max_queries
        self.max_scrapes = max_scrapes
        self.query_count = 0
        self.scrape_count = 0
        self.cost = 0.0

    def can_query(self) -> bool:
        return self.query_count < self.max_queries and self.cost < self.budget

    def can_scrape(self) -> bool:
        return self.scrape_count < self.max_scrapes and self.cost < self.budget

    def record_query(self):
        self.query_count += 1
        self.cost += 0.001

    def record_scrape(self):
        self.scrape_count += 1
        self.cost += 0.003

    def summary(self) -> str:
        return (
            f"Queries: {self.query_count}/{self.max_queries} | "
            f"Scrapes: {self.scrape_count}/{self.max_scrapes} | "
            f"Cost: ${self.cost:.3f}/${self.budget:.2f}"
        )


def run_shell(cmd: list[str], cwd: str = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or str(PROJECT_DIR),
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        return output[:15000]
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timed out after 120s"
    except Exception as e:
        return f"[ERROR] {e}"


def handle_tool_call(name: str, args: dict, tracker: ToolTracker) -> str:
    if name == "serper_search":
        if not tracker.can_query():
            return json.dumps({"error": f"Query budget exhausted. {tracker.summary()}"})
        tracker.record_query()
        try:
            result = serper_search.search(
                query=args["query"],
                news=args.get("news", False),
                tbs=args.get("tbs"),
            )
            organic = result.get("organic", [])[:5]
            trimmed = {
                "organic": [
                    {"title": r.get("title", ""), "snippet": r.get("snippet", ""), "link": r.get("link", "")}
                    for r in organic
                ],
                "knowledgeGraph": result.get("knowledgeGraph", {}),
            }
            return json.dumps(trimmed, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    elif name == "spider_scrape":
        if not tracker.can_scrape():
            return json.dumps({"error": f"Scrape budget exhausted. {tracker.summary()}"})
        tracker.record_scrape()
        try:
            result = scrape_url(
                url=args["url"],
                return_format="markdown",
                readability=True,
                root_selector=args.get("root_selector"),
            )
            if isinstance(result, list) and result:
                content = result[0].get("content", "")[:5000]
            elif isinstance(result, dict):
                content = result.get("content", str(result))[:5000]
            else:
                content = str(result)[:5000]
            return json.dumps({"content": content}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    elif name == "run_pattern_test":
        cmd = ["py", "scripts/pattern_tester.py"]
        if args.get("category"):
            cmd += ["--category", args["category"]]
        if args.get("company"):
            cmd += ["--company", args["company"]]
        if args.get("dry_run"):
            cmd.append("--dry-run")
        return run_shell(cmd)

    elif name == "run_gt_evaluation":
        cmd = ["py", "scripts/gt_evaluator.py", "--json"]
        if args.get("category"):
            cmd += ["--category", args["category"]]
        if args.get("company"):
            cmd += ["--company", args["company"]]
        output = run_shell(cmd)
        try:
            evals = json.loads(output.split("\n[stderr]")[0])
            from collections import defaultdict
            by_cat = defaultdict(list)
            for e in evals:
                by_cat[e["category_id"]].append(e["gt_score"])
            summary = {cat: {"avg": round(sum(s)/len(s), 3), "n": len(s)} for cat, s in by_cat.items()}
            return json.dumps({"per_category": summary, "total_evals": len(evals)}, indent=2)
        except Exception:
            return output

    elif name == "run_validate_score":
        return run_shell(["py", "scripts/validate.py", "--score"])

    elif name == "save_baseline":
        cmd = ["py", "scripts/autoresearch.py", "--save-baseline"]
        if args.get("name"):
            cmd.append(args["name"])
        return run_shell(cmd)

    elif name == "compare_baseline":
        cmd = ["py", "scripts/autoresearch.py", "--compare"]
        if args.get("name"):
            cmd.append(args["name"])
        return run_shell(cmd)

    elif name == "read_master_config":
        config_path = SCRIPT_DIR / "master_test_config.json"
        return config_path.read_text(encoding="utf-8")

    elif name == "write_master_config":
        config_path = SCRIPT_DIR / "master_test_config.json"
        try:
            parsed = json.loads(args["config_json"])
            config_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
            return json.dumps({"status": "ok", "categories": len(parsed.get("categories", []))})
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {e}"})

    elif name == "update_best_config":
        config_path = PROJECT_DIR / "best_config.json"
        try:
            parsed = json.loads(args["config_json"])
            config_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
            return json.dumps({"status": "ok"})
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {e}"})

    return json.dumps({"error": f"Unknown tool: {name}"})


# ── System prompt assembly ───────────────────────────────────────────────────

def assemble_system_prompt() -> str:
    parts = []

    # 1. Research prompt (loop protocol)
    research_prompt = PROJECT_DIR / "research_prompt.md"
    if research_prompt.exists():
        parts.append(research_prompt.read_text(encoding="utf-8"))

    # 2. Domain briefing
    domain_briefing = PROJECT_DIR / "domain-briefing.md"
    if domain_briefing.exists():
        parts.append("\n---\n# DOMAIN BRIEFING\n" + domain_briefing.read_text(encoding="utf-8"))

    # 3. Best config (warm-start)
    best_config = PROJECT_DIR / "best_config.json"
    if best_config.exists():
        parts.append("\n---\n# WARM-START CONFIG (best_config.json)\n```json\n" +
                     best_config.read_text(encoding="utf-8") + "\n```")

    # 4. Current GT scores
    try:
        gt_output = subprocess.run(
            ["py", "scripts/validate.py", "--score"],
            capture_output=True, text=True, cwd=str(PROJECT_DIR),
            timeout=30, encoding="utf-8", errors="replace",
        )
        if gt_output.stdout:
            parts.append("\n---\n# CURRENT GT SCORES\n```\n" + gt_output.stdout[:5000] + "\n```")
    except Exception:
        parts.append("\n---\n# CURRENT GT SCORES\n[Could not load — run validate.py manually]")

    # Agent-specific instructions
    parts.append("""
---
# AGENT INSTRUCTIONS

You are the autoresearch optimization agent. Your job is to improve GT scores by
mutating query variants in master_test_config.json.

## Available tools

- `serper_search` — test a single query against Google (costs ~$0.001)
- `spider_scrape` — scrape a page for data SERP can't reach (costs ~$0.003)
- `run_pattern_test` — run pattern_tester.py on a category or company (costs Serper credits)
- `run_gt_evaluation` — score results against ground truth (free)
- `run_validate_score` — full GT accuracy report (free)
- `save_baseline` — snapshot current GT scores
- `compare_baseline` — diff current vs saved baseline
- `read_master_config` — read current config
- `write_master_config` — write updated config (full JSON)
- `update_best_config` — update warm-start config (full JSON)

## Loop protocol

1. Save baseline before mutating
2. Identify 3 worst categories from GT scores
3. For each: propose 1-2 new variants, quick-test on 5 companies via serper_search
4. If promising (GT > 0.25 on sample), add to config and run full pattern test
5. Score with GT evaluation, compare to baseline
6. Keep improvements, revert regressions
7. Update best_config.json with findings
8. Repeat until budget exhausted or no improvement

## Rules

- NEVER modify gt_evaluator.py, validate.py, or ground truth files
- Only mutate master_test_config.json through the write_master_config tool
- Test new variants on 5 companies first (1 per tier) — prune below 0.15 GT
- Track query/scrape budget — stop when exhausted
- For SERP-capped categories (tech_stack, partnerships, customer_case_studies), use spider_scrape
- After 3 consecutive no-improvement iterations, switch to exploration mode
""")

    return "\n".join(parts)


# ── Main loop ────────────────────────────────────────────────────────────────

def run_agent(
    model: str = "gpt-4o-mini",
    max_iterations: int = 10,
    budget: float = 0.25,
    max_queries: int = 75,
    max_scrapes: int = 20,
    dry_run: bool = False,
):
    client = OpenAI()
    tracker = ToolTracker(budget=budget, max_queries=max_queries, max_scrapes=max_scrapes)

    print(f"{'='*60}")
    print(f"AUTORESEARCH AGENT")
    print(f"Model: {model}")
    print(f"Budget: ${budget:.2f} | Max queries: {max_queries} | Max scrapes: {max_scrapes}")
    print(f"Max iterations: {max_iterations}")
    print(f"{'='*60}")

    if dry_run:
        print("\n[DRY RUN] Assembling system prompt...")
        prompt = assemble_system_prompt()
        print(f"System prompt length: {len(prompt)} chars")
        print(f"\nFirst 500 chars:\n{prompt[:500]}")
        return

    system_prompt = assemble_system_prompt()
    print(f"System prompt assembled: {len(system_prompt)} chars")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": (
            "Begin the optimization loop. Start by saving a baseline, then identify "
            "the 3 worst-performing categories and propose improvements. Work through "
            f"the loop protocol. Budget: {tracker.summary()}"
        )},
    ]

    iteration = 0
    total_input_tokens = 0
    total_output_tokens = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'─'*60}")
        print(f"ITERATION {iteration}/{max_iterations} | {tracker.summary()}")
        print(f"{'─'*60}")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.7,
            )
        except Exception as e:
            print(f"[ERROR] OpenAI API call failed: {e}")
            break

        usage = response.usage
        if usage:
            total_input_tokens += usage.prompt_tokens
            total_output_tokens += usage.completion_tokens
            print(f"Tokens: {usage.prompt_tokens} in / {usage.completion_tokens} out")

        choice = response.choices[0]
        assistant_msg = choice.message

        messages.append(assistant_msg)

        if assistant_msg.content:
            print(f"\n[AGENT]: {assistant_msg.content[:500]}")

        if choice.finish_reason == "stop" and not assistant_msg.tool_calls:
            print("\n[AGENT] Loop complete (no more tool calls).")
            break

        if not assistant_msg.tool_calls:
            print("\n[AGENT] No tool calls, ending.")
            break

        for tc in assistant_msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            print(f"  → {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:200]})")

            result = handle_tool_call(fn_name, fn_args, tracker)
            print(f"    ← {result[:200]}{'...' if len(result) > 200 else ''}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        if not tracker.can_query() and not tracker.can_scrape():
            print(f"\n[BUDGET EXHAUSTED] {tracker.summary()}")
            messages.append({
                "role": "user",
                "content": (
                    "Budget exhausted. Wrap up: save final baseline, update best_config.json "
                    "with any improvements found, and summarize what changed."
                ),
            })

        # Trim context if getting large (keep system + last N messages)
        if len(messages) > 80:
            messages = [messages[0]] + messages[-60:]
            print("  [Context trimmed to last 60 messages]")

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Iterations: {iteration}")
    print(f"Tool usage: {tracker.summary()}")
    print(f"OpenAI tokens: {total_input_tokens} in / {total_output_tokens} out")
    est_cost = (total_input_tokens * 0.15 / 1_000_000) + (total_output_tokens * 0.6 / 1_000_000)
    print(f"Est. OpenAI cost: ${est_cost:.4f} (gpt-4o-mini pricing)")
    print(f"Total est. cost: ${tracker.cost + est_cost:.3f}")


def main():
    parser = argparse.ArgumentParser(description="Autoresearch Agent — OpenAI tool-calling optimization loop")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model (default: gpt-4o-mini)")
    parser.add_argument("--max-iterations", type=int, default=10, help="Max loop iterations (default: 10)")
    parser.add_argument("--budget", type=float, default=0.25, help="Total budget in USD (default: 0.25)")
    parser.add_argument("--max-queries", type=int, default=75, help="Max Serper queries (default: 75)")
    parser.add_argument("--max-scrapes", type=int, default=20, help="Max Spider scrapes (default: 20)")
    parser.add_argument("--dry-run", action="store_true", help="Assemble prompt but don't run")
    args = parser.parse_args()

    run_agent(
        model=args.model,
        max_iterations=args.max_iterations,
        budget=args.budget,
        max_queries=args.max_queries,
        max_scrapes=args.max_scrapes,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
