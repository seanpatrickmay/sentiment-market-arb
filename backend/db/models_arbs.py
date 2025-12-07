from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, Numeric, Boolean, ForeignKey

from .base import Base


class ArbitrageOpportunity(Base):
    __tablename__ = "arbitrage_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sports_event_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports_events.id"), nullable=False)
    market_type: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome_group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    num_outcomes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_stake: Mapped[Numeric] = mapped_column(Numeric(18, 8), nullable=False)
    worst_case_pnl: Mapped[Numeric] = mapped_column(Numeric(18, 8), nullable=False)
    best_case_pnl: Mapped[Numeric] = mapped_column(Numeric(18, 8), nullable=False)
    worst_case_roi: Mapped[Numeric] = mapped_column(Numeric(18, 8), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    detection_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    legs: Mapped[list["ArbitrageLeg"]] = relationship(
        "ArbitrageLeg", back_populates="opportunity", cascade="all, delete-orphan"
    )


class ArbitrageLeg(Base):
    __tablename__ = "arbitrage_legs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arbitrage_opportunity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arbitrage_opportunities.id"), nullable=False
    )

    venue_id: Mapped[str] = mapped_column(String(50), nullable=False)
    market_outcome_id: Mapped[int] = mapped_column(Integer, ForeignKey("market_outcomes.id"), nullable=False)
    outcome_label: Mapped[str] = mapped_column(String(50), nullable=False)

    stake_shares: Mapped[Numeric] = mapped_column(Numeric(18, 8), nullable=False)
    share_price: Mapped[Numeric] = mapped_column(Numeric(18, 8), nullable=False)
    win_pnl_per_share: Mapped[Numeric] = mapped_column(Numeric(18, 8), nullable=False)
    lose_pnl_per_share: Mapped[Numeric] = mapped_column(Numeric(18, 8), nullable=False)

    source_quote_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("quotes.id"), nullable=True)

    opportunity: Mapped["ArbitrageOpportunity"] = relationship("ArbitrageOpportunity", back_populates="legs")
