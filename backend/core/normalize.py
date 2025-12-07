from __future__ import annotations

from typing import Optional

from db import models
from core.odds import share_price_from_raw
from core.payoffs import compute_payoff_long


def normalize_quote_fields(quote: models.Quote, venue: models.Venue) -> None:
    """
    Given a Quote ORM object with raw_price and price_format set,
    compute normalized fields and assign them on the quote.
    """
    if quote.raw_price is None or quote.price_format is None:
        return

    share_price = share_price_from_raw(float(quote.raw_price), quote.price_format)
    quote.share_price = share_price
    # Convenience: decimal odds and implied prob
    quote.decimal_odds = 1.0 / share_price if share_price > 0 else None
    quote.implied_prob_raw = share_price

    win_pnl, lose_pnl = compute_payoff_long(share_price, venue.fee_model)
    quote.net_pnl_if_win_per_share = win_pnl
    quote.net_pnl_if_lose_per_share = lose_pnl
