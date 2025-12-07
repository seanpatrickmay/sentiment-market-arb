from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from db import models
from mapping.sports_parser import parse_and_update_market_from_normalized, parse_market_text
from ingestion.types import NormalizedMarket


@dataclass
class MappingCandidateSuggestion:
    market_id: int
    candidate_sports_event_id: Optional[int]
    confidence_score: float


def _team_match_score(parsed_home: str, parsed_away: str, ev: models.SportsEvent) -> float:
    if not parsed_home or not parsed_away:
        return 0.0
    # Exact match with correct home/away
    if ev.home_team.lower() == parsed_home.lower() and ev.away_team.lower() == parsed_away.lower():
        return 1.0
    # Match ignoring home/away ordering
    if ev.home_team.lower() == parsed_away.lower() and ev.away_team.lower() == parsed_home.lower():
        return 0.8
    return 0.0


def _time_score(time_hint: Optional[datetime], ev_time: Optional[datetime]) -> float:
    if not time_hint or not ev_time:
        return 0.5
    delta_hours = abs((ev_time - time_hint).total_seconds()) / 3600.0
    if delta_hours < 2:
        return 1.0
    if delta_hours < 12:
        return 0.8
    if delta_hours < 48:
        return 0.5
    return 0.0


def suggest_for_market(db: Session, market: models.Market) -> List[models.MappingCandidate]:
    # Ensure parsed fields exist
    nm = NormalizedMarket(
        venue_id=market.venue_id,
        venue_market_key=market.venue_market_key,
        market_type=market.market_type,
        question_text=market.question_text,
        listing_time_utc=market.listing_time_utc,
        expiration_time_utc=market.expiration_time_utc,
        status=market.status,
        raw={},
        parsed_sport_hint=market.parsed_sport,
        parsed_league_hint=market.parsed_league,
    )
    parse_and_update_market_from_normalized(market, nm)

    parsed = parse_market_text(
        market.question_text,
        sport_hint=market.parsed_sport,
        league_hint=market.parsed_league,
        time_hint=market.parsed_start_time_hint or market.expiration_time_utc or market.listing_time_utc,
    )

    parsed_sport = parsed.sport
    parsed_home = parsed.home_team or market.parsed_home_team
    parsed_away = parsed.away_team or market.parsed_away_team
    time_hint = parsed.event_start_time_hint or market.parsed_start_time_hint

    # Clear existing pending candidates for this market
    db.query(models.MappingCandidate).filter(
        models.MappingCandidate.market_id == market.id,
        models.MappingCandidate.status == "pending",
    ).delete()

    candidates: List[models.MappingCandidate] = []

    event_query = db.query(models.SportsEvent)
    if parsed_sport:
        event_query = event_query.filter(models.SportsEvent.sport == parsed_sport)

    events = event_query.all()

    # Score existing events
    for ev in events:
        team_score = _team_match_score(parsed_home or "", parsed_away or "", ev)
        time_score_val = _time_score(time_hint, ev.event_start_time_utc)
        league_score = 1.0 if parsed_sport and ev.sport == parsed_sport else 0.5

        base_score = 0.6 * team_score + 0.3 * time_score_val + 0.1 * league_score
        if base_score <= 0:
            continue

        candidate = models.MappingCandidate(
            market_id=market.id,
            candidate_sports_event_id=ev.id,
            confidence_score=round(float(base_score), 4),
            features_json={
                "team_score": team_score,
                "time_score": time_score_val,
                "league_score": league_score,
            },
            status="pending",
        )
        db.add(candidate)
        candidates.append(candidate)

    # If no candidates at all, create a new sports event based on parsed data
    if not candidates:
        if parsed_sport and parsed_home and parsed_away:
            new_event = models.SportsEvent(
                sport=parsed_sport,
                league=parsed.league or parsed_sport,
                home_team=parsed_home,
                away_team=parsed_away,
                event_start_time_utc=time_hint,
                canonical_name=f"{parsed_home} @ {parsed_away}"
                if parsed_home and parsed_away
                else market.question_text[:200],
                status="scheduled",
                source="auto",
            )
            db.add(new_event)
            db.flush()

            candidate = models.MappingCandidate(
                market_id=market.id,
                candidate_sports_event_id=new_event.id,
                confidence_score=0.7,
                features_json={"created_new_event": True},
                status="pending",
            )
            db.add(candidate)
            candidates.append(candidate)

    return candidates


def bulk_suggest_for_unmapped_markets(db: Session, limit: int = 100) -> int:
    """
    Generate mapping candidates for markets that do not yet have an
    associated sports_event and have no confirmed event_market_links.
    """
    subq = (
        db.query(models.EventMarketLink.market_id)
        .filter(models.EventMarketLink.confirmed_by_user.is_(True))
        .subquery()
    )

    markets = (
        db.query(models.Market)
        .filter(
            ~models.Market.id.in_(subq),
        )
        .limit(limit)
        .all()
    )

    total = 0
    for market in markets:
        created = suggest_for_market(db, market)
        if created:
            total += len(created)

    return total
