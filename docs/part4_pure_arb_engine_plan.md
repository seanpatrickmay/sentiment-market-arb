## Part 4 – Pure Arbitrage Engine (Sports)

Goal: given normalized odds/payoffs (Part 3) and mapped sports events/markets (Parts 1–2), systematically detect and parameterize pure arbitrage portfolios across venues. A pure arbitrage portfolio has non-negative payoff in every outcome and strictly positive payoff in at least one outcome, after fees.

Scope:
- Only structural arbitrage; no statistical or fair-value modeling.
- Initial focus on:
  - 2-way markets (e.g. moneyline without draw, over/under at a fixed line).
  - 3-way markets (e.g. moneyline with draw).
- Only long/back positions (buying outcome shares) in v1.

---

### 4.1 Arbitrage types supported (v1)

We focus on "back-all-outcomes" arbitrage: buy (long) positions on all mutually exclusive outcomes of a market, potentially across multiple venues, so that:
- The combined payoff is ≥ 0 in every global outcome.
- At least one global outcome yields > 0 payoff.

Supported cases:
- 2-way markets:
  - Examples: "draw no bet" moneyline (`home_win`, `away_win`), totals (`over`, `under`).
  - Classical no-fee condition: if share prices are `p1`, `p2`, then buying 1 share of each costs `p1 + p2` and pays `1` in any outcome; arbitrage if `p1 + p2 < 1`.

- 3-way markets:
  - Examples: moneyline with draw (`home_win`, `draw`, `away_win`).
  - Classical no-fee condition: if share prices are `p_home`, `p_draw`, `p_away`, then buying 1 share of each costs `p_home + p_draw + p_away` and pays `1` in any outcome; arbitrage if the sum < 1.

Future extensions (not required in v1):
- Explicit lay/short positions.
- Cross-market arbs (e.g. alt lines, correlated totals/spreads).

---

### 4.2 Arb market view and data assembly

For a given `sports_event` and `market_type`, we build an in-memory representation for the arb engine.

**4.2.1 ArbMarket structure**

For each `(sports_event_id, market_type, outcome_group)`:
- `ArbMarket`:
  - `sports_event_id`
  - `market_type` – e.g. `moneyline`, `total`.
  - `outcome_group` – label grouping markets for that event and type.
  - `outcomes` – list of `ArbOutcome`:
    - `label` – logical outcome label (`home_win`, `away_win`, `draw`, `over`, `under`).
    - `legs` – list of `ArbLegCandidate` from different venues.

**4.2.2 ArbLegCandidate structure**

Each `ArbLegCandidate` represents one venue's quote on a specific logical outcome:
- `venue_id`
- `market_outcome_id`
- Latest normalized quote (from Part 3), including:
  - `share_price` (`p`)
  - `net_pnl_if_win_per_share` (`win_pnl`)
  - `net_pnl_if_lose_per_share` (`lose_pnl`)
- Optional liquidity info:
  - `max_size` – the maximum number of shares we assume can be bought at/near the quoted price.
  - `orderbook_depth` or similar (future).

The arb engine operates only on these normalized legs and does not re-parse raw venue odds.

---

### 4.3 Selecting the best leg per outcome

For back-all-outcomes portfolios using only long positions, using more than one venue for the same logical outcome is usually dominated by choosing the best venue.

For each logical outcome:
- Compute an "effective worst-case cost" per share for each leg, e.g.:
  - `effective_cost = max(-win_pnl, -lose_pnl)` (worst-case loss per share), or
  - Simplified: fee-adjusted share price (e.g. `p` or `p * (1 + turnover_fee)`).
- Select the **leg with minimal effective_cost** (subject to `max_size`/liquidity constraints) as the **best leg** for that outcome.

After this step, each `ArbMarket` has at most one chosen leg per logical outcome for the back-all-outcomes optimization.

---

### 4.4 Core algorithm for 2-way arbitrage

Consider an `ArbMarket` with 2 outcomes A and B (e.g. `home_win` and `away_win`), with chosen best legs:

- Outcome A leg:
  - `win_pnl = win_A` – per-share PnL if outcome A occurs.
  - `lose_pnl = lose_A` – per-share PnL if outcome B occurs.

- Outcome B leg:
  - `win_pnl = win_B` – per-share PnL if B occurs.
  - `lose_pnl = lose_B` – per-share PnL if A occurs.

Let `x_A`, `x_B ≥ 0` be the number of shares bought in each leg.

Payoff by global outcome:
- If A occurs:
  - `PnL_A = x_A * win_A + x_B * lose_B`.
- If B occurs:
  - `PnL_B = x_A * lose_A + x_B * win_B`.

**Pure arb condition:**
- Need `PnL_A ≥ 0` and `PnL_B ≥ 0`, with at least one strictly > 0.

