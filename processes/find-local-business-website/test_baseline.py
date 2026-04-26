"""
Baseline annealing test for find-local-business-website process.

Runs a BBB-first website discovery prompt against 15 ground truth
local businesses using gpt-4o-mini via OpenAI with web_search
(Serper) and scrape_url (Spider) as tool calls.

Usage:
    py test_baseline.py                    # run all 15
    py test_baseline.py --ids gt-01 gt-04  # run specific IDs
    py test_baseline.py --verbose          # show agent turns
    py test_baseline.py --dry-run          # show prompt only, no API calls
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

EVERYTHING_CC = Path("C:/Users/mitch/Everything_CC")
load_dotenv(EVERYTHING_CC / ".env", override=True)

import requests as http_requests

GT_PATH = Path(__file__).parent / "ground_truth.json"
RESULTS_DIR = Path(__file__).parent / "results"

MODEL = "gpt-4o-mini"
MAX_TURNS = 7
REQUIRED_KEYS = ["website", "confidence", "source"]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SPIDER_API_KEY = os.getenv("SPIDER_API_KEY")

# --- Tool definitions for OpenAI function calling ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search Google via Serper. Returns URLs, titles, snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_url",
            "description": "Scrape a URL and return clean markdown content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to scrape"},
                },
                "required": ["url"],
            },
        },
    },
]


def execute_web_search(query: str) -> str:
    """Execute a Serper search and return formatted results."""
    resp = http_requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query, "gl": "us", "hl": "en", "num": 10},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    lines = []
    for i, r in enumerate(data.get("organic", [])[:10], 1):
        lines.append(f"{i}. [{r.get('title', '')}]({r.get('link', '')})")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
    if data.get("knowledgeGraph"):
        kg = data["knowledgeGraph"]
        lines.append(f"\nKnowledge Graph: {kg.get('title', '')} — {kg.get('description', '')}")
        if kg.get("website"):
            lines.append(f"Website: {kg['website']}")

    return "\n".join(lines) if lines else "No results found."


def execute_scrape(url: str) -> str:
    """Scrape a URL via Spider Cloud and return markdown."""
    resp = http_requests.post(
        "https://api.spider.cloud/scrape",
        headers={
            "Authorization": f"Bearer {SPIDER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "url": url,
            "return_format": "markdown",
            "readability": True,
            "request": "smart",
            "cache": True,
            "max_credits_allowed": 20,
            "proxy": "residential",
            "block_ads": True,
            "block_images": True,
            "block_stylesheets": True,
            "filter_main_only": True,
            "filter_output_images": True,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list) and data:
        content = data[0].get("content", "")
    elif isinstance(data, dict):
        content = data.get("content", "")
    else:
        content = str(data)

    # Truncate to avoid blowing up context
    if len(content) > 4000:
        content = content[:4000] + "\n\n[TRUNCATED]"
    return content or "No content extracted."


def execute_tool(name: str, args: dict) -> str:
    """Route a tool call to its implementation."""
    try:
        if name == "web_search":
            return execute_web_search(args["query"])
        elif name == "scrape_url":
            return execute_scrape(args["url"])
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error: {e}"


# --- OpenAI agent loop ---

def run_agent(prompt: str, verbose: bool = False) -> dict:
    """Run gpt-4o-mini with tool calling loop."""
    messages = [
        {"role": "system", "content": (
            "You are a local business research agent. You find websites and owner info "
            "for small businesses using web search and page scraping. "
            "Always return your final answer as a single JSON object, no other text."
        )},
        {"role": "user", "content": prompt},
    ]

    total_prompt_tokens = 0
    total_completion_tokens = 0
    tools_called = []

    for turn in range(MAX_TURNS):
        if verbose:
            print(f"  [Turn {turn + 1}/{MAX_TURNS}]")

        if turn >= MAX_TURNS - 2 and turn > 0:
            messages.append({
                "role": "system",
                "content": f"Turn {turn + 1}/{MAX_TURNS}. Return your JSON answer NOW with what you have.",
            })

        resp = http_requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "tools": TOOLS,
                "temperature": 0.1,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        usage = data.get("usage", {})
        total_prompt_tokens += usage.get("prompt_tokens", 0)
        total_completion_tokens += usage.get("completion_tokens", 0)

        choice = data["choices"][0]
        msg = choice["message"]

        tool_calls = msg.get("tool_calls", [])

        if not tool_calls:
            if verbose:
                content_preview = (msg.get("content") or "")[:200]
                print(f"  [FINAL] {content_preview}")

            # Estimate cost: 4o-mini pricing
            cost = (total_prompt_tokens * 0.15 + total_completion_tokens * 0.60) / 1_000_000
            return {
                "content": msg.get("content", ""),
                "turns": turn + 1,
                "tools_called": tools_called,
                "costs": {"total_usd": round(cost, 6)},
            }

        messages.append(msg)

        for tc in tool_calls:
            func_name = tc["function"]["name"]
            func_args = json.loads(tc["function"]["arguments"])

            if verbose:
                if func_name == "web_search":
                    print(f"  [TOOL] web_search: {func_args.get('query', '')}")
                else:
                    print(f"  [TOOL] scrape_url: {func_args.get('url', '')[:80]}")

            result = execute_tool(func_name, func_args)
            tools_called.append({"name": func_name, "args": func_args})

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    # Ran out of turns
    cost = (total_prompt_tokens * 0.15 + total_completion_tokens * 0.60) / 1_000_000
    return {
        "content": messages[-1].get("content", ""),
        "turns": MAX_TURNS,
        "tools_called": tools_called,
        "costs": {"total_usd": round(cost, 6)},
        "error": "max turns reached",
    }


def run_agent_with_retry(prompt: str, verbose: bool = False, max_retries: int = 1) -> dict:
    """Run agent with JSON parse retry."""
    import re

    for attempt in range(max_retries + 1):
        if verbose and attempt > 0:
            print(f"  [RETRY {attempt}]")

        result = run_agent(prompt, verbose=verbose)

        if "error" in result and "max turns" not in result.get("error", ""):
            continue

        content = result.get("content", "")

        # Extract JSON from response
        parsed = None
        try:
            # Try markdown fence first
            fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if fence:
                parsed = json.loads(fence.group(1))
            else:
                # Find first { ... }
                start = content.find("{")
                if start != -1:
                    depth = 0
                    for i, c in enumerate(content[start:], start):
                        if c == "{": depth += 1
                        elif c == "}": depth -= 1
                        if depth == 0:
                            parsed = json.loads(content[start:i+1])
                            break
        except json.JSONDecodeError:
            pass

        if parsed and all(k in parsed for k in REQUIRED_KEYS):
            result["parsed"] = parsed
            return result

    result["error"] = result.get("error", "JSON parse failed after retries")
    result["parsed"] = {}
    return result


# --- Prompt builder ---

def build_prompt(company: dict) -> str:
    """Build the BBB-first website discovery prompt for a local business."""
    name = company["company_name"]
    city = company["city"]
    state = company["state"]
    zip_code = company.get("zip", "")

    zip_clause = f", ZIP {zip_code}" if zip_code else ""

    return f"""Find the official website for a local business.

