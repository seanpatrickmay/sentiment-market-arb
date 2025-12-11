from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from db import models

router = APIRouter(prefix="/sports-events", tags=["sports-events"], redirect_slashes=False)


@router.get("", response_model=List[dict])
def list_sports_events(
    sport: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.SportsEvent)
    if sport:
        query = query.filter(models.SportsEvent.sport == sport)
    events = query.order_by(models.SportsEvent.event_start_time_utc.asc().nullslast()).all()
    return [
        {
            "id": ev.id,
            "sport": ev.sport,
            "league": ev.league,
            "home_team": ev.home_team,
            "away_team": ev.away_team,
            "event_start_time_utc": ev.event_start_time_utc,
            "canonical_name": ev.canonical_name,
            "status": ev.status,
        }
        for ev in events
    ]


@router.get("/{event_id}", response_model=dict)
def get_sports_event(event_id: int, db: Session = Depends(get_db)):
    ev = db.query(models.SportsEvent).filter(models.SportsEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Sports event not found")
    markets = [
        {
            "id": m.id,
            "venue_id": m.venue_id,
            "market_type": m.market_type,
            "question_text": m.question_text,
            "status": m.status,
        }
        for m in ev.markets
    ]
    return {
        "id": ev.id,
        "sport": ev.sport,
        "league": ev.league,
        "home_team": ev.home_team,
        "away_team": ev.away_team,
        "event_start_time_utc": ev.event_start_time_utc,
        "canonical_name": ev.canonical_name,
        "status": ev.status,
        "markets": markets,
    }
