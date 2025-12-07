from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import httpx

from app.config import settings
from db import models
from db.session import SessionLocal
from ingestion.utils import create_quotes_for_market
from ingestion.kalshi import fetch_raw_markets as fetch_markets


def _extract_yes_price(raw: dict) -> Optional[float]:
    """
    Heuristic extraction of a yes/share price from a Kalshi market payload.
    Kalshi prices are often quoted in cents (0-100). We normalize to 0-1.
    """
    candidates = [
        raw.get("last_price"),
        raw.get("last_price_cents"),
        raw.get("yes_price"),
        raw.get("mid_price"),
        raw.get("close_price"),
    ]
    for val in candidates:
        if val is None:
            continue
        try:
            f = float(val)
            # If value looks like cents, convert
            if f > 1.0:
                f = f / 100.0
            if 0 <= f <= 1.0:
                return f
        except Exception:
            continue

    bid = raw.get("yes_bid")
    ask = raw.get("yes_ask")
    try:
        bid_f = float(bid) if bid is not None else None
        ask_f = float(ask) if ask is not None else None
        if bid_f is not None and ask_f is not None:
            if bid_f > 1.0:
                bid_f /= 100.0
            if ask_f > 1.0:
                ask_f /= 100.0
            if 0 <= bid_f <= 1.0 and 0 <= ask_f <= 1.0:
                return (bid_f + ask_f) / 2.0
    except Exception:
        pass

    return None


def ingest_kalshi_quotes() -> int:
    """
    Attempt to ingest quotes for Kalshi sports markets.
    Returns number of Quote rows created.
    """
    raw_markets = fetch_markets()
    db = SessionLocal()
    created = 0
    try:
        for raw in raw_markets:
            venue_market_key = str(raw.get("ticker") or raw.get("id") or "")
            market = (
                db.query(models.Market)
                .filter(models.Market.venue_id == "kalshi", models.Market.venue_market_key == venue_market_key)
                .first()
            )
            if not market:
                continue

            price = _extract_yes_price(raw)
            if price is None:
                continue

            ts = None
            ts_raw = raw.get("last_trade_time") or raw.get("updated_at")
            if ts_raw:
                try:
                    ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                except Exception:
                    ts = None

            created += create_quotes_for_market(
                db,
                market,
                yes_price=price,
                price_format="share_0_1",
                source="kalshi_api",
                timestamp=ts,
            )

        db.commit()
    finally:
        db.close()

    return created

