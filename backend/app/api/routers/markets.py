from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from db import models

router = APIRouter(prefix="/markets", tags=["markets"], redirect_slashes=False)


@router.get("", response_model=List[dict])
def list_markets(
    venue_id: Optional[str] = None,
    sport: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Market)
    if venue_id:
        query = query.filter(models.Market.venue_id == venue_id)
    if sport:
        query = query.join(models.SportsEvent, models.Market.sports_event).filter(models.SportsEvent.sport == sport)
    markets = query.order_by(models.Market.id.asc()).limit(200).all()
    return [
        {
            "id": m.id,
            "venue_id": m.venue_id,
            "sports_event_id": m.sports_event_id,
            "venue_market_key": m.venue_market_key,
            "market_type": m.market_type,
            "question_text": m.question_text,
            "status": m.status,
        }
        for m in markets
    ]
