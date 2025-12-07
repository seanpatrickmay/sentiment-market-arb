from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from .base import Base


engine = create_engine(settings.database_url.unicode_string(), future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