**No-fee special case (sanity filter):**
- Under simple share pricing and no fees:
  - `win_A = 1 - p_A`, `lose_A = -p_A`, etc.
  - Buying 1 share of each gives:
    - Cost: `p_A + p_B`.
    - Payoff: `1` in either outcome.
    - PnL: `1 - (p_A + p_B)`.
  - Condition: `p_A + p_B < 1`.
  - This is a fast filter before more detailed checks.

**With fees (general case):**

We use the full payoffs from Part 3:
- Step 1: Find stake ratio that equalizes PnL across outcomes (risk boundary):
  - Set `PnL_A = PnL_B = t` for some t.
  - Subtract:
    - `x_A * (win_A - lose_A) = x_B * (win_B - lose_B)`.
    - `x_B / x_A = r = (win_A - lose_A) / (win_B - lose_B)`.
  - Require `r > 0` (stakes non-negative).

- Step 2: Check PnL at this ratio:
  - Express PnL in, say, state A:
    - `PnL_A(x_A) = x_A * (win_A + r * lose_B)`.
  - If `win_A + r * lose_B > 0`, taking any `x_A > 0` yields `PnL_A > 0` and (by construction) `PnL_B > 0` → pure arb exists with equalized PnL.
  - If `win_A + r * lose_B ≤ 0`, no equalized-positive PnL solution.

- Step 3 (optional refinement):
  - In some cases, a portfolio may exist with `PnL_A ≥ 0`, `PnL_B ≥ 0` where PnLs are not equal.
  - For v1, we can either:
    - Consider a small search around `r` (e.g. slightly higher/lower stake ratios), or
    - Accept that if equalized PnL cannot be positive, we rarely get significant arbitrage from skewed stakes under realistic fee models.

Outputs when an arb is found:
- Stake sizes:
  - `x_A`, `x_B` (number of shares).
- Per-state PnLs:
  - `PnL_A`, `PnL_B`.
- Worst-case PnL:
  - `worst_case_pnl = min(PnL_A, PnL_B)`.
- Total stake outlay (approximate):
  - `total_stake ≈ x_A * effective_cost_A + x_B * effective_cost_B`.
- Worst-case ROI:
  - `worst_case_roi = worst_case_pnl / total_stake`.

We enforce minimum thresholds on total stake and `worst_case_roi` to avoid tiny, noisy opportunities.

---

### 4.5 Core algorithm for 3-way arbitrage

For a 3-way `ArbMarket` (e.g. `home_win`, `draw`, `away_win`), with chosen best legs:

For each outcome i = 1,2,3:
- `win_i` – per-share PnL if outcome i occurs.
- `lose_i` – per-share PnL if any other outcome occurs.

Stakes: `x1`, `x2`, `x3 ≥ 0`.

Payoff by global outcome:
- If outcome 1 occurs:
  - `PnL_1 = x1 * win_1 + x2 * lose_2 + x3 * lose_3`.
- If outcome 2 occurs:
  - `PnL_2 = x1 * lose_1 + x2 * win_2 + x3 * lose_3`.
- If outcome 3 occurs:
  - `PnL_3 = x1 * lose_1 + x2 * lose_2 + x3 * win_3`.

Pure arb condition:
- Find `x1, x2, x3 ≥ 0` such that:
  - `PnL_1 ≥ 0`, `PnL_2 ≥ 0`, `PnL_3 ≥ 0`.
  - At least one PnL strictly > 0.

**No-fee special case (sanity filter):**
- Under simple share pricing and no fees:
  - Share prices `p1`, `p2`, `p3`.
  - Buy 1 share of each:
    - Cost: `p1 + p2 + p3`.
    - Payoff: `1` in any outcome.
    - PnL: `1 - (p1 + p2 + p3)`.
  - Arb if `p1 + p2 + p3 < 1`.

**With general payoffs: small linear feasibility problem**

We consider the inequalities:
- `PnL_1(x) ≥ 0`, `PnL_2(x) ≥ 0`, `PnL_3(x) ≥ 0`, with `x ≥ 0`.

Given the low dimension (3 variables, 3 constraints), practical options:
- Filter first: if the sum of effective costs (fee-adjusted share prices) ≥ 1, skip as "very unlikely" arb.
- For candidates (sum < 1), solve a small LP:
  - Either use a lightweight LP solver, or
  - Implement a custom enumerator:
    - Analyze cases where one or more constraints bind (PnL = 0), solve for `x`, verify all PnLs ≥ 0.

Outputs mirror the 2-way case:
- Stake sizes per outcome (`x1`, `x2`, `x3`).
- PnL in each global outcome (`PnL_1`, `PnL_2`, `PnL_3`).
- `worst_case_pnl`, `best_case_pnl`, and `worst_case_roi`.

