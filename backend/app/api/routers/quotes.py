from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.session import get_db
from db import models


router = APIRouter(prefix="/quotes", tags=["quotes"], redirect_slashes=False)


@router.get("", response_model=List[dict])
def list_quotes(
    market_id: Optional[int] = Query(None),
    sports_event_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(models.Quote).join(models.MarketOutcome)
    if market_id:
        query = query.filter(models.MarketOutcome.market_id == market_id)
    if sports_event_id:
        query = query.join(models.Market, models.MarketOutcome.market).filter(
            models.Market.sports_event_id == sports_event_id
        )

    quotes = query.order_by(models.Quote.timestamp.desc()).limit(limit).all()
    results = []
    for q in quotes:
        mo = q.market_outcome
        m = mo.market
        results.append(
            {
                "quote_id": q.id,
                "timestamp": q.timestamp,
                "venue_id": m.venue_id,
                "market_id": m.id,
                "market_outcome_id": mo.id,
                "outcome_label": mo.label,
                "raw_price": float(q.raw_price) if q.raw_price is not None else None,
                "price_format": q.price_format,
                "share_price": float(q.share_price) if q.share_price is not None else None,
                "win_pnl": float(q.net_pnl_if_win_per_share) if q.net_pnl_if_win_per_share is not None else None,
                "lose_pnl": float(q.net_pnl_if_lose_per_share) if q.net_pnl_if_lose_per_share is not None else None,
            }
        )
    return results
