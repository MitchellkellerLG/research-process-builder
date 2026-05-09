# Handoff: find-game-signals — 2026-05-05-B

## Status
60-day extraction complete. Sheet partially pushed (batch bug). Ready to fix push → weekly cron.

## What's Done This Session
- Switched classifier from OpenAI → back to OpenAI (quota was billing issue, fixed)
- Fixed `None.lower()` dedup crash
- Updated schema: `developer` + `developer_domain` + `publisher` + `publisher_domain` + `article_date` (dropped old `studio_name`)
- Dedup now by `game_title` for announcements (was studio+title)
- Fixed em dash regex in parser (`[\-—]`) — was silently dropping all results from new files
- Added `--tbs` + `--out` flags to `game_signal_test.py`
- Added A8 (gematsu.com) + A9 (polygon.com) queries
- 60-day run: 301 raw → 111 signals (40 game announces, 71 fundings)
- Wired gws CLI for all Sheets ops (subprocess, not gspread)
- Batched push to handle Windows CLI length limit

## The Batch Push Bug
Error: `Expecting value: line 1 column 1 (char 0)` — one gws batch chunk returns empty stdout.
Likely cause: gws returns empty body (not JSON) for a successful update when cells already exist.

**Fix:** wrap each batch parse in try/except and check stderr for errors:
```python
try:
    result = _json.loads(r2.stdout)
    total_pushed += result.get("updatedRows", 0)
except:
    if r2.returncode != 0:
        print(f"Batch error: {r2.stderr[:200]}")
```

## Sheet
https://docs.google.com/spreadsheets/d/1CPmppaXj_CrtzLLaBtUbuHVe3p52P9Zl3nBJ2FJYYOg
May be partially populated — clear Sheet1 and re-run push after fixing bug.

## Sources to Add (A stream)
- `site:gamerant.com` — catches franchise/IP scoops (e.g. KOTOR revival). Add to A1 or new A10 query
- `site:gematsu.com` — already added as A8, validate it's pulling Japanese studio content
- `site:polygon.com` — already added as A9

## Immediate Next Steps
1. Fix batch push bug (3 lines)
2. Clear sheet + re-push: `py scripts/game_signals_extract.py --push-sheets 1CPmppaXj_CrtzLLaBtUbuHVe3p52P9Zl3nBJ2FJYYOg`
3. Add `site:gamerant.com` to A1 query
4. Graduate to weekly Trigger.dev cron via `/graduate-to-trigger`
   - Pattern: same as series-a-daily
   - Cadence: weekly (Monday 7am ET) with `qdr:w`
   - Output: append to same Sheet

## Key Files
- `scripts/game_signals_extract.py` — main extract + classify + push
- `scripts/game_signal_test.py` — search runner (now has `--tbs` + `--out`)
- `searches/game-signal-60day-results.md` — 60-day raw results (151 results)
- `searches/game-signal-test-results.md` — 30-day raw results
- `searches/game-signal-fix-results.md` — fix queries raw results
- `output/game-signals-30day.csv` — 111 signals, 13 columns

## Schema (FIELDNAMES)
`signal_type | developer | developer_domain | publisher | publisher_domain | game_title | funding_amount | genre | platform | article_date | source_url | summary | date_detected`

## Key Kill Patterns (never re-test)
- `"new IP"` on LinkedIn = IP law contamination
- `site:gamesindustry.biz` for individual reveals = editorial only
- `site:venturebeat.com/games` as site: = subdomain broken
- `"gaming company"` in press wires = FanDuel/DraftKings
- `site:crunchbase.com/news` = query structure broken (0 results)
- `reddit-find -o` flag = crashes on emoji

## Workflow Reminder
OpenAI key name in `.env`: `OPEN_AI_API` (not `OPENAI_API_KEY`)
gws CLI: `C:/Users/mitch/AppData/Roaming/npm/gws.cmd` — use subprocess, not shell
