from fastapi import APIRouter

from ingestion.polymarket import ingest_polymarket_sports_markets
from ingestion.kalshi import ingest_kalshi_sports_markets
from ingestion.polymarket_quotes import ingest_polymarket_quotes
from ingestion.kalshi_quotes import ingest_kalshi_quotes


router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/polymarket", response_model=dict)
def trigger_polymarket_ingestion():
    count = ingest_polymarket_sports_markets()
    return {"source": "polymarket", "ingested_markets": count}


@router.post("/kalshi", response_model=dict)
def trigger_kalshi_ingestion():
    count = ingest_kalshi_sports_markets()
    return {"source": "kalshi", "ingested_markets": count}


@router.post("/polymarket/quotes", response_model=dict)
def trigger_polymarket_quote_ingestion():
    count = ingest_polymarket_quotes()
    return {"source": "polymarket", "ingested_quotes": count}


@router.post("/kalshi/quotes", response_model=dict)
def trigger_kalshi_quote_ingestion():
    count = ingest_kalshi_quotes()
    return {"source": "kalshi", "ingested_quotes": count}
