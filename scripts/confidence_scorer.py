"""
Confidence Scorer for Series A Pipeline

Assigns HIGH / MEDIUM / LOW confidence to each extracted company record
before it writes to Supabase. Three independent signals combined into
a composite gate.

Signal 1 — name_quality:    Is company_name a real company name or a headline description?
Signal 2 — funding_explicit: Is a funding round type in the title, snippet, or only implied?
Signal 3 — source_tier:     How reliable is the source domain?

Composite rule:
  Any signal LOW  → composite LOW
  All signals HIGH → composite HIGH
  Otherwise        → MEDIUM

Usage:
    from confidence_scorer import score_confidence, ConfidenceLevel

    level, signals = score_confidence(company_name, title, snippet, source_domain)
    if level == ConfidenceLevel.LOW:
        drop()
    elif level == ConfidenceLevel.MEDIUM:
        send_to_review_queue()
    else:
        write_to_supabase()
"""

import re
from enum import Enum
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SignalScores(NamedTuple):
    name_quality: ConfidenceLevel
    funding_explicit: ConfidenceLevel
    source_tier: ConfidenceLevel
    composite: ConfidenceLevel
    reasons: list[str]


# ---------------------------------------------------------------------------
# Signal 1: Name quality
# Detects journalistic framing, media outlet names, and VC/investor names
# ---------------------------------------------------------------------------

