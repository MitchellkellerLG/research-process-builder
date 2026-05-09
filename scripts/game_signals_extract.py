"""
Extract structured signal records from raw search results.
Reads: searches/game-signal-test-results.md + searches/game-signal-fix-results.md
Calls GPT-4o-mini to classify each result as signal/noise + extract fields.
Writes: output/game-signals-30day.csv + output/game-signals-30day.json

Usage:
    py scripts/game_signals_extract.py
    py scripts/game_signals_extract.py --push-sheets <SHEET_ID>  (after auth)
"""
import json
import os
import re
import csv
import sys
import argparse
from pathlib import Path
from datetime import date
from openai import OpenAI
from dotenv import dotenv_values

_env = {
    **dotenv_values(Path(__file__).parent.parent.parent / ".env"),
    **dotenv_values(Path(__file__).parent.parent / ".env"),  # repo .env wins
}
_api_key = _env.get("OPEN_AI_API") or _env.get("OPENAI_API_KEY") or os.environ.get("OPEN_AI_API") or os.environ.get("OPENAI_API_KEY", "")

client = OpenAI(api_key=_api_key)
TODAY = date.today().isoformat()
OUT_DIR = Path(__file__).parent.parent / "output"
OUT_DIR.mkdir(exist_ok=True)

STREAM_A_IDS = {"A1", "A2", "A3", "A4", "A5", "A6", "A7", "A1b", "A2b", "A3b", "A4b", "A5b", "A6b", "A7b"}
STREAM_B_IDS = {"B1", "B2", "B3", "B4", "B5", "B6", "B7", "B4b", "B8", "B9"}

FIELDNAMES = [
    "signal_type", "developer", "developer_domain", "publisher", "publisher_domain",
    "game_title", "funding_amount", "genre", "platform",
    "article_date", "source_url", "summary", "date_detected"
]

SYSTEM_PROMPT = """You classify gaming search results as signal or noise, then extract structured data.

SIGNAL TYPES:
- "game_announcement": pre-release game reveal or announcement. Must be a brand-new original game not yet released.
  INCLUDE: action RPG, MMORPG, soulslike, open-world RPG, hack & slash, fighting, third-person story shooter, monster hunting genres
  EXCLUDE: DLC, expansions, patches, reviews of released games, forum speculation with no source, sports games, puzzle/casual mobile, remasters, remakes, ports, definitive editions, anniversary editions, enhanced editions, collections of existing games
- "studio_funding": a game studio raised a funding round
  INCLUDE: any disclosed investment in a game development studio
  EXCLUDE: sports betting companies (FanDuel, DraftKings), game retailers (GameStop), government grants, crowdfunding under $500K

If neither applies: "noise"

For signals, extract:
- developer: the studio making the game (game_announcement) or receiving funding (studio_funding)
- developer_domain: developer's website if mentioned (e.g. "rebelwolves.com"), else null
- publisher: publishing company if different from developer, else null. For studio_funding usually null.
- publisher_domain: publisher's website if mentioned, else null
- game_title: game name for game_announcement, null or "undisclosed" for studio_funding with no named game
- funding_amount: e.g. "$5.7M", "€2.1M", null for game_announcement
- genre: one of: Action RPG | MMORPG | Soulslike | Open-World | Hack & Slash | Fighting | Third-Person Shooter | Monster Hunting | Other | null
- platform: comma-separated from: PC, PS5, Xbox Series X, Switch, Mobile — null if not stated
- article_date: publication date of the article in YYYY-MM-DD format if detectable, else null
- summary: 1-2 sentences. Be specific — include developer, game name if known, amount if funding.

Return JSON only:
{
  "classification": "game_announcement" | "studio_funding" | "noise",
  "developer": string | null,
  "developer_domain": string | null,
  "publisher": string | null,
  "publisher_domain": string | null,
  "game_title": string | null,
  "funding_amount": string | null,
  "genre": string | null,
  "platform": string | null,
  "article_date": string | null,
  "summary": string | null
}"""


def parse_results_md(path: Path) -> list[dict]:
    """Parse markdown results file into list of {query_id, title, url, snippet, date}."""
    text = path.read_text(encoding="utf-8")
    records = []
    current_qid = None

    for line in text.splitlines():
        # Detect query section
        m = re.match(r"^## (A\d+[ab]?|B\d+[ab]?) [\-—]", line)
        if m:
            current_qid = m.group(1)
            continue

        # Detect result entry: "- **Title**"
        m = re.match(r"^- \*\*(.+?)\*\*\s*$", line)
        if m and current_qid:
            records.append({
                "query_id": current_qid,
                "title": m.group(1),
                "url": "",
                "snippet": "",
                "date": "",
            })
            continue

        # URL line (follows title)
        if records and records[-1]["url"] == "" and line.strip().startswith("http"):
            records[-1]["url"] = line.strip()
            continue

        # Snippet line
        if records and records[-1]["snippet"] == "" and records[-1]["url"] != "" and line.strip() and not line.strip().startswith("Date:"):
            records[-1]["snippet"] = line.strip()
            continue

        # Date line
        m = re.match(r"\s*Date: (.+)", line)
        if m and records:
            records[-1]["date"] = m.group(1).strip()

    return [r for r in records if r["url"]]