---

### 4.6 Storage of arbitrage opportunities

We log detected arbs so they can be inspected, backtested, and optionally executed later.

**4.6.1 `arbitrage_opportunities`**

Fields:
- `id`
- `sports_event_id`
- `market_type`
- `outcome_group`
- `detected_at` – timestamp.
- `num_outcomes` – 2 or 3.
- `total_stake` – sum of stake outlay for all legs at detection scale.
- `worst_case_pnl`
- `best_case_pnl`
- `worst_case_roi` – `worst_case_pnl / total_stake`.
- `status` – `open`, `expired`, `executed`, `ignored`.
- Optional: `detection_method_version`, `notes`.

**4.6.2 `arbitrage_legs`**

Fields:
- `id`
- `arbitrage_opportunity_id` → `arbitrage_opportunities.id`.
- `venue_id`
- `market_outcome_id`
- `outcome_label` – e.g. `home_win`, `away_win`, `draw`, `over`, `under`.
- `stake_shares` – number of shares to buy.
- `share_price` – share price at detection time.
- `win_pnl_per_share` – from normalization.
- `lose_pnl_per_share` – from normalization.
- Optional: `max_liquidity_shares`, `direction` (`long` for v1).

This schema lets us reconstruct portfolios and compute realized or hypothetical PnL later.

---

### 4.7 Arbitrage scanning job

We implement a periodic arb scanning process that:

1. Iterates over candidate markets:
   - For each `sports_event` with multiple venues mapped:
     - For each `market_type` and `outcome_group`:
       - Build an `ArbMarket` using latest quotes and normalized payoffs.
       - Only consider markets where the set of outcomes forms a complete partition (2-way or 3-way) per the `market_outcomes` metadata.

2. For each `ArbMarket`:
   - Select best leg per outcome.
   - Apply fast filters (e.g. sum of effective share prices < 1).
   - Run the detailed 2-way or 3-way algorithm to verify existence of a pure arb and compute stakes/PnL.

3. If an opportunity is found and passes thresholds:
   - Minimum `total_stake` requirement.
   - Minimum `worst_case_roi` requirement.
   - Insert into `arbitrage_opportunities` and `arbitrage_legs`.

4. Deduplication (optional, but recommended):
   - Avoid logging essentially identical opportunities repeatedly over short intervals:
     - Use a hash or fingerprint of `(sports_event_id, market_type, outcome_group, legs and their prices)` and skip duplicates within a time window.

This scanner runs independently of any execution logic and can be reused for backtesting by replaying historical quotes.

---

### 4.8 API for consumers (backend & frontend)

We expose arbitrage opportunities via HTTP for monitoring and future UI:

- `GET /arbs`
  - Query params: `min_roi`, `sport`, `venue`, `market_type`, `limit`, etc.
  - Returns a list of recent `arbitrage_opportunities` with summary fields.

- `GET /arbs/{id}`
  - Returns full detail of a specific opportunity:
    - Associated `sports_event` info.
    - All legs (`venue`, `market_outcome`, `stake_shares`, `share_price`, per-share PnL).
    - Per-outcome PnL summary.

- `POST /debug/arb-check` (optional, for research/debugging):
  - Accepts a payload representing an `ArbMarket` snapshot.
  - Returns whether a pure arb exists under the engine's rules and, if so, the calculated stakes and PnL per global outcome.

These endpoints form the primary interface for monitoring arbs and will be the basis for any frontend visualization.

---

### 4.9 Definition of done for Part 4

Part 4 is complete when:
- For any `sports_event` with mapped markets and normalized quotes:
  - The arb engine can:
    - Build an `ArbMarket` representation (outcomes and candidate legs).
    - Select best legs per outcome.
    - Detect pure back-all-outcomes arbitrage opportunities for 2-way and 3-way markets, considering fees.
    - Compute stake sizes and PnL in each global outcome, including worst-case ROI.

- Detected opportunities are:
  - Persisted in `arbitrage_opportunities` and `arbitrage_legs`.
  - Queryable via `GET /arbs` and `GET /arbs/{id}`.

- On a synthetic test scenario (e.g. Miami Heat @ Orlando Magic with hand-crafted prices on two venues):
  - Classical arbs (sum of implied probabilities < 1) are correctly identified, with PnL matching manual calculations.
  - Non-arb scenarios (sum ≥ 1) are correctly rejected.
  - When simple fee models are turned on, PnL remains consistent with the fee assumptions defined in Part 3.

With Part 4 in place, the system can systematically identify pure sports arbitrage opportunities across venues, setting the stage for Part 5 (simulation & PnL accounting) and Part 6 (optional live execution).