# Patterns that indicate a news headline was captured instead of a company name
HEADLINE_FRAMING = re.compile(
    r"""
    \b(
        ex[-\s]          # "Ex-Twitter", "Ex CEO"
        | ceo['s]?       # "CEO's", "CEOs"
        | founder['s]?
        | backed         # "VC-backed startup"
        | raises?        # "raises $X" shouldn't be in a name
        | raised
        | secures?
        | closes?
        | funding
        | round
        | acqui          # acquires/acquired
        | unveils?
        | launches?
        | announces?
    )\b
    |
    's\s+\w+             # possessive: "CEO's Startup", "Musk's Company"
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Words that suggest the name is a media outlet or aggregator, not the funded company
MEDIA_OUTLET_NAMES = re.compile(
    r'\b(Inc42|TechCrunch|VentureBeat|Forbes|Reuters|Bloomberg|Axios|'
    r'Crunchbase|PitchBook|AlleyWatch|FinSMEs|SiliconAngle|Dealroom|'
    r'VCNewsDaily|TechEU|EU.Startups|BusinessWire|PRNewswire)\b',
    re.IGNORECASE,
)

# VC / fund names that shouldn't be company_name (the funded entity)
VC_NAME_IN_COMPANY = re.compile(
    r'\b(Capital|Ventures|Partners|Fund|Investment|Advisors|'
    r'Management|Sequoia|Andreessen|Bessemer|Greylock|Accel|'
    r'Lightspeed|GV|YC|a16z|Khosla|NEA|Insight|Tiger Global|'
    r'Coatue|General Catalyst|Goldman Sachs|Bain)\b',
    re.IGNORECASE,
)

# "startup" in extracted name = GPT pulled from headline context, not a proper name
STARTUP_IN_NAME = re.compile(r'\bstartup\b', re.IGNORECASE)


def score_name_quality(company_name: str) -> tuple[ConfidenceLevel, str]:
    name = company_name.strip()

    if not name or len(name) < 2:
        return ConfidenceLevel.LOW, "empty or too short"

    if HEADLINE_FRAMING.search(name):
        return ConfidenceLevel.LOW, f"headline framing in name: '{name[:50]}'"

    if MEDIA_OUTLET_NAMES.search(name):
        return ConfidenceLevel.LOW, f"media outlet name: '{name[:50]}'"

    if STARTUP_IN_NAME.search(name):
        return ConfidenceLevel.LOW, f"'startup' in name — likely headline extraction: '{name[:50]}'"

    if VC_NAME_IN_COMPANY.search(name):
        return ConfidenceLevel.MEDIUM, f"VC/fund term in name — may be investor not company: '{name[:50]}'"

    # Name looks like proper noun: starts with capital, reasonable length, no framing
    if re.match(r'^[A-Z]', name) and 3 <= len(name) <= 60:
        return ConfidenceLevel.HIGH, "clean proper noun"

    return ConfidenceLevel.MEDIUM, f"ambiguous name format: '{name[:50]}'"


# ---------------------------------------------------------------------------
# Signal 2: Funding round explicitness
# ---------------------------------------------------------------------------

FUNDING_ROUND_RE = re.compile(
    r'\b(?:Series\s+[A-E]|Seed|Pre[-\s]?Seed|Growth|Bridge|Extension|IPO\s+round)\b',
    re.IGNORECASE
)
AMOUNT_RE = re.compile(
    r'[\$\€\£\¥]\s*[\d,.]+\s*[MBmb](?:illion)?|\d+\s*(?:million|billion)',
    re.IGNORECASE
)


def score_funding_explicit(title: str, snippet: str) -> tuple[ConfidenceLevel, str]:
    if FUNDING_ROUND_RE.search(title):
        return ConfidenceLevel.HIGH, "funding round type in title"

    combined = f"{title} {snippet}"
    if FUNDING_ROUND_RE.search(snippet):
        return ConfidenceLevel.MEDIUM, "funding round type in snippet only"

    # Has explicit funding amount but no round label — still likely valid
    if AMOUNT_RE.search(combined):
        return ConfidenceLevel.MEDIUM, "funding amount present but no explicit round type"

    return ConfidenceLevel.LOW, "no funding round signal in title or snippet"


# ---------------------------------------------------------------------------
# Signal 3: Source tier
# ---------------------------------------------------------------------------

TIER_HIGH_DOMAINS = {
    # Dedicated funding news
    "finsmes.com", "thesaasnews.com", "alleywatch.com",
    # Press wires — company-authored announcements
    "businesswire.com", "prnewswire.com", "einpresswire.com",
    # Quality tech press
    "techcrunch.com", "eu-startups.com", "tech.eu", "techround.co.uk",
    # Recognized funding trackers
    "ventureburn.com", "siliconangle.com", "pulse2.com",
}

TIER_MEDIUM_DOMAINS = {
    # Good but noisier
    "yahoo.com", "finance.yahoo.com", "entrepreneur.com",
    "businessinsider.com", "zdnet.com", "infotechlead.com",
    "citybiz.co", "biospace.com", "eu.36kr.com",
}

TIER_LOW_DOMAINS = {
    # Social media — not primary sources
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com",
    "x.com", "cdninstagram.com",
    # Paywalled / unreliable
    "wsj.com", "ft.com",
    # Dead sources confirmed in query audit
    "vcnewsdaily.com",
    # CDN / redirect domains
    "t.co", "bit.ly", "amazonaws.com", "cloudfront.net",
    # Binance / crypto platforms that embed random news
    "binance.com",
}


def _normalize_domain(domain: str) -> str:
    d = domain.lower().strip()
    d = d.removeprefix("https://").removeprefix("http://")
    d = d.split("/")[0].removeprefix("www.")
    return d


def score_source_tier(source_domain: str) -> tuple[ConfidenceLevel, str]:
    domain = _normalize_domain(source_domain)

    if domain in TIER_LOW_DOMAINS:
        return ConfidenceLevel.LOW, f"low-tier source: {domain}"

    if domain in TIER_HIGH_DOMAINS:
        return ConfidenceLevel.HIGH, f"tier-HIGH source: {domain}"

    if domain in TIER_MEDIUM_DOMAINS:
        return ConfidenceLevel.MEDIUM, f"tier-MEDIUM source: {domain}"

    # Unknown domains: MEDIUM by default — don't block, but flag for review
    return ConfidenceLevel.MEDIUM, f"unknown source domain: {domain}"


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------

_LEVEL_ORDER = {ConfidenceLevel.LOW: 0, ConfidenceLevel.MEDIUM: 1, ConfidenceLevel.HIGH: 2}


def _composite(signals: list[ConfidenceLevel]) -> ConfidenceLevel:
    """Any LOW → LOW. All HIGH → HIGH. Otherwise MEDIUM."""
    if ConfidenceLevel.LOW in signals:
        return ConfidenceLevel.LOW
    if all(s == ConfidenceLevel.HIGH for s in signals):
        return ConfidenceLevel.HIGH
    return ConfidenceLevel.MEDIUM


def score_confidence(
    company_name: str,
    title: str,
    snippet: str,
    source_domain: str,
) -> SignalScores:
    """
    Score a single extracted company record.

    Returns SignalScores with per-signal levels and composite verdict.
    """
    name_lvl, name_reason = score_name_quality(company_name)
    explicit_lvl, explicit_reason = score_funding_explicit(title, snippet)
    tier_lvl, tier_reason = score_source_tier(source_domain)

    composite = _composite([name_lvl, explicit_lvl, tier_lvl])

    return SignalScores(
        name_quality=name_lvl,
        funding_explicit=explicit_lvl,
        source_tier=tier_lvl,
        composite=composite,
        reasons=[name_reason, explicit_reason, tier_reason],
    )