Business: {name}
Location: {city}, {state}{zip_clause}

## Instructions

You have web_search and scrape_url tools. Use MINIMAL searches — return your JSON as soon as you have a confident answer.

### Step 1: BBB Search (preferred — gives website + owner)
Search: "{name}" {city} site:bbb.org

If no BBB result, try ONE variant with key words from the name (strip LLC/Inc/Corp, try common trade name variants like "Contractors" → "Builders").

If a BBB page is found:
- Scrape it with scrape_url
- Extract: website URL, owner/principal name, business address, phone
- Verify the BBB listing address matches {city}, {state}
- RETURN JSON IMMEDIATELY — do not keep searching if BBB gave you a website

### Step 2: Direct Search (only if BBB found no website)
Search: "{name}" {city} {state}

From results, pick the business website (not directory pages ABOUT the business):
- The business's OWN domain is the target, not Yelp/YP/Manta pages
- Domain contains company name words → strong signal
- Result mentions {city} or {state} → confirms identity

### Step 3: Give up quickly
If 2 searches return nothing useful, return null. Do NOT keep searching — "no website found" is valid.

## Rules
- Strip LLC, Inc, Corp, Ltd from the company name when searching
- "No website found" is a valid answer — return null with low confidence
- If multiple businesses share the name, use {city}/{state} to disambiguate
- If a candidate website is in a DIFFERENT city/state, it's the wrong business — return null
- BBB address match = high confidence. Search-only = medium. Unverified = low.

