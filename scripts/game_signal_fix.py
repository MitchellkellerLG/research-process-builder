"""
Phase 5: fix patterns targeting Stream A failures + B4 rework.
"""
import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=False)

SERPER_KEY = os.environ.get("SERPER_API_KEY", "")
if not SERPER_KEY:
    raise SystemExit("SERPER_API_KEY not found")

TBS = "qdr:m"
HEADERS = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}

FIX_QUERIES = [
    # Stream A fixes
    {
        "id": "A1b",
        "label": "Gaming press reveals — DLC/expansion excluded",
        "q": '"new game" announced 2026 site:ign.com OR site:eurogamer.net OR site:gamespot.com -DLC -expansion -update -patch -season',
        "num": 20,
    },
    {
        "id": "A2b",
        "label": "VGC standalone — announce/reveal/first look",
        "q": "site:videogameschronicle.com announced OR reveals OR \"first look\" OR \"new game\"",
        "num": 20,
    },
    {
        "id": "A3b",
        "label": "Publisher-gated AAA announce",
        "q": '"game announced" OR "revealed today" OR "world premiere" "Bandai Namco" OR "FromSoftware" OR "Square Enix" OR "Ubisoft" OR "Capcom" OR "Bethesda" OR "Sony Santa Monica" OR "Xbox Game Studios" OR "Naughty Dog" OR "CD Projekt"',
        "num": 20,
    },
    {
        "id": "A4b",
        "label": "GamesIndustry.biz standalone — new game announced",
        "q": "site:gamesindustry.biz \"new game\" OR announces OR announced OR reveal 2026",
        "num": 20,
    },
    {
        "id": "A5b",
        "label": "Character animation genre + announce press",
        "q": '"action RPG" OR "MMORPG" OR "soulslike" OR "open world" announced OR revealed OR \"world premiere\" site:ign.com OR site:kotaku.com OR site:pcgamer.com OR site:eurogamer.net',
        "num": 20,
    },
    {
        "id": "A6b",
        "label": "Triple-i Initiative + ID@Xbox + Wholesome Direct reveals",
        "q": '"Triple-i Initiative" OR "ID@Xbox" OR "Wholesome Direct" OR "Future Games Show" reveal OR announced OR "world premiere" 2026',
        "num": 20,
    },
    {
        "id": "A7b",
        "label": "UE5/RE Engine — publisher scoped",
        "q": '"Unreal Engine 5" OR "RE Engine" game announced OR reveal OR "world premiere" "Capcom" OR "Bandai Namco" OR "Square Enix" OR "Ubisoft" OR "2K" OR "Epic" OR "Sega" OR "Konami"',
        "num": 15,
    },
    # Stream B fix
    {
        "id": "B4b",
        "label": "Press wire — game studio funding (no sports betting noise)",
        "q": 'site:businesswire.com OR site:prnewswire.com OR site:einpresswire.com "game studio" OR "game developer" OR "indie game" OR "gaming startup" raises OR funding OR investment -FanDuel -DraftKings -sports betting',
        "num": 15,
    },
    {
        "id": "B8",
        "label": "GamesBeat dedicated funding coverage",
        "q": "site:venturebeat.com/games funding OR raised OR investment OR \"Series A\" OR \"seed round\" studio developer 2026",
        "num": 15,
    },
    {
        "id": "B9",
        "label": "GamesPress + Gamespress.com studio funding",
        "q": "site:gamespress.com funding OR raised OR investment million studio 2026",
        "num": 10,
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
    out_path = Path(__file__).parent.parent / "searches" / "game-signal-fix-results.md"
    lines = ["# Game Signal Fix Queries — Phase 5\n", f"TBS: {TBS} | Fix queries: {len(FIX_QUERIES)}\n\n"]

    total_hits = 0
    for q in FIX_QUERIES:
        print(f"  Running {q['id']}: {q['label']}...")
        try:
            data = serper_search(q["q"], q["num"])
            results = extract_results(data)
            total_hits += len(results)
            lines.append(f"## {q['id']} -- {q['label']}\n")
            lines.append(f"Query: `{q['q']}`\n")
            lines.append(f"Results: {len(results)}\n\n")
            for r in results:
                lines.append(f"- **{r['title']}**  \n  {r['url']}  \n  {r['snippet']}  \n  Date: {r['date']}\n\n")
        except Exception as e:
            lines.append(f"## {q['id']} -- ERROR: {e}\n\n")

    lines.append(f"\n---\nTotal results: {total_hits}\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Done. {total_hits} results saved.")


if __name__ == "__main__":
    run()
