from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from db import models_arbs, models
from core.arb_engine import scan_all_events_for_arbs


router = APIRouter(prefix="/arbs", tags=["arbitrage"])


@router.post("/scan", response_model=dict)
def scan_for_arbitrage(db: Session = Depends(get_db)):
    created = scan_all_events_for_arbs(db)
    return {"detected_opportunities": created}


@router.get("/", response_model=List[dict])
def list_arbs(
    min_roi: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(models_arbs.ArbitrageOpportunity).order_by(models_arbs.ArbitrageOpportunity.detected_at.desc())
    if min_roi is not None:
        query = query.filter(models_arbs.ArbitrageOpportunity.worst_case_roi >= min_roi)
    ops = query.limit(limit).all()
    results = []
    for op in ops:
        results.append(
            {
                "id": op.id,
                "sports_event_id": op.sports_event_id,
                "market_type": op.market_type,
                "outcome_group": op.outcome_group,
                "detected_at": op.detected_at,
                "num_outcomes": op.num_outcomes,
                "total_stake": float(op.total_stake),
                "worst_case_pnl": float(op.worst_case_pnl),
                "best_case_pnl": float(op.best_case_pnl),
                "worst_case_roi": float(op.worst_case_roi),
                "status": op.status,
            }
        )
    return results


@router.get("/{arb_id}", response_model=dict)
def get_arb(arb_id: int, db: Session = Depends(get_db)):
    op = db.query(models_arbs.ArbitrageOpportunity).filter(models_arbs.ArbitrageOpportunity.id == arb_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Arbitrage opportunity not found")
    legs = db.query(models_arbs.ArbitrageLeg).filter(models_arbs.ArbitrageLeg.arbitrage_opportunity_id == op.id).all()
    legs_out = []
    for l in legs:
        legs_out.append(
            {
                "venue_id": l.venue_id,
                "market_outcome_id": l.market_outcome_id,
                "outcome_label": l.outcome_label,
                "stake_shares": float(l.stake_shares),
                "share_price": float(l.share_price),
                "win_pnl_per_share": float(l.win_pnl_per_share),
                "lose_pnl_per_share": float(l.lose_pnl_per_share),
                "source_quote_id": l.source_quote_id,
            }
        )
    return {
        "id": op.id,
        "sports_event_id": op.sports_event_id,
        "market_type": op.market_type,
        "outcome_group": op.outcome_group,
        "detected_at": op.detected_at,
        "num_outcomes": op.num_outcomes,
        "total_stake": float(op.total_stake),
        "worst_case_pnl": float(op.worst_case_pnl),
        "best_case_pnl": float(op.best_case_pnl),
        "worst_case_roi": float(op.worst_case_roi),
        "status": op.status,
        "legs": legs_out,
    }

