from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class NormalizedMarket:
    venue_id: str
    venue_market_key: str
    market_type: str
    question_text: str
    listing_time_utc: Optional[datetime]
    expiration_time_utc: Optional[datetime]
    status: str
    raw: dict[str, Any]
    parsed_sport_hint: Optional[str] = None
    parsed_league_hint: Optional[str] = None
    parsed_home_team_hint: Optional[str] = None
    parsed_away_team_hint: Optional[str] = None
    event_ref_hint: Optional[str] = None
