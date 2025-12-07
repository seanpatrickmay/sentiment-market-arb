from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from db import models
from core.normalize import normalize_quote_fields


def ensure_outcomes_for_market(market: models.Market) -> None:
    """
    Ensure market_outcomes exist for a market.
    For moneyline with parsed teams, create home/away outcomes.
    Otherwise, create generic yes/no outcomes.
    """
    if market.market_outcomes:
        return

    outcomes = []
    if market.market_type == "moneyline" and market.parsed_home_team and market.parsed_away_team:
        outcomes.append(
            models.MarketOutcome(
                market_id=market.id,
                label="home_win",
                display_name=market.parsed_home_team,
                is_exhaustive_group=True,
            )
        )
        outcomes.append(
            models.MarketOutcome(
                market_id=market.id,
                label="away_win",
                display_name=market.parsed_away_team,
                is_exhaustive_group=True,
            )
        )
    else:
        outcomes.append(
            models.MarketOutcome(
                market_id=market.id,
                label="yes",
                display_name="Yes",
                is_exhaustive_group=True,
            )
        )
        outcomes.append(
            models.MarketOutcome(
                market_id=market.id,
                label="no",
                display_name="No",
                is_exhaustive_group=True,
            )
        )

    for o in outcomes:
        market.market_outcomes.append(o)


def create_quotes_for_market(
    db: Session,
    market: models.Market,
    yes_price: Optional[float],
    price_format: str,
    source: str,
    timestamp: Optional[datetime] = None,
) -> int:
    """
    Given a market and a price for the 'yes' side, create Quote rows for
    both outcomes (second outcome uses 1 - yes_price) assuming a binary partition.
    Returns number of quotes created.
    """
    if yes_price is None:
        return 0

    ensure_outcomes_for_market(market)
    db.flush()  # ensure outcomes have ids
    if not market.market_outcomes:
        return 0

    # Heuristic: first outcome gets the given price, second gets complement.
    created = 0
    price_yes = float(yes_price)
    price_no = max(0.0, min(1.0, 1.0 - price_yes))

    venue = market.venue
    ts = timestamp or datetime.utcnow()

    outcomes = sorted(market.market_outcomes, key=lambda mo: mo.id or 0)
    prices = [price_yes, price_no]

    for outcome, p in zip(outcomes[:2], prices):
        quote = models.Quote(
            market_outcome_id=outcome.id,
            timestamp=ts,
            raw_price=p,
            price_format=price_format,
            source=source,
        )
        normalize_quote_fields(quote, venue)
        db.add(quote)
        created += 1

    return created
