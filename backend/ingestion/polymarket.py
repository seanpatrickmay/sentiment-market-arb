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
        # Expecting ISO 8601; will raise if not compatible
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def fetch_raw_markets() -> list[dict]:
    """
    Fetch raw Polymarket markets.

    This assumes the configured POLYMARKET_API_BASE exposes a `/markets`
    endpoint returning either:
      - {"data": [...]} (clob.polymarket.com)
      - {"markets": [...]} or a bare list.
    Adjust the path/shape if your deployment differs.
    """
    url = f"{settings.polymarket_api_base.rstrip('/')}/markets"
    headers = {}
    if settings.polymarket_api_key:
        headers["Authorization"] = f"Bearer {settings.polymarket_api_key}"

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # clob.polymarket.com shape: {"data": [...], "next_cursor": ..., ...}
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
        if "markets" in data and isinstance(data["markets"], list):
            return data["markets"]
    if isinstance(data, list):
        return data
    raise RuntimeError("Unexpected Polymarket markets response shape")


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
    question = str(raw.get("question") or raw.get("title") or "")
    market_type = _infer_market_type(question)
    listing = _iso_to_dt(raw.get("openDate") or raw.get("created_at"))
    expiry = _iso_to_dt(raw.get("closeDate") or raw.get("endDate") or raw.get("expires_at"))
    status = str(raw.get("status") or "open")
    category = str(raw.get("category") or raw.get("sport") or "").upper() or None

    return NormalizedMarket(
        venue_id="polymarket",
        venue_market_key=str(raw.get("id") or raw.get("slug") or ""),
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


def ingest_polymarket_sports_markets() -> int:
    """
    Fetch Polymarket markets, normalize, and upsert sports-related markets.

    Returns the number of markets upserted.
    """
    raw_markets = fetch_raw_markets()
    count = 0
    db = SessionLocal()
    try:
        # Ensure venue row exists
        venue = db.query(models.Venue).filter(models.Venue.id == "polymarket").first()
        if venue is None:
            venue = models.Venue(
                id="polymarket",
                name="Polymarket",
                base_currency="USD",
                fee_model={"type": "profit_commission", "commission_rate": 0.02},
            )
            db.add(venue)
            db.commit()

        for raw in raw_markets:
            nm = normalize_market(raw)
            # Filter to our sports of interest if possible
            sport_hint = (nm.parsed_sport_hint or "").upper()
            if sport_hint and sport_hint not in ("MLB", "NFL", "NBA", "NHL"):
                continue

            upsert_market(db, nm)
            count += 1

        db.commit()
    finally:
        db.close()

    return count
