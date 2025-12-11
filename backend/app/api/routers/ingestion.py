import logging

from fastapi import APIRouter, HTTPException

from ingestion.polymarket import ingest_polymarket_sports_markets
from ingestion.kalshi import ingest_kalshi_sports_markets
from ingestion.kalshi_events import ingest_kalshi_events
from ingestion.polymarket_quotes import ingest_polymarket_quotes
from ingestion.kalshi_quotes import ingest_kalshi_quotes


router = APIRouter(prefix="/ingest", tags=["ingestion"], redirect_slashes=False)

logger = logging.getLogger(__name__)


@router.post("/polymarket", response_model=dict)
def trigger_polymarket_ingestion():
    try:
        count = ingest_polymarket_sports_markets()
        return {"source": "polymarket", "ingested_markets": count}
    except Exception as e:
        logger.exception("Polymarket ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kalshi", response_model=dict)
def trigger_kalshi_ingestion():
    try:
        count = ingest_kalshi_sports_markets()
        return {"source": "kalshi", "ingested_markets": count}
    except Exception as e:
        logger.exception("Kalshi ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kalshi/events", response_model=dict)
def trigger_kalshi_event_ingestion():
    try:
        count = ingest_kalshi_events()
        return {"source": "kalshi", "ingested_events": count}
    except Exception as e:
        logger.exception("Kalshi event ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polymarket/quotes", response_model=dict)
def trigger_polymarket_quote_ingestion():
    try:
        count = ingest_polymarket_quotes()
        return {"source": "polymarket", "ingested_quotes": count}
    except Exception as e:
        logger.exception("Polymarket quote ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kalshi/quotes", response_model=dict)
def trigger_kalshi_quote_ingestion():
    try:
        count = ingest_kalshi_quotes()
        return {"source": "kalshi", "ingested_quotes": count}
    except Exception as e:
        logger.exception("Kalshi quote ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))
