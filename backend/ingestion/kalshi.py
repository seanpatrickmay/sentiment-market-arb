from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re

from db import models
from db.session import SessionLocal
from ingestion.types import NormalizedMarket
from mapping.sports_parser import parse_and_update_market_from_normalized
from kalshi.client import build_kalshi_client
from ingestion.kalshi_events import ingest_kalshi_events


def _iso_to_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def fetch_raw_markets(params: Optional[Dict[str, Any]] = None) -> list[dict]:
    """
    Fetch raw Kalshi markets via signed requests.
    Expects /trade-api/v2/markets returning { "markets": [...] } or { "data": [...] }.
    """
    client = build_kalshi_client()
    if not client:
        raise RuntimeError("Kalshi credentials not configured")

    resp = client.get(client.MARKETS_PATH, params=params or {})
    data = resp.json()
    if isinstance(data, dict):
        if "markets" in data and isinstance(data["markets"], list):
            return data["markets"]
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
    if isinstance(data, list):
        return data
    raise RuntimeError(f"Unexpected Kalshi markets response shape: {type(data)} with keys {list(data.keys()) if isinstance(data, dict) else ''}")


def _infer_market_type(question_text: str) -> str:
    text = question_text.lower()
    if "moneyline" in text or "ml" in text:
        return "moneyline"
    if "total" in text or "over/under" in text:
        return "total"
    if "spread" in text or "handicap" in text:
        return "spread"
    return "binary"


def _extract_event_ref(raw: dict) -> Optional[str]:
    """
    Attempt to extract a stable event identifier from the market payload.
    """
    return raw.get("event_ticker") or raw.get("event") or raw.get("series_ticker")


def _parse_event_from_ticker(raw: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Attempt to parse sport and teams from Kalshi event_ticker / ticker.
    Example: event_ticker 'KXNBAGAME-25DEC10PHXOKC' -> sport NBA, away PHX, home OKC
    """
    event_ticker = str(raw.get("event_ticker") or raw.get("ticker") or "")
    sport = None
    if "NBA" in event_ticker:
        sport = "NBA"
    elif "NFL" in event_ticker:
        sport = "NFL"
    elif "MLB" in event_ticker:
        sport = "MLB"
    elif "NHL" in event_ticker:
        sport = "NHL"

    away = None
    home = None
    m = re.search(r"([A-Z]{6})$", event_ticker)
    if m:
        teams = m.group(1)
        away, home = teams[:3], teams[3:]
    return sport, home, away


def normalize_market(raw: dict) -> NormalizedMarket:
    # Skip multi-leg / multivariate combos for now
    if raw.get("mve_selected_legs"):
        raise ValueError("skip_multileg")

    question = str(raw.get("title") or raw.get("subtitle") or raw.get("question") or raw.get("ticker") or "")
    market_type = _infer_market_type(question)
    listing = _iso_to_dt(raw.get("listing_ts") or raw.get("open_time") or raw.get("created_time"))
    expiry = _iso_to_dt(raw.get("expiry_ts") or raw.get("close_time") or raw.get("latest_expiration_time"))
    status = str(raw.get("status") or "open")
    parsed_sport, home_team, away_team = _parse_event_from_ticker(raw)
    event_ref = _extract_event_ref(raw)

    return NormalizedMarket(
        venue_id="kalshi",
        venue_market_key=str(raw.get("ticker") or raw.get("id") or ""),
        market_type=market_type,
        question_text=question,
        listing_time_utc=listing,
        expiration_time_utc=expiry,
        status=status,
        raw=raw,
        parsed_sport_hint=parsed_sport,
        parsed_league_hint=parsed_sport,
        parsed_home_team_hint=home_team,
        parsed_away_team_hint=away_team,
        event_ref_hint=event_ref,
    )


def upsert_market(db, nm: NormalizedMarket, events_by_ref: Optional[dict] = None) -> models.Market:
    market = (
        db.query(models.Market)
        .filter(
            models.Market.venue_id == nm.venue_id,
            models.Market.venue_market_key == nm.venue_market_key,
        )
        .first()
    )
    if market is None:
        market = models.Market(
            venue_id=nm.venue_id,
            venue_market_key=nm.venue_market_key,
        )
        db.add(market)

    market.market_type = nm.market_type
    market.question_text = nm.question_text
    market.listing_time_utc = nm.listing_time_utc
    market.expiration_time_utc = nm.expiration_time_utc
    market.status = nm.status

    if nm.parsed_sport_hint and not market.parsed_sport:
        market.parsed_sport = nm.parsed_sport_hint
    if nm.parsed_league_hint and not market.parsed_league:
        market.parsed_league = nm.parsed_league_hint
    if nm.parsed_home_team_hint:
        market.parsed_home_team = nm.parsed_home_team_hint
    if nm.parsed_away_team_hint:
        market.parsed_away_team = nm.parsed_away_team_hint

    parse_and_update_market_from_normalized(market, nm)

    # Ensure we have an id before creating link rows
    db.flush()

    if events_by_ref and nm.event_ref_hint:
        ev = events_by_ref.get(nm.event_ref_hint)
        if ev:
            market.sports_event_id = ev.id
            existing_link = (
                db.query(models.EventMarketLink)
                .filter(
                    models.EventMarketLink.market_id == market.id,
                    models.EventMarketLink.sports_event_id == ev.id,
                )
                .first()
            )
            if not existing_link:
                db.add(
                    models.EventMarketLink(
                        market_id=market.id,
                        sports_event_id=ev.id,
                        link_type="primary",
                        confirmed_by_user=False,
                        source="kalshi_ingest",
                    )
                )

    return market


def ingest_kalshi_sports_markets() -> int:
    """
    Fetch Kalshi markets, normalize, and upsert sports-related markets.

    Returns the number of markets upserted.
    """
    # First ingest events so we can link markets to events.
    ingest_kalshi_events()

    db = SessionLocal()
    count = 0
    try:
        # Ensure venue row exists
        venue = db.query(models.Venue).filter(models.Venue.id == "kalshi").first()
        if venue is None:
            venue = models.Venue(
                id="kalshi",
                name="Kalshi",
                base_currency="USD",
                fee_model={"type": "per_contract", "trading_fee": 0.02, "settlement_fee": 0.01, "fee_cap": 9.0},
            )
            db.add(venue)
            db.commit()

        events = (
            db.query(models.SportsEvent)
            .filter(models.SportsEvent.source == "kalshi", models.SportsEvent.external_event_ref.isnot(None))
            .all()
        )
        events_by_ref = {ev.external_event_ref: ev for ev in events if ev.external_event_ref}

        # Fetch markets per event when we can; fall back to a single fetch.
        raw_markets: list[dict] = []
        if events_by_ref:
            seen_keys = set()
            for ref in events_by_ref.keys():
                try:
                    subset = fetch_raw_markets({"event_ticker": ref})
                except Exception:
                    subset = []
                for raw in subset:
                    key = raw.get("ticker") or raw.get("id")
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    raw_markets.append(raw)
        else:
            raw_markets = fetch_raw_markets()

        for raw in raw_markets:
            try:
                nm = normalize_market(raw)
            except ValueError:
                # skip multileg or invalid formats
                continue
            sport_hint = (nm.parsed_sport_hint or "").upper()
            if sport_hint and sport_hint not in ("MLB", "NFL", "NBA", "NHL"):
                continue

            upsert_market(db, nm, events_by_ref=events_by_ref)
            count += 1

        db.commit()
    finally:
        db.close()

    return count
