from __future__ import annotations


def american_to_decimal(american_odds: float) -> float:
    """
    Convert American odds to decimal odds.
    +150 -> 2.5
    -200 -> 1.5
    """
    if american_odds == 0:
        raise ValueError("American odds cannot be zero")
    if american_odds > 0:
        return 1.0 + american_odds / 100.0
    else:
        return 1.0 + 100.0 / abs(american_odds)


def decimal_to_share_price(decimal_odds: float) -> float:
    """
    Convert decimal odds to an equivalent share price in [0, 1].
    """
    if decimal_odds <= 0:
        raise ValueError("Decimal odds must be positive")
    return 1.0 / decimal_odds


def american_to_share_price(american_odds: float) -> float:
    return decimal_to_share_price(american_to_decimal(american_odds))


def share_price_from_raw(raw_price: float, price_format: str) -> float:
    """
    Normalize a raw price into a share price in [0, 1].
    Supported formats:
      - 'share_0_1' : already in [0, 1]
      - 'decimal'   : decimal odds
      - 'american'  : American odds
    """
    fmt = price_format.lower()
    if fmt == "share_0_1":
        return float(raw_price)
    if fmt == "decimal":
        return decimal_to_share_price(float(raw_price))
    if fmt == "american":
        return american_to_share_price(float(raw_price))
    raise ValueError(f"Unsupported price_format: {price_format}")

