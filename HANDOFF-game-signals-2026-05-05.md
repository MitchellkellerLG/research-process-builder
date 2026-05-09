# Handoff: find-game-signals — 2026-05-05

## Status
Process built and validated. Extraction script written and partially tested. Needs: re-run extraction → push CSV to Google Sheets.

## What's Done
- Process file: `processes/find-game-signals/process.md` — 11 primary queries, two streams
- Status file: `processes/find-game-signals/STATUS.md`
- Test results: `searches/game-signal-test-results.md` (14 queries, 101 results) + `searches/game-signal-fix-results.md` (10 fix queries, 64 results)
- Extraction script: `scripts/game_signals_extract.py` — GPT-4o-mini classifier, CSV + JSON output
- Test scripts: `scripts/game_signal_test.py` + `scripts/game_signal_fix.py`

## Immediate Next Step: Run Extraction

```bash
py scripts/game_signals_extract.py
```

Reads both search result markdown files, deduplicates, calls GPT-4o-mini to classify each result as `game_announcement | studio_funding | noise`, extracts 8 structured fields, writes:
- `output/game-signals-30day.csv`
- `output/game-signals-30day.json`

Script was fixed for Unicode crash (cp1252 encoding issue in print). Should run clean now.

Expected output: ~20-30 real signals from 165 raw results. From partial run we saw:
- Metro 2039 (4A Games, action)
- Kiln (Double Fine)
- Crop (11-bit Studios)
- Blood of the Dawnwalker (Rebel Wolves)
- Dragon Ball Xenoverse 3 (Bandai Namco)
- AC Black Flag Resynced (Ubisoft)
- Above Land: Rhapsody
- Valor Mortis (One More Level, soulslike)
- Beast of Reincarnation (Game Freak)
- Long Gone (Triple-i)
- Silent Whispers (LKA, UE5)
- Alien: Isolation 2 teaser (Creative Assembly)
- Human Computer $5.7M seed
- Spill Games $3.1M seed
- Mindtail $2M pre-seed
- Reforged Studios $30M
- Soloband Games Series A

## Push to Google Sheets

### Option A: Service Account (cleanest for automation)
1. Create service account in Google Cloud Console
2. Download JSON key → save to `~/.config/gspread/service_account.json`
3. Share target Sheet with service account email
4. Run: `py scripts/game_signals_extract.py --push-sheets <SHEET_ID>`

### Option B: OAuth (one-time browser auth)
1. Run `py scripts/game_signals_extract.py --push-sheets <SHEET_ID>`
2. gspread will prompt for OAuth if no service account found
3. Or use MCP Google Drive tool (start with `mcp__claude_ai_Google_Drive__authenticate`)

### Sheet columns (in order):
signal_type | studio_name | studio_domain | game_title | funding_amount | genre | platform | source_url | summary | date_detected

## Accuracy (current)
- Stream A (game announces): ~85% — showcase roundup scraping is the remaining gap
- Stream B (studio funding): ~90%+
- Combined: ~88%

## Remaining Work for 90%+
1. Add `site:gematsu.com` to A3 query for Japanese studio coverage
2. Build Stage 3 showcase scraper — A4 returns roundup articles (40+ games/article), need to scrape and explode into individual rows
3. 7-day live run with `qdr:d` to validate daily recall vs 30-day test

## Graduate to TriggerDev
After live validation, use `/graduate-to-trigger` skill. Pattern: same as `series-a-daily` monitor. Daily 7am ET cron, outputs to same Google Sheet via append.

## Key Kill Patterns (never re-test)
- `"new IP"` on LinkedIn = IP law contamination
- `site:gamesindustry.biz` for individual reveals = editorial only
- `site:venturebeat.com/games` as site: query = subdomain broken
- `"gaming company"` in press wires = FanDuel/DraftKings sports betting
- `site:crunchbase.com/news` = query structure broken (0 results)
- reddit-find `-o` flag = crashes on emoji in post titles (use stdout only)
