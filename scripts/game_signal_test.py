"""
Phase 3 test: run all Stream A + Stream B query candidates.
Output: searches/game-signal-test-results.md (default)

Usage:
    py scripts/game_signal_test.py
    py scripts/game_signal_test.py --tbs qdr:2m --out searches/game-signal-60day-results.md
"""
import argparse
import os
import requests
from pathlib import Path
from dotenv import dotenv_values

_env = {
    **dotenv_values(Path(__file__).parent.parent.parent / ".env"),
    **dotenv_values(Path(__file__).parent.parent / ".env"),
}
SERPER_KEY = _env.get("SERPER_API_KEY") or os.environ.get("SERPER_API_KEY", "")
if not SERPER_KEY:
    raise SystemExit("SERPER_API_KEY not found in .env")

parser = argparse.ArgumentParser()
parser.add_argument("--tbs", default="qdr:m", help="Serper time filter (e.g. qdr:m, qdr:2m, qdr:w)")
parser.add_argument("--out", default="searches/game-signal-test-results.md")
_args = parser.parse_args()
TBS = _args.tbs
HEADERS = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}

QUERIES = [
    # Stream A — Game Announcements
    {
        "id": "A1",
        "label": "Gaming press — reveal/announce",
        "q": '"game reveal" OR "new game announced" OR "reveal trailer" site:ign.com OR site:eurogamer.net OR site:gamespot.com OR site:gamerant.com',
        "num": 20,
    },
    {
        "id": "A2",
        "label": "VGC + GI.biz — reveal/announce",
        "q": '"game reveal" OR "game announced" site:videogameschronicle.com OR site:gamesindustry.biz',
        "num": 20,
    },
    {
        "id": "A3",
        "label": "Animation-heavy genres announced",
        "q": '"action RPG" OR "open world RPG" OR "MMORPG" OR "soulslike" game announced OR reveal 2026',
        "num": 20,
    },
    {
        "id": "A4",
        "label": "Major franchise signals",
        "q": '"God of War" OR "Monster Hunter" OR "Witcher" OR "Cyberpunk" OR "GTA" sequel OR "new game" OR announced',
        "num": 20,
    },
    {
        "id": "A5",
        "label": "Press wire — video game announce",
        "q": 'site:businesswire.com OR site:prnewswire.com "video game" announce OR reveal OR "new title"',
        "num": 15,
    },
    {
        "id": "A6",
        "label": "Gaming events — reveals",
        "q": '"Summer Game Fest" OR "State of Play" OR "Xbox Showcase" OR "Nintendo Direct" reveal game',
        "num": 20,
    },
    {
        "id": "A7",
        "label": "AAA engine signal",
        "q": '"Unreal Engine 5" OR "RE Engine" OR "Decima Engine" game announced OR reveal OR trailer',
        "num": 20,
    },
    {
        "id": "A8",
        "label": "Gematsu — Japanese studio announcements",
        "q": 'site:gematsu.com announced OR reveal OR trailer 2026',
        "num": 20,
    },
    {
        "id": "A9",
        "label": "Polygon — game reveals",
        "q": 'site:polygon.com "announced" OR "reveal trailer" game 2026',
        "num": 20,
    },
    # Stream B — Game Studio Funding
    {
        "id": "B1",
        "label": "Broad game studio funding",
        "q": '"game studio" raises OR raised OR funding OR investment million 2026',
        "num": 20,
    },
    {
        "id": "B2",
        "label": "Game studio round types",
        "q": '"game developer" OR "game development studio" "Series A" OR "Series B" OR seed OR funding',
        "num": 20,
    },
    {
        "id": "B3",
        "label": "Vertical press — GI.biz + GamesBeat",
        "q": "site:gamesindustry.biz OR site:venturebeat.com funding investment raised game studio",
        "num": 20,
    },
    {
        "id": "B4",
        "label": "Press wire — game studio funding",
        "q": 'site:businesswire.com OR site:prnewswire.com "game studio" OR "game developer" OR "gaming company" raises OR funding OR investment',
        "num": 15,
    },
    {
        "id": "B5",
        "label": "Pocket Gamer Biz — mobile gaming funding",
        "q": "site:pocketgamer.biz funding investment raised million",
        "num": 10,
    },
    {
        "id": "B6",
        "label": "Crunchbase News — gaming funding",
        "q": 'site:crunchbase.com/news "game" OR "gaming" funding 2026',
        "num": 10,
    },
    {
        "id": "B7",
        "label": "Console/PC game studio raises — broad",
        "q": '"video game" OR "console game" studio raises OR secured OR "closed a" million funding',
        "num": 20,
    },
]


def serper_search(q, num):
    resp = requests.post(
        "https://google.serper.dev/search",
        headers=HEADERS,
        json={"q": q, "tbs": TBS, "gl": "us", "hl": "en", "num": num},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def extract_results(data):
    out = []
    for r in data.get("organic", []):
        out.append({
            "title": r.get("title", ""),
            "url": r.get("link", ""),
            "snippet": r.get("snippet", ""),
            "date": r.get("date", ""),
        })
    return out


def run():
    out_path = Path(__file__).parent.parent / _args.out
    lines = [f"# Game Signal Test — TBS: {TBS}\n", f"TBS: {TBS} | Queries: {len(QUERIES)}\n\n"]

    total_hits = 0
    for q in QUERIES:
        print(f"  Running {q['id']}: {q['label']}...")
        try:
            data = serper_search(q["q"], q["num"])
            results = extract_results(data)
            total_hits += len(results)
            lines.append(f"## {q['id']} — {q['label']}\n")
            lines.append(f"Query: `{q['q']}`\n")
            lines.append(f"Results: {len(results)}\n\n")
            for r in results:
                lines.append(f"- **{r['title']}**  \n  {r['url']}  \n  {r['snippet']}  \n  Date: {r['date']}\n\n")
        except Exception as e:
            lines.append(f"## {q['id']} — ERROR: {e}\n\n")

    lines.append(f"\n---\nTotal results: {total_hits}\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nDone. {total_hits} results -> {out_path}")


if __name__ == "__main__":
    run()
