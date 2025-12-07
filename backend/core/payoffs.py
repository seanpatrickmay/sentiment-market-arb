from __future__ import annotations

from typing import Dict, Tuple


def compute_payoff_long(share_price: float, fee_model: Dict | None) -> Tuple[float, float]:
    """
    Compute per-share PnL for a long position (buying a share that pays 1 if the outcome occurs).

    Returns:
        (win_pnl, lose_pnl)
    """
    p = float(share_price)
    if fee_model is None:
        return 1.0 - p, -p

    fee_type = fee_model.get("type")

    if fee_type == "profit_commission":
        c = float(fee_model.get("commission_rate", 0.0))
        win_pnl = (1.0 - p) * (1.0 - c)
        lose_pnl = -p
        return win_pnl, lose_pnl

    if fee_type == "turnover_fee":
        g = float(fee_model.get("turnover_rate", 0.0))
        effective_cost = p * (1.0 + g)
        win_pnl = 1.0 - effective_cost
        lose_pnl = -effective_cost
        return win_pnl, lose_pnl

    if fee_type == "per_contract":
        trading_fee = float(fee_model.get("trading_fee", 0.0))
        settlement_fee = float(fee_model.get("settlement_fee", 0.0))
        effective_cost = p + trading_fee
        win_pnl = 1.0 - effective_cost - settlement_fee
        lose_pnl = -effective_cost
        return win_pnl, lose_pnl

    # Fallback: treat as no fees if unknown type
    return 1.0 - p, -p

