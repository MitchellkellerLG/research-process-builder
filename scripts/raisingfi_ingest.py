"""
raisingfi_ingest.py — Ingest funding announcements from @raisingfi X account.

Fetches structured tweets via X API v2, parses emoji-delimited fields,
and upserts to the funding_discoveries Supabase table.

Usage:
  python scripts/raisingfi_ingest.py                  # normal run
  python scripts/raisingfi_ingest.py --dry-run        # parse + print, no Supabase
  python scripts/raisingfi_ingest.py --backfill-days 7 # fetch last 7 days
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR.parent / ".env")
load_dotenv(Path.home() / ".env", override=False)

X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL") or os.getenv("SUPABASE_URL")
if SUPABASE_URL and not SUPABASE_URL.startswith("http"):
    SUPABASE_URL = None
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

SUPABASE_TABLE = "funding_discoveries"
STATE_FILE = SCRIPT_DIR.parent / "output" / "raisingfi_state.json"
RAISINGFI_USERNAME = "raisingfi"

X_API_BASE = "https://api.x.com/2"

FIELD_PATTERNS = {
    "company_name": re.compile(r"🏛️\s*Company:\s*(.+)"),
    "website":      re.compile(r"🔗\s*Website:\s*(https?://\S+)"),
    "amount_raised": re.compile(r"📊\s*Amount:\s*(.+)"),
    "round_type":   re.compile(r"🔄\s*Round:\s*(.+)"),
    "industry":     re.compile(r"⚙️\s*Industry:\s*(.+)"),
    "location":     re.compile(r"🌍\s*Location:\s*(.+)"),
    "valuation":    re.compile(r"🧮\s*Valuation:\s*(.+)"),
}


# ---------------------------------------------------------------------------
# X API helpers
# ---------------------------------------------------------------------------

def x_headers() -> dict:
    return {"Authorization": f"Bearer {X_BEARER_TOKEN}"}


def get_user_id(username: str) -> str:
    resp = requests.get(
        f"{X_API_BASE}/users/by/username/{username}",
        headers=x_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "data" not in data:
        raise ValueError(f"User @{username} not found: {data}")
    return data["data"]["id"]


def fetch_tweets(
    user_id: str,
    since_id: str | None = None,
    start_time: str | None = None,
    max_results: int = 100,
) -> list[dict]:
    """Fetch original tweets (no retweets/replies) from user timeline."""
    params = {
        "max_results": min(max_results, 100),
        "exclude": "retweets,replies",
        "tweet.fields": "created_at,text,id,entities",
    }
    if since_id:
        params["since_id"] = since_id
    if start_time:
        params["start_time"] = start_time

    all_tweets = []
    next_token = None

    while True:
        if next_token:
            params["pagination_token"] = next_token

        resp = requests.get(
            f"{X_API_BASE}/users/{user_id}/tweets",
            headers=x_headers(),
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()

        tweets = body.get("data", [])
        all_tweets.extend(tweets)

        meta = body.get("meta", {})
        next_token = meta.get("next_token")
        if not next_token or len(tweets) == 0:
            break

    return all_tweets


# ---------------------------------------------------------------------------
# Domain resolution — prefer empty over wrong
# ---------------------------------------------------------------------------

# Domains that are NOT company websites
BAD_DOMAINS = {
    "twitter.com", "x.com", "linkedin.com", "facebook.com", "instagram.com",
    "youtube.com", "tiktok.com", "github.com", "medium.com", "substack.com",
    # News / aggregators
    "crunchbase.com", "techcrunch.com", "bloomberg.com", "reuters.com",
    "thesaasnews.com", "finsmes.com", "businesswire.com", "prnewswire.com",
    "pitchbook.com", "dealroom.co", "tracxn.com", "venturebeat.com",
    "sifted.eu", "eu-startups.com", "tech.eu", "wired.com", "forbes.com",
    "cnbc.com", "bbc.com", "theverge.com", "engadget.com", "arstechnica.com",
    # URL shorteners
    "t.co", "bit.ly", "goo.gl", "tinyurl.com", "ow.ly",
}


def _extract_domain(url: str) -> str:
    """Extract clean domain from URL, empty string on failure."""
    try:
        host = urlparse(url).netloc.replace("www.", "").lower().strip()
        return host if host else ""
    except Exception:
        return ""


def _is_plausible_company_domain(domain: str, company_name: str) -> bool:
    """Check if domain looks like it belongs to the company (not a news site)."""
    if not domain:
        return False
    if domain in BAD_DOMAINS:
        return False
    for bad in BAD_DOMAINS:
        if domain.endswith("." + bad):
            return False
    # Single-word TLD like "t.co" — reject
    if domain.count(".") < 1:
        return False
    return True


def resolve_company_domain(
    website_tco: str | None,
    entities: dict,
    company_name: str,
) -> str:
    """
    Resolve company domain from tweet data. Strategy:
    1. Match the t.co URL from 🔗 Website: line to its expanded URL in entities
    2. Validate the expanded URL is a plausible company domain
    3. Return empty string if no confident match (better than wrong domain)
    """
    url_entities = entities.get("urls", [])

    # Build t.co → expanded lookup
    tco_map = {}
    for ue in url_entities:
        short = ue.get("url", "")
        expanded = ue.get("unwound_url") or ue.get("expanded_url", "")
        if short and expanded:
            tco_map[short] = expanded

    # Strategy 1: Match the specific t.co from the Website line
    if website_tco and website_tco in tco_map:
        expanded = tco_map[website_tco]
        domain = _extract_domain(expanded)
        if _is_plausible_company_domain(domain, company_name):
            return domain

    # Strategy 2: If only one non-bad URL in entities, it's likely the company
    plausible = []
    for expanded in tco_map.values():
        domain = _extract_domain(expanded)
        if _is_plausible_company_domain(domain, company_name):
            plausible.append(domain)

    if len(plausible) == 1:
        return plausible[0]

    # Strategy 3: If multiple, check if any domain contains a word from company name
    if plausible and company_name:
        name_words = [w.lower() for w in re.split(r'[\s&\-]+', company_name) if len(w) > 2]
        for domain in plausible:
            domain_base = domain.split(".")[0]
            for word in name_words:
                if word in domain_base or domain_base in word:
                    return domain

    # No confident match — return empty (better than wrong)
    return ""


# ---------------------------------------------------------------------------
# Tweet parsing
# ---------------------------------------------------------------------------

def parse_tweet(tweet: dict) -> dict | None:
    """Parse emoji-delimited funding tweet. Returns None if not a funding post."""
    text = tweet.get("text", "")

    if "🏛️" not in text or "📊" not in text:
        return None

    parsed = {}
    for field, pattern in FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            parsed[field] = match.group(1).strip()

    if not parsed.get("company_name"):
        return None

    # Clean company name — sometimes a t.co URL leaks in
    name = parsed["company_name"]
    name = re.sub(r'https?://\S+', '', name).strip()
    if not name:
        return None
    parsed["company_name"] = name

    # Resolve company domain from tweet entities
    website_tco = parsed.pop("website", None)
    parsed["company_domain"] = resolve_company_domain(
        website_tco, tweet.get("entities", {}), parsed.get("company_name", "")
    )

    # Drop N/A valuation
    val = parsed.pop("valuation", None)
    if val and val.strip().upper() != "N/A":
        parsed["valuation"] = val

    parsed["tweet_id"] = tweet["id"]
    parsed["tweet_created_at"] = tweet.get("created_at", "")
    parsed["source_url"] = f"https://x.com/{RAISINGFI_USERNAME}/status/{tweet['id']}"

    return parsed


def to_supabase_row(parsed: dict, date_override: str | None = None) -> dict:
    """Map parsed tweet fields to funding_discoveries schema."""
    if date_override:
        discovered_date = date_override
    elif parsed.get("tweet_created_at"):
        discovered_date = parsed["tweet_created_at"][:10]
    else:
        discovered_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return {
        "discovered_date": discovered_date,
        "company_name": parsed.get("company_name", ""),
        "company_domain": parsed.get("company_domain", ""),
        "amount_raised": parsed.get("amount_raised", ""),
        "round_type": parsed.get("round_type", ""),
        "source_url": parsed.get("source_url", ""),
        "lead_investors": "not_stated",
        "round_reasoning": "not_stated",
        "discovered_by": "raisingfi",
        "industry": parsed.get("industry", ""),
        "location": parsed.get("location", ""),
        "source_count": 1,
        "score": 0,
        "pipeline_version": "raisingfi-1.0",
    }


# ---------------------------------------------------------------------------
# State management (since_id tracking)
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def supabase_headers(prefer: str = None) -> dict:
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def push_to_supabase(rows: list[dict]) -> int:
    """Upsert rows to Supabase. Returns count of successful upserts."""
    seen = set()
    deduped = []
    for row in rows:
        key = (row["company_name"].lower(), row["discovered_date"])
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    upserted = 0
    for row in deduped:
        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
                f"?on_conflict=company_name,discovered_date",
                headers=supabase_headers(prefer="resolution=merge-duplicates"),
                json=[row],
                timeout=15,
            )
            if resp.status_code in (200, 201):
                upserted += 1
            else:
                print(f"  Supabase error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  Supabase error: {e}")
    return upserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest @raisingfi funding tweets")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print, no Supabase push")
    parser.add_argument("--backfill-days", type=int, default=0, help="Fetch tweets from N days ago")
    parser.add_argument("--date", type=str, default=None, help="Override discovered_date (YYYY-MM-DD)")
    args = parser.parse_args()

    if not X_BEARER_TOKEN:
        print("ERROR: X_BEARER_TOKEN not set in environment")
        sys.exit(1)

    if not args.dry_run and (not SUPABASE_URL or not SUPABASE_KEY):
        print("ERROR: SUPABASE_URL and SUPABASE_KEY required (or use --dry-run)")
        sys.exit(1)

    # Resolve user ID
    print(f"Looking up @{RAISINGFI_USERNAME}...")
    user_id = get_user_id(RAISINGFI_USERNAME)
    print(f"  User ID: {user_id}")

    # Determine fetch window
    state = load_state()
    since_id = None
    start_time = None

    if args.backfill_days > 0:
        start_dt = datetime.now(timezone.utc) - timedelta(days=args.backfill_days)
        start_time = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"  Backfill mode: fetching since {start_time}")
    elif state.get("since_id"):
        since_id = state["since_id"]
        print(f"  Incremental mode: since_id={since_id}")
    else:
        start_dt = datetime.now(timezone.utc) - timedelta(days=1)
        start_time = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"  First run: fetching last 24h since {start_time}")

    # Fetch tweets
    print("Fetching tweets...")
    tweets = fetch_tweets(user_id, since_id=since_id, start_time=start_time)
    print(f"  Fetched {len(tweets)} tweets")

    if not tweets:
        print("No new tweets. Done.")
        return

    # Parse
    parsed = []
    skipped = 0
    for tweet in tweets:
        result = parse_tweet(tweet)
        if result:
            parsed.append(result)
        else:
            skipped += 1

    print(f"  Parsed {len(parsed)} funding tweets, skipped {skipped} non-funding")

    if not parsed:
        print("No funding tweets found. Done.")
        # Still update since_id
        newest_id = max(tweets, key=lambda t: int(t["id"]))["id"]
        state["since_id"] = newest_id
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return

    # Build Supabase rows
    rows = [to_supabase_row(p, date_override=args.date) for p in parsed]

    if args.dry_run:
        resolved = [r for r in rows if r["company_domain"]]
        unresolved = [r for r in rows if not r["company_domain"]]
        print(f"\n--- DRY RUN: {len(rows)} rows ({len(resolved)} with domain, "
              f"{len(unresolved)} unresolved) ---")
        for row in rows:
            domain_display = row["company_domain"] or "[NO DOMAIN]"
            print(f"  {row['company_name']:30s} | {row['amount_raised']:15s} | "
                  f"{row['round_type']:12s} | {domain_display}")
        if unresolved:
            print(f"\n  Unresolved domains ({len(unresolved)}):")
            for row in unresolved:
                print(f"    - {row['company_name']}")
    else:
        print("Pushing to Supabase...")
        count = push_to_supabase(rows)
        print(f"  Upserted {count}/{len(rows)} rows")

    # Update state
    newest_id = max(tweets, key=lambda t: int(t["id"]))["id"]
    state["since_id"] = newest_id
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["tweets_processed"] = state.get("tweets_processed", 0) + len(parsed)
    save_state(state)
    print(f"  State saved: since_id={newest_id}")


if __name__ == "__main__":
    main()
