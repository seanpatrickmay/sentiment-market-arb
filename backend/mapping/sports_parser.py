from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from db import models
from ingestion.types import NormalizedMarket


@dataclass
class ParsedMarketMetadata:
    sport: Optional[str]
    league: Optional[str]
    home_team: Optional[str]
    away_team: Optional[str]
    event_start_time_hint: Optional[datetime]


SPORT_MAP = {
    "NBA": "NBA",
    "NFL": "NFL",
    "MLB": "MLB",
    "NHL": "NHL",
}


def _clean_team_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())


def parse_market_text(
    question_text: str,
    sport_hint: Optional[str] = None,
    league_hint: Optional[str] = None,
    time_hint: Optional[datetime] = None,
) -> ParsedMarketMetadata:
    sport = None
    if sport_hint:
        upper = sport_hint.upper()
        sport = SPORT_MAP.get(upper, upper)
    else:
        upper_text = question_text.upper()
        for k, v in SPORT_MAP.items():
            if k in upper_text:
                sport = v
                break

    league = None
    if league_hint:
        league = league_hint.upper()
    else:
        league = sport

    # Strip obvious suffixes like "- Moneyline (date)"
    main_text = question_text
    if " - " in main_text:
        main_text = main_text.split(" - ", 1)[0]
    if ":" in main_text:
        # e.g. "NBA: Team A @ Team B"
        main_text = main_text.split(":", 1)[1]

    home_team = None
    away_team = None

    patterns = [
        r"(?P<away>.+?)\s+@\s+(?P<home>.+)",
        r"(?P<away>.+?)\s+at\s+(?P<home>.+)",
        r"(?P<home>.+?)\s+vs\.?\s+(?P<away>.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, main_text, flags=re.IGNORECASE)
        if match:
            away_raw = match.group("away")
            home_raw = match.group("home")
            away_team = _clean_team_name(away_raw)
            home_team = _clean_team_name(home_raw)
            break

    return ParsedMarketMetadata(
        sport=sport,
        league=league,
        home_team=home_team,
        away_team=away_team,
        event_start_time_hint=time_hint,
    )


def parse_and_update_market_from_normalized(market: models.Market, nm: NormalizedMarket) -> None:
    parsed = parse_market_text(
        nm.question_text,
        sport_hint=nm.parsed_sport_hint or market.parsed_sport,
        league_hint=nm.parsed_league_hint or market.parsed_league,
        time_hint=nm.expiration_time_utc or nm.listing_time_utc,
    )

    if parsed.sport:
        market.parsed_sport = parsed.sport
    if parsed.league:
        market.parsed_league = parsed.league
    if parsed.home_team:
        market.parsed_home_team = parsed.home_team
    if parsed.away_team:
        market.parsed_away_team = parsed.away_team
    if parsed.event_start_time_hint:
        market.parsed_start_time_hint = parsed.event_start_time_hint