## Return JSON only — no other text:

{{{{
  "website": "https://example.com or null if not found",
  "bbb_url": "BBB page URL or null",
  "owner_name": "owner/principal name from BBB or null",
  "owner_title": "title if found or null",
  "phone": "phone number or null",
  "address_match": "exact if BBB address matches, partial if same city, none if no BBB",
  "confidence": "high, medium, or low",
  "source": "bbb, directory, search, or none"
}}}}"""


# --- Scoring ---

def score_result(result: dict, gt: dict) -> dict:
    """Score a single result against ground truth."""
    parsed = result.get("parsed", {})
    if not parsed:
        return {
            "website_correct": False,
            "owner_correct": False,
            "bbb_found": False,
            "confidence_calibrated": False,
            "error": result.get("error", "no parsed output"),
        }

    found_website = (parsed.get("website") or "").lower().rstrip("/")
    known_website = (gt.get("known_website") or "").lower().rstrip("/")

    def domain(url):
        return url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/").split("/")[0]

    def domain_match(found, known):
        """Match on root domain — subpages count as correct."""
        if not found or not known:
            return False
        return domain(found) == domain(known) or domain(known) in found

    if not known_website:
        website_correct = not found_website or parsed.get("website") is None
    else:
        website_correct = domain_match(found_website, known_website)
        if not website_correct and gt.get("known_website_alt"):
            website_correct = domain_match(found_website, gt["known_website_alt"])

    known_owner = gt.get("known_owner")
    found_owner = parsed.get("owner_name")
    if known_owner and found_owner:
        owner_correct = known_owner.lower() in found_owner.lower() or found_owner.lower() in known_owner.lower()
    elif not known_owner:
        owner_correct = None
    else:
        owner_correct = False

    known_bbb = gt.get("known_bbb")
    found_bbb = parsed.get("bbb_url")
    bbb_found = bool(found_bbb) if known_bbb else None

    confidence = parsed.get("confidence", "").lower()
    if website_correct:
        confidence_calibrated = confidence in ("high", "medium")
    elif not known_website:
        confidence_calibrated = confidence == "low" or parsed.get("website") is None
    else:
        confidence_calibrated = confidence == "low"

    return {
        "website_correct": website_correct,
        "owner_correct": owner_correct,
        "bbb_found": bbb_found,
        "confidence_calibrated": confidence_calibrated,
        "found_website": parsed.get("website"),
        "found_owner": parsed.get("owner_name"),
        "found_bbb": parsed.get("bbb_url"),
        "found_confidence": confidence,
        "found_source": parsed.get("source"),
    }


# --- Main runner ---

def run_baseline(ids: list[str] | None = None, verbose: bool = False, dry_run: bool = False):
    """Run baseline test against ground truth."""
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not found. Check .env at Everything_CC root.")
        sys.exit(1)
    if not SERPER_API_KEY:
        print("ERROR: SERPER_API_KEY not found.")
        sys.exit(1)

    with open(GT_PATH) as f:
        ground_truth = json.load(f)

    if ids:
        ground_truth = [gt for gt in ground_truth if gt["id"] in ids]

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"baseline_{timestamp}"

    results = []
    total_cost = 0.0

    print(f"\n{'='*70}")
    print(f"  BASELINE RUN: find-local-business-website")
    print(f"  Model: {MODEL} | Companies: {len(ground_truth)} | Max turns: {MAX_TURNS}")
    print(f"{'='*70}\n")

    for i, gt in enumerate(ground_truth):
        prompt = build_prompt(gt)

        if dry_run:
            print(f"[{i+1}/{len(ground_truth)}] {gt['id']} — {gt['company_name']}")
            print(f"  Prompt length: {len(prompt)} chars")
            print(f"  Difficulty: {gt['difficulty']}")
            print()
            continue

        print(f"[{i+1}/{len(ground_truth)}] {gt['id']} — {gt['company_name']} ({gt['city']}, {gt['state']}) [{gt['difficulty']}]")

        start = time.time()
        result = run_agent_with_retry(prompt=prompt, verbose=verbose)
        elapsed = time.time() - start

        cost = result.get("costs", {}).get("total_usd", 0)
        total_cost += cost
        turns = result.get("turns", 0)

        score = score_result(result, gt)

        entry = {
            "id": gt["id"],
            "company_name": gt["company_name"],
            "city": gt["city"],
            "state": gt["state"],
            "difficulty": gt["difficulty"],
            "known_website": gt.get("known_website"),
            "known_owner": gt.get("known_owner"),
            "known_bbb": gt.get("known_bbb"),
            **score,
            "cost_usd": round(cost, 6),
            "elapsed_sec": round(elapsed, 1),
            "turns": turns,
            "tools_used": [t["name"] for t in result.get("tools_called", [])],
            "raw_content": result.get("content", "")[:500],
        }
        results.append(entry)

        web_icon = "Y" if score["website_correct"] else "N"
        owner_icon = "Y" if score.get("owner_correct") is True else ("-" if score.get("owner_correct") is None else "N")
        bbb_icon = "Y" if score.get("bbb_found") is True else ("-" if score.get("bbb_found") is None else "N")

        print(f"  Website: {web_icon} | Owner: {owner_icon} | BBB: {bbb_icon} | "
              f"Conf: {score.get('found_confidence', '?')} | Source: {score.get('found_source', '?')} | "
              f"${cost:.4f} | {elapsed:.1f}s | {turns}t")
        if score.get("found_website"):
            print(f"  Found: {score['found_website']}")
        if score.get("error"):
            print(f"  ERROR: {score['error']}")
        print()

    if dry_run:
        return

    total = len(results)
    web_correct = sum(1 for r in results if r["website_correct"])
    owner_correct = sum(1 for r in results if r["owner_correct"] is True)
    owner_testable = sum(1 for r in results if r["owner_correct"] is not None)
    bbb_found = sum(1 for r in results if r["bbb_found"] is True)
    bbb_testable = sum(1 for r in results if r["bbb_found"] is not None)

    print(f"\n{'='*70}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"  Website accuracy:  {web_correct}/{total} ({web_correct/total*100:.0f}%)")
    if owner_testable:
        print(f"  Owner accuracy:    {owner_correct}/{owner_testable} ({owner_correct/owner_testable*100:.0f}%)")
    if bbb_testable:
        print(f"  BBB hit rate:      {bbb_found}/{bbb_testable} ({bbb_found/bbb_testable*100:.0f}%)")
    print(f"  Total cost:        ${total_cost:.4f}")
    print(f"  Avg cost/lead:     ${total_cost/total:.4f}")
    print()

    for diff in ("easy", "medium", "hard"):
        subset = [r for r in results if r["difficulty"] == diff]
        if subset:
            correct = sum(1 for r in subset if r["website_correct"])
            print(f"  {diff.upper():6s}: {correct}/{len(subset)} correct")

    print(f"{'='*70}\n")

    output_path = RESULTS_DIR / f"{run_name}.json"
    with open(output_path, "w") as f:
        json.dump({
            "run_name": run_name,
            "timestamp": timestamp,
            "model": MODEL,
            "max_turns": MAX_TURNS,
            "total_companies": total,
            "website_accuracy": web_correct / total,
            "total_cost_usd": round(total_cost, 6),
            "results": results,
        }, f, indent=2)

    print(f"Results saved: {output_path}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baseline annealing test")
    parser.add_argument("--ids", nargs="+", help="Specific GT IDs to test")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Show prompts without calling API")
    args = parser.parse_args()

    run_baseline(ids=args.ids, verbose=args.verbose, dry_run=args.dry_run)
