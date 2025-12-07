from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from db import models, models_arbs


@dataclass
class Leg:
    venue_id: str
    market_outcome_id: int
    outcome_label: str
    share_price: float
    win_pnl: float
    lose_pnl: float
    quote_id: Optional[int]
    effective_cost: float


def _latest_quotes_for_outcomes(db: Session, outcome_ids: List[int]) -> Dict[int, models.Quote]:
    """
    Return latest quote per market_outcome_id from the `outcome_ids`.
    """
    if not outcome_ids:
        return {}
    subq = (
        db.query(
            models.Quote.market_outcome_id,
            func.max(models.Quote.timestamp).label("max_ts"),
        )
        .filter(models.Quote.market_outcome_id.in_(outcome_ids))
        .group_by(models.Quote.market_outcome_id)
        .subquery()
    )
    rows = (
        db.query(models.Quote)
        .join(
            subq,
            (models.Quote.market_outcome_id == subq.c.market_outcome_id)
            & (models.Quote.timestamp == subq.c.max_ts),
        )
        .all()
    )
    return {q.market_outcome_id: q for q in rows}


def _effective_cost(share_price: float, lose_pnl: float) -> float:
    # Worst-case cash outlay proxy
    return max(share_price, abs(lose_pnl))


def _select_best_leg(outcomes: List[models.MarketOutcome], quotes_map: Dict[int, models.Quote]) -> Optional[Leg]:
    best = None
    for mo in outcomes:
        q = quotes_map.get(mo.id)
        if not q or q.share_price is None or q.net_pnl_if_win_per_share is None or q.net_pnl_if_lose_per_share is None:
            continue
        share_price = float(q.share_price)
        win_pnl = float(q.net_pnl_if_win_per_share)
        lose_pnl = float(q.net_pnl_if_lose_per_share)
        eff_cost = _effective_cost(share_price, lose_pnl)
        leg = Leg(
            venue_id=mo.market.venue_id,
            market_outcome_id=mo.id,
            outcome_label=mo.label,
            share_price=share_price,
            win_pnl=win_pnl,
            lose_pnl=lose_pnl,
            quote_id=q.id,
            effective_cost=eff_cost,
        )
        if best is None or leg.effective_cost < best.effective_cost:
            best = leg
    return best


def _solve_2way(leg_a: Leg, leg_b: Leg) -> Optional[Tuple[float, float, float, float]]:
    """
    Return (x_a, x_b, pnl_a, pnl_b) if pure arb exists, else None.
    """
    win_a, lose_a = leg_a.win_pnl, leg_a.lose_pnl
    win_b, lose_b = leg_b.win_pnl, leg_b.lose_pnl

    denom = (win_b - lose_b)
    num = (win_a - lose_a)
    if denom <= 0 or num <= 0:
        return None
    r = num / denom  # x_b / x_a
    if r <= 0:
        return None

    pnl_a = win_a + r * lose_b
    pnl_b = lose_a + r * win_b
    if pnl_a <= 0 or pnl_b <= 0:
        return None

    return 1.0, r, pnl_a, pnl_b


def _total_stake(leg_a: Leg, leg_b: Leg, x_a: float, x_b: float) -> float:
    return x_a * leg_a.effective_cost + x_b * leg_b.effective_cost


def _total_stake_3(legs: List[Leg], stakes: List[float]) -> float:
    return sum(x * l.effective_cost for x, l in zip(stakes, legs))


def _check_equal_stakes_3way(legs: List[Leg]) -> Optional[Tuple[List[float], List[float]]]:
    """
    Simple heuristic: take stake 1 for each outcome, check PnL in all states.
    Returns (stakes, pnls) if all >= 0 and at least one > 0.
    """
    stakes = [1.0, 1.0, 1.0]
    pnls = []
    for i in range(3):
        pnl = 0.0
        for j, leg in enumerate(legs):
            if i == j:
                pnl += stakes[j] * leg.win_pnl
            else:
                pnl += stakes[j] * leg.lose_pnl
        pnls.append(pnl)
    if min(pnls) >= 0 and max(pnls) > 0:
        return stakes, pnls
    return None


