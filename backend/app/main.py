import logging
import os

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.health import router as health_router
from app.api.routers.ingestion import router as ingestion_router
from app.api.routers.mapping_candidates import router as mapping_candidates_router
from app.api.routers.sports_events import router as sports_events_router
from app.api.routers.markets import router as markets_router
from app.api.routers.quotes import router as quotes_router
from app.api.routers.arbs import router as arbs_router
from app.config import settings


logger = logging.getLogger(__name__)


app = FastAPI(title="Sports Pure Arb Backend", version="0.1.0")

# CORS for local dev (frontend on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def run_migrations() -> None:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    alembic_cfg_path = os.path.join(base_dir, "alembic.ini")
    alembic_cfg = Config(alembic_cfg_path)
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url.unicode_string())
    logger.info("Running database migrations at startup...")
    command.upgrade(alembic_cfg, "head")

app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(sports_events_router)
app.include_router(markets_router)
app.include_router(mapping_candidates_router)
app.include_router(quotes_router)
app.include_router(arbs_router)
