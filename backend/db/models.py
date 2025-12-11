from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base
from .models_arbs import ArbitrageOpportunity, ArbitrageLeg  # noqa: F401


SPORTS = ("MLB", "NFL", "NBA", "NHL")


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    fee_model: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    markets: Mapped[list["Market"]] = relationship("Market", back_populates="venue")


class SportsEvent(Base):
    __tablename__ = "sports_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sport: Mapped[str] = mapped_column(String(20), nullable=False)
    league: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    home_team: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False)
    event_start_time_utc: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="scheduled")
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    external_event_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    markets: Mapped[list["Market"]] = relationship("Market", back_populates="sports_event")
    event_links: Mapped[list["EventMarketLink"]] = relationship(
        "EventMarketLink", back_populates="sports_event", cascade="all, delete-orphan"
    )


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venue_id: Mapped[str] = mapped_column(String(50), ForeignKey("venues.id"), nullable=False)
    sports_event_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sports_events.id"), nullable=True)

    venue_market_key: Mapped[str] = mapped_column(String(100), nullable=False)
    market_type: Mapped[str] = mapped_column(String(50), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    listing_time_utc: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expiration_time_utc: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    settlement_time_utc: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")

    parsed_sport: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    parsed_league: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parsed_home_team: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parsed_away_team: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parsed_start_time_hint: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    parsed_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    venue: Mapped["Venue"] = relationship("Venue", back_populates="markets")
    sports_event: Mapped[Optional["SportsEvent"]] = relationship("SportsEvent", back_populates="markets")
    market_outcomes: Mapped[list["MarketOutcome"]] = relationship(
        "MarketOutcome", back_populates="market", cascade="all, delete-orphan"
    )
    mapping_candidates: Mapped[list["MappingCandidate"]] = relationship(
        "MappingCandidate", back_populates="market", cascade="all, delete-orphan"
    )
    event_links: Mapped[list["EventMarketLink"]] = relationship(
        "EventMarketLink", back_populates="market", cascade="all, delete-orphan"
    )


class MarketOutcome(Base):
    __tablename__ = "market_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(Integer, ForeignKey("markets.id"), nullable=False)

    label: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    line: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    side: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    group_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_exhaustive_group: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    settlement_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    market: Mapped["Market"] = relationship("Market", back_populates="market_outcomes")
    quotes: Mapped[list["Quote"]] = relationship(
        "Quote", back_populates="market_outcome", cascade="all, delete-orphan"
    )


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_outcome_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_outcomes.id"), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    raw_price: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    price_format: Mapped[str] = mapped_column(String(20), nullable=False)

    bid_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    ask_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    share_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    net_pnl_if_win_per_share: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    net_pnl_if_lose_per_share: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)

    decimal_odds: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    implied_prob_raw: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    market_outcome: Mapped["MarketOutcome"] = relationship("MarketOutcome", back_populates="quotes")


class EventMarketLink(Base):
    __tablename__ = "event_market_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sports_event_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_events.id"), nullable=False)
    market_id: Mapped[int] = mapped_column(Integer, ForeignKey("markets.id"), nullable=False)

    link_type: Mapped[str] = mapped_column(String(50), nullable=False, default="primary")
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sports_event: Mapped["SportsEvent"] = relationship("SportsEvent", back_populates="event_links")
    market: Mapped["Market"] = relationship("Market", back_populates="event_links")


class MappingCandidate(Base):
    __tablename__ = "mapping_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(Integer, ForeignKey("markets.id"), nullable=False)
    candidate_sports_event_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sports_events.id"), nullable=True)

    confidence_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    features_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    market: Mapped["Market"] = relationship("Market", back_populates="mapping_candidates")
    candidate_sports_event: Mapped[Optional["SportsEvent"]] = relationship("SportsEvent")