def detect_arbs_for_event(db: Session, ev: models.SportsEvent) -> List[models_arbs.ArbitrageOpportunity]:
    """
    Detect pure back-all-outcomes arbs for a sports event.
    Currently handles 2-way and simple 3-way outcomes (home/away/draw, yes/no, over/under).
    """
    opportunities: List[models_arbs.ArbitrageOpportunity] = []

    markets = db.query(models.Market).filter(models.Market.sports_event_id == ev.id).all()
    if not markets:
        return opportunities

    # Collect outcomes and latest quotes per logical label
    all_outcomes: List[models.MarketOutcome] = []
    for m in markets:
        all_outcomes.extend(m.market_outcomes)
    outcome_ids = [mo.id for mo in all_outcomes]
    quotes_map = _latest_quotes_for_outcomes(db, outcome_ids)

    # Group by outcome label
    legs_by_label: Dict[str, Leg] = {}
    for label in ["home_win", "away_win", "draw", "over", "under", "yes", "no"]:
        related = [mo for mo in all_outcomes if mo.label == label]
        leg = _select_best_leg(related, quotes_map)
        if leg:
            legs_by_label[label] = leg

    # Helper to create opp
    def record_opp(market_type: str, outcome_group: str, legs: List[Leg], stakes: List[float], pnls: List[float]):
        total_stake = sum(stakes[i] * legs[i].effective_cost for i in range(len(legs)))
        worst = min(pnls)
        best = max(pnls)
        if total_stake <= 0:
            return
        roi = worst / total_stake
        if roi < settings.min_worst_case_roi or total_stake < settings.min_total_stake:
            return

        opp = models_arbs.ArbitrageOpportunity(
            sports_event_id=ev.id,
            market_type=market_type,
            outcome_group=outcome_group,
            detected_at=datetime.utcnow(),
            num_outcomes=len(legs),
            total_stake=total_stake,
            worst_case_pnl=worst,
            best_case_pnl=best,
            worst_case_roi=roi,
            status="open",
            detection_version="v1",
        )
        db.add(opp)
        db.flush()
        for leg, stake in zip(legs, stakes):
            db.add(
                models_arbs.ArbitrageLeg(
                    arbitrage_opportunity_id=opp.id,
                    venue_id=leg.venue_id,
                    market_outcome_id=leg.market_outcome_id,
                    outcome_label=leg.outcome_label,
                    stake_shares=stake,
                    share_price=leg.share_price,
                    win_pnl_per_share=leg.win_pnl,
                    lose_pnl_per_share=leg.lose_pnl,
                    source_quote_id=leg.quote_id,
                )
            )
        opportunities.append(opp)

    # 2-way: home/away
    if "home_win" in legs_by_label and "away_win" in legs_by_label:
        a = legs_by_label["home_win"]
        b = legs_by_label["away_win"]
        solved = _solve_2way(a, b)
        if solved:
            x_a, x_b, pnl_a, pnl_b = solved
            record_opp("moneyline", "home_away", [a, b], [x_a, x_b], [pnl_a, pnl_b])

    # 2-way yes/no
    if "yes" in legs_by_label and "no" in legs_by_label:
        a = legs_by_label["yes"]
        b = legs_by_label["no"]
        solved = _solve_2way(a, b)
        if solved:
            x_a, x_b, pnl_a, pnl_b = solved
            record_opp("binary", "yes_no", [a, b], [x_a, x_b], [pnl_a, pnl_b])

    # 2-way over/under
    if "over" in legs_by_label and "under" in legs_by_label:
        a = legs_by_label["over"]
        b = legs_by_label["under"]
        solved = _solve_2way(a, b)
        if solved:
            x_a, x_b, pnl_a, pnl_b = solved
            record_opp("total", "over_under", [a, b], [x_a, x_b], [pnl_a, pnl_b])

    # 3-way: home/draw/away (simple heuristic: equal stakes, all PnL >= 0)
    if all(k in legs_by_label for k in ("home_win", "draw", "away_win")):
        legs = [legs_by_label["home_win"], legs_by_label["draw"], legs_by_label["away_win"]]
        check = _check_equal_stakes_3way(legs)
        if check:
            stakes, pnls = check
            record_opp("moneyline", "home_draw_away", legs, stakes, pnls)

    return opportunities


def scan_all_events_for_arbs(db: Session) -> int:
    events = db.query(models.SportsEvent).all()
    total = 0
    for ev in events:
        ops = detect_arbs_for_event(db, ev)
        total += len(ops)
    db.commit()
    return total
