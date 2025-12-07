from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import httpx

from app.config import settings
from db import models
from db.session import SessionLocal
from ingestion.utils import create_quotes_for_market
from ingestion.polymarket import fetch_raw_markets as fetch_markets
from core.normalize import normalize_quote_fields


def _extract_yes_price(raw: dict) -> Optional[float]:
    """
    Heuristic extraction of a yes/share price from a Polymarket market payload.
    """
    for key in ("bestAsk", "best_ask", "price", "lastPrice", "probability"):
        val = raw.get(key)
        if val is not None:
            try:
                f = float(val)
                if 0 <= f <= 1.0:
                    return f
            except Exception:
                continue

    # If we have both bid/ask, take mid
    bid = raw.get("bestBid") or raw.get("best_bid")
    ask = raw.get("bestAsk") or raw.get("best_ask")
    try:
        bid_f = float(bid) if bid is not None else None
        ask_f = float(ask) if ask is not None else None
        if bid_f is not None and ask_f is not None and bid_f >= 0 and ask_f <= 1:
            return (bid_f + ask_f) / 2.0
    except Exception:
        pass

    return None


def ingest_polymarket_quotes() -> int:
    """
    Attempt to ingest quotes for Polymarket sports markets.
    Returns number of Quote rows created.
    """
    raw_markets = fetch_markets()
    db = SessionLocal()
    created = 0
    try:
        for raw in raw_markets:
            venue_market_key = str(raw.get("id") or raw.get("slug") or "")
            market = (
                db.query(models.Market)
                .filter(models.Market.venue_id == "polymarket", models.Market.venue_market_key == venue_market_key)
                .first()
            )
            if not market:
                continue

            price = _extract_yes_price(raw)
            if price is None:
                continue

            ts = None
            ts_raw = raw.get("updated_at") or raw.get("last_trade_time")
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
                source="polymarket_api",
                timestamp=ts,
            )

        db.commit()
    finally:
        db.close()

    return created

