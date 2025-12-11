from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from db import models
from mapping.engine import bulk_suggest_for_unmapped_markets


router = APIRouter(prefix="/mapping-candidates", tags=["mapping"], redirect_slashes=False)


@router.get("", response_model=List[dict])
def list_mapping_candidates(
    status: str = Query("pending"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(models.MappingCandidate).order_by(models.MappingCandidate.confidence_score.desc())
    if status:
        query = query.filter(models.MappingCandidate.status == status)
    candidates = query.limit(limit).all()

    results = []
    for c in candidates:
        market = c.market
        ev = c.candidate_sports_event
        results.append(
            {
                "id": c.id,
                "market_id": c.market_id,
                "candidate_sports_event_id": c.candidate_sports_event_id,
                "confidence_score": float(c.confidence_score),
                "status": c.status,
                "market": {
                    "id": market.id,
                    "venue_id": market.venue_id,
                    "question_text": market.question_text,
                    "parsed_sport": market.parsed_sport,
                    "parsed_home_team": market.parsed_home_team,
                    "parsed_away_team": market.parsed_away_team,
                },
                "sports_event": {
                    "id": ev.id if ev else None,
                    "sport": ev.sport if ev else None,
                    "home_team": ev.home_team if ev else None,
                    "away_team": ev.away_team if ev else None,
                    "event_start_time_utc": ev.event_start_time_utc if ev else None,
                },
                "features": c.features_json or {},
            }
        )
    return results


@router.post("/suggest", response_model=dict)
def suggest_for_unmapped(limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    created = bulk_suggest_for_unmapped_markets(db, limit=limit)
    db.commit()
    return {"created_candidates": created}


@router.post("/{candidate_id}/accept", response_model=dict)
def accept_mapping_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(models.MappingCandidate).filter(models.MappingCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Mapping candidate not found")
    if candidate.status == "accepted":
        return {"status": "already_accepted"}

    market = candidate.market
    event = candidate.candidate_sports_event
    if not event:
        raise HTTPException(status_code=400, detail="Candidate has no target sports event")

    link = (
        db.query(models.EventMarketLink)
        .filter(
            models.EventMarketLink.market_id == market.id,
            models.EventMarketLink.sports_event_id == event.id,
        )
        .first()
    )
    if not link:
        link = models.EventMarketLink(
            market_id=market.id,
            sports_event_id=event.id,
            link_type="primary",
            confirmed_by_user=True,
            source="manual",
        )
        db.add(link)
    else:
        link.confirmed_by_user = True
        link.source = "manual"

    market.sports_event_id = event.id

    candidate.status = "accepted"
    candidate.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(market)

    return {
        "status": "accepted",
        "market_id": market.id,
        "sports_event_id": event.id,
    }


@router.post("/{candidate_id}/reject", response_model=dict)
def reject_mapping_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(models.MappingCandidate).filter(models.MappingCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Mapping candidate not found")

    candidate.status = "rejected"
    candidate.reviewed_at = datetime.utcnow()
    db.commit()

    return {"status": "rejected", "candidate_id": candidate_id}
