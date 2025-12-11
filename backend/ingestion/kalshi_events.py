from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Tuple

import re

from db import models
from db.session import SessionLocal
from kalshi.client import build_kalshi_client


def _iso_to_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_event_ticker(event_ticker: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Attempt to pull sport + home/away hints from an event ticker.
    Example tickers often end with 6 letters for the teams.
    """
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
    m = re.search(r"([A-Z]{6})$", event_ticker or "")
    if m:
        teams = m.group(1)
        away, home = teams[:3], teams[3:]

    return sport, home, away


def normalize_event(raw: dict) -> Optional[models.SportsEvent]:
    """
    Normalize a Kalshi event payload (sports only).
    """
    category = (raw.get("category") or "").lower()
    if category != "sports":
        return None

    title = str(raw.get("title") or raw.get("event_ticker") or "")
    sub_title = str(raw.get("sub_title") or "")
    event_ticker = str(raw.get("event_ticker") or "")
    # Heuristic sport from series_ticker prefix
    series_ticker = str(raw.get("series_ticker") or "")
    sport, home_hint, away_hint = _parse_event_ticker(event_ticker or series_ticker)
    if not sport:
        for token in ["NBA", "NFL", "MLB", "NHL"]:
            if token in series_ticker or token in title:
                sport = token
                break
    if not sport:
        sport = "SPORTS"

    start_time = _iso_to_dt(
        raw.get("event_start_time")
        or raw.get("event_start_date")
        or raw.get("open_time")
        or raw.get("close_time")
        or raw.get("listing_ts")
    )

    ev = models.SportsEvent(
        sport=sport,
        league=sport,
        home_team=home_hint or "",
        away_team=away_hint or "",
        event_start_time_utc=start_time,
        location=None,
        canonical_name=title or sub_title or event_ticker,
        status="scheduled",
        source="kalshi",
        external_event_ref=event_ticker or series_ticker,
    )
    return ev


def ingest_kalshi_events() -> int:
    """
    Fetch sports events from Kalshi and upsert into sports_events.
    """
    client = build_kalshi_client()
    if not client:
        raise RuntimeError("Kalshi credentials not configured")
    resp = client.get("/trade-api/v2/events")
    data = resp.json()
    events = data.get("events", []) if isinstance(data, dict) else []

    db = SessionLocal()
    count = 0
    try:
        for raw in events:
            ev = normalize_event(raw)
            if not ev:
                continue
            # Upsert by external_event_ref
            existing = (
                db.query(models.SportsEvent)
                .filter(models.SportsEvent.external_event_ref == ev.external_event_ref, models.SportsEvent.source == "kalshi")
                .first()
            )
            if existing:
                existing.sport = ev.sport
                existing.league = ev.league
                existing.canonical_name = ev.canonical_name
                existing.status = ev.status
                if ev.home_team:
                    existing.home_team = ev.home_team
                if ev.away_team:
                    existing.away_team = ev.away_team
                if ev.event_start_time_utc:
                    existing.event_start_time_utc = ev.event_start_time_utc
            else:
                db.add(ev)
            count += 1
        db.commit()
    finally:
        db.close()

    return count