def classify_result(r: dict) -> dict:
    """Call gpt-4o-mini to classify and extract structured fields."""
    user_msg = f"""Title: {r['title']}
URL: {r['url']}
Snippet: {r['snippet']}
Query context: {"Stream A (game announcements)" if r['query_id'] in STREAM_A_IDS else "Stream B (studio funding)"}"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)


def dedup(signals: list[dict]) -> list[dict]:
    """Dedup by source_url, then by game_title (announcements) or developer+amount (funding)."""
    seen_urls = set()
    seen_entities = set()
    out = []
    for s in signals:
        url = s.get("source_url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        if s["signal_type"] == "game_announcement":
            title = (s.get("game_title") or "").lower().strip()
            key = title if title and title != "undisclosed" else None
        else:
            key = ((s.get("developer") or "").lower(), s.get("funding_amount", "")) or None

        if key and key in seen_entities:
            print(f"    [dedup] skipping duplicate: {key}")
            continue
        if key:
            seen_entities.add(key)
        out.append(s)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--push-sheets", metavar="SHEET_ID", help="Google Sheet ID ('new' to create)")
    parser.add_argument("--results", nargs="+", help="Override result files to read")
    args = parser.parse_args()

    # Load raw results
    default_files = [
        Path(__file__).parent.parent / "searches" / "game-signal-test-results.md",
        Path(__file__).parent.parent / "searches" / "game-signal-fix-results.md",
        Path(__file__).parent.parent / "searches" / "game-signal-60day-results.md",
    ]
    files = [Path(f) for f in args.results] if args.results else [f for f in default_files if f.exists()]
    all_results = []
    for f in files:
        all_results.extend(parse_results_md(f))
    results_a = all_results  # unified
    results_b = []
    all_results = results_a + results_b
    print(f"Loaded {len(all_results)} raw results from {len(files)} files")

    # Dedup raw by URL before LLM calls
    seen_raw = set()
    unique_results = []
    for r in all_results:
        if r["url"] not in seen_raw:
            seen_raw.add(r["url"])
            unique_results.append(r)
    print(f"After URL dedup: {len(unique_results)} unique results")

    # Classify each
    signals = []
    noise_count = 0
    for i, r in enumerate(unique_results):
        safe_title = r['title'][:60].encode('ascii', 'replace').decode('ascii')
        print(f"  [{i+1}/{len(unique_results)}] {safe_title}...", end=" ", flush=True)
        try:
            result = classify_result(r)
            cls = result.get("classification", "noise")
            if cls == "noise":
                print(f"NOISE")
                noise_count += 1
            else:
                record = {
                    "signal_type": cls,
                    "developer": result.get("developer"),
                    "developer_domain": result.get("developer_domain"),
                    "publisher": result.get("publisher"),
                    "publisher_domain": result.get("publisher_domain"),
                    "game_title": result.get("game_title"),
                    "funding_amount": result.get("funding_amount"),
                    "genre": result.get("genre"),
                    "platform": result.get("platform"),
                    "article_date": result.get("article_date"),
                    "source_url": r["url"],
                    "summary": result.get("summary"),
                    "date_detected": TODAY,
                }
                signals.append(record)
                print(f"{cls.upper()} — {result.get('developer') or result.get('game_title')}")
        except Exception as e:
            print(f"ERROR: {e}")
            noise_count += 1

    # Dedup signals
    signals = dedup(signals)

    print(f"\nResults: {len(signals)} signals, {noise_count} noise")
    print(f"  Game announces: {sum(1 for s in signals if s['signal_type'] == 'game_announcement')}")
    print(f"  Studio funding: {sum(1 for s in signals if s['signal_type'] == 'studio_funding')}")

    # Write CSV
    csv_path = OUT_DIR / "game-signals-30day.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(signals)
    print(f"\nCSV: {csv_path}")

    # Write JSON
    json_path = OUT_DIR / "game-signals-30day.json"
    json_path.write_text(json.dumps(signals, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"JSON: {json_path}")

    # Push to Google Sheets if requested
    if args.push_sheets:
        import subprocess, json as _json
        GWS = "C:/Users/mitch/AppData/Roaming/npm/gws.cmd"
        try:
            if args.push_sheets == "new":
                r = subprocess.run(
                    [GWS, "sheets", "spreadsheets", "create",
                     "--json", '{"properties":{"title":"Game Signals — LeadGrow"}}', "--format", "json"],
                    capture_output=True, text=True)
                sheet_id = _json.loads(r.stdout)["spreadsheetId"]
                print(f"\nCreated: https://docs.google.com/spreadsheets/d/{sheet_id}")
            else:
                sheet_id = args.push_sheets

            all_rows = [FIELDNAMES] + [[str(s.get(f) or "")[:200] for f in FIELDNAMES] for s in signals]
            BATCH = 5
            total_pushed = 0
            for i in range(0, len(all_rows), BATCH):
                chunk = all_rows[i:i + BATCH]
                start_row = i + 1
                params = _json.dumps({"spreadsheetId": sheet_id, "range": f"Sheet1!A{start_row}", "valueInputOption": "USER_ENTERED"})
                body = _json.dumps({"values": chunk})
                r2 = subprocess.run(
                    [GWS, "sheets", "spreadsheets", "values", "update",
                     "--params", params, "--json", body, "--format", "json"],
                    capture_output=True, text=True)
                try:
                    total_pushed += _json.loads(r2.stdout).get("updatedRows", 0)
                except Exception:
                    if r2.returncode != 0:
                        print(f"Batch error: {r2.stderr[:200]}")
            print(f"Pushed {total_pushed} rows -> https://docs.google.com/spreadsheets/d/{sheet_id}")
        except Exception as e:
            print(f"\nSheets push failed: {e}")

    return signals


if __name__ == "__main__":
    main()
