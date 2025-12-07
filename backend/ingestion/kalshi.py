from __future__ import annotations

from datetime import datetime
from typing import Any, List

import httpx

from app.config import settings
from db import models
from db.session import SessionLocal
from ingestion.types import NormalizedMarket
from mapping.sports_parser import parse_and_update_market_from_normalized


def _iso_to_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def fetch_raw_markets() -> list[dict]:
    """
    Fetch raw Kalshi markets.

    This assumes the configured KALSHI_API_BASE exposes a `/markets` endpoint
    returning either a list under `markets` or a list directly.
    Authentication is done via basic auth using `KALSHI_API_KEY` and
    `KALSHI_API_SECRET`.
    """
    url = f"{settings.kalshi_api_base.rstrip('/')}/markets"
    auth = None
    if settings.kalshi_api_key and settings.kalshi_api_secret:
        auth = (settings.kalshi_api_key, settings.kalshi_api_secret)

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, auth=auth)
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "markets" in data:
        markets = data["markets"]
        if isinstance(markets, list):
            return markets
    raise RuntimeError("Unexpected Kalshi markets response shape")


def _infer_market_type(question_text: str) -> str:
    text = question_text.lower()
    if "moneyline" in text or "ml" in text:
        return "moneyline"
    if "total" in text or "over/under" in text:
        return "total"
    if "spread" in text or "handicap" in text:
        return "spread"
    return "unknown"


def normalize_market(raw: dict) -> NormalizedMarket:
    question = str(raw.get("title") or raw.get("question") or "")
    market_type = _infer_market_type(question)
    listing = _iso_to_dt(raw.get("listing_ts") or raw.get("open_time"))
    expiry = _iso_to_dt(raw.get("expiry_ts") or raw.get("close_time"))
    status = str(raw.get("status") or "open")
    category = str(raw.get("category") or raw.get("sport") or "").upper() or None

    return NormalizedMarket(
        venue_id="kalshi",
        venue_market_key=str(raw.get("ticker") or raw.get("id") or ""),
        market_type=market_type,
        question_text=question,
        listing_time_utc=listing,
        expiration_time_utc=expiry,
        status=status,
        raw=raw,
        parsed_sport_hint=category,
        parsed_league_hint=category,
    )


def upsert_market(db, nm: NormalizedMarket) -> models.Market:
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

    parse_and_update_market_from_normalized(market, nm)

    return market


def ingest_kalshi_sports_markets() -> int:
    """
    Fetch Kalshi markets, normalize, and upsert sports-related markets.

    Returns the number of markets upserted.
    """
    raw_markets = fetch_raw_markets()
    count = 0
    db = SessionLocal()
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

        for raw in raw_markets:
            nm = normalize_market(raw)
            sport_hint = (nm.parsed_sport_hint or "").upper()
            if sport_hint and sport_hint not in ("MLB", "NFL", "NBA", "NHL"):
                continue

            upsert_market(db, nm)
            count += 1

        db.commit()
    finally:
        db.close()

    return count
