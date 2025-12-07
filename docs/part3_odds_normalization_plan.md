## Part 3 – Odds & Payoff Normalization (Sports, Pure Arbitrage)

Goal: for any bettable outcome on any venue, compute a standardized per‑unit payoff profile so the arbitrage engine can assemble portfolios that have non‑negative payoff in every outcome and positive payoff in at least one outcome, after accounting for venue fees.

Scope:
- Only mechanical payoffs; no fair‑value or probability modeling.
- Support prediction‑market style shares (Polymarket/Kalshi) and traditional sportsbook odds (decimal/American) for future venues.
- Include venue‑specific fee models in all payoff calculations.

---

### 3.1 Unifying odds formats into a share model

We unify all odds formats to a common 0/1 share representation:

> A “unit” is a claim that pays 1 unit of base currency if the outcome occurs, and 0 otherwise.

For each outcome on each venue, we compute a normalized share price `p ∈ (0, 1)`:
- `share_price = p` = current cost to buy 1 unit that pays 1 if the outcome occurs.

Ignoring fees:
- PnL per share if outcome happens: `+ (1 - p)`.
- PnL per share if outcome does not happen: `- p`.

We derive `p` from venue-specific odds formats:

- Prediction markets (`share_0_1`):
  - If the venue quotes a price directly in `[0, 1]` (e.g. Polymarket/Kalshi yes-share price):
    - `share_price = raw_price`.

- Decimal odds `O` (e.g. 2.50):
  - Stake `S` returns `S * O` if win, `0` if lose.
  - Equivalent share price:
    - `share_price = 1 / O`.

- American odds:
  - Convert to decimal `O` first:
    - If `+A`: `O = 1 + A / 100`.
    - If `-A`: `O = 1 + 100 / A`.
  - Then `share_price = 1 / O`.

Implementation utilities (e.g. `core/odds.py`):
- `decimal_to_share_price(decimal_odds) -> share_price`
- `american_to_decimal(american_odds) -> decimal_odds`
- `american_to_share_price(american_odds) -> share_price`
- `share_price_from_raw(raw_price, price_format) -> share_price`

All subsequent payoff logic operates on these normalized share prices.

---

### 3.2 Venue fee models

We encode each venue’s fee structure in `venues.fee_model` (JSON or equivalent), and use it to adjust raw payoffs.

Initial fee types:

- `no_fees`:
  - No adjustment:
    - If win: `PnL = 1 - p`.
    - If lose: `PnL = -p`.

- `profit_commission`:
  - Venue charges a fraction `c` of net profit on winning positions.
  - Per share (buying at price `p`):
    - Gross win PnL: `1 - p`.
    - Net win PnL: `(1 - p) * (1 - c)`.
    - Lose PnL: `-p`.

- `turnover_fee`:
  - Venue charges a fraction `g` of stake as a fee regardless of outcome.
  - Effective cost per share: `p * (1 + g)`.
  - Win PnL: `1 - p * (1 + g)`.
  - Lose PnL: `-p * (1 + g)`.

Future extensions (not required for initial implementation):
- Combine profit commission and turnover fees.
- Per-outcome or per-market fee overrides if needed.

Example `fee_model` JSONs:

- Prediction market with profit commission:
```json
{
  "type": "profit_commission",
  "commission_rate": 0.02
}
```

- Sportsbook with no fees:
```json
{
  "type": "no_fees"
}
```

---

### 3.3 Normalized payoff fields in `quotes`

The `quotes` table already stores raw odds/price snapshots per `market_outcome`. Part 3 adds normalized payoff metrics derived from share prices and venue fees.

For each `quotes` row (joined to `market_outcomes -> markets -> venues`):
- Inputs:
  - `raw_price`
  - `price_format` (`share_0_1`, `decimal`, `american`, etc.)
  - `venue.fee_model` (from `venues`).

Derived values:
- `share_price` (`p`):
  - `share_price = share_price_from_raw(raw_price, price_format)`.

- `net_pnl_if_win_per_share` (`win_pnl`):
  - Using `venue.fee_model` and `p`:
    - `no_fees`: `win_pnl = 1 - p`.
    - `profit_commission` with rate `c`: `win_pnl = (1 - p) * (1 - c)`.
    - `turnover_fee` with rate `g`: `win_pnl = 1 - p * (1 + g)`.

- `net_pnl_if_lose_per_share` (`lose_pnl`):
  - `no_fees`: `lose_pnl = -p`.
  - `profit_commission`: `lose_pnl = -p`.
  - `turnover_fee`: `lose_pnl = -p * (1 + g)`.

Optional convenience fields:
- `decimal_odds` – if we want to store a unified decimal odds representation.
- `implied_prob_raw` – purely mechanical implied probability (no de‑vig/overround modeling), e.g. `1 / decimal_odds` or approximately `p` for `share_0_1`.

Implementation helpers (e.g. `core/payoffs.py`):
- `normalize_quote(raw_price, price_format, venue_fee_model) -> NormalizedQuote` containing:
  - `share_price`
  - `net_pnl_if_win_per_share`
  - `net_pnl_if_lose_per_share`
  - Optional `decimal_odds`, `implied_prob_raw`.

Storage vs. computation:
- For performance, we may persist `share_price`, `net_pnl_if_win_per_share`, and `net_pnl_if_lose_per_share` in `quotes` when we ingest/update quotes.
- Alternatively, compute them on the fly in the pure arb engine via helper functions.

---

### 3.4 Back vs lay positions (extension)

Initial focus:
- Model only **long/back** positions (buying 1 share of an outcome) and construct arbitrage portfolios using combinations of long positions on different venues/outcomes.

Later extension for true lay/short positions:
- A lay (short) position on an outcome with share price `p` is economically the mirror of a long:
  - You receive `p` now.
  - If the outcome happens, you must pay 1.
  - Per share:
    - If outcome happens: `PnL = p - 1`.
    - If outcome does not happen: `PnL = +p`.
- With fees, adjust these similarly using `venue.fee_model`.
- Implementation could treat a short position as:
  - PnL = `- win_pnl` when outcome occurs, `- lose_pnl` when it does not, where `win_pnl`/`lose_pnl` are from the long position.

This extension is optional and can be added when/if the execution model requires explicit lay positions.

---

### 3.5 Example: Miami Heat @ Orlando Magic moneyline

For a concrete example, consider `sports_event_id = 10` (Miami Heat @ Orlando Magic), moneyline markets on two venues.

Assume snapshot prices:
- Polymarket (profit commission `c_PM = 0.02`):
  - Heat win share: `raw_price = 0.55`, `price_format = 'share_0_1'`.
  - Magic win share: `raw_price = 0.50`, `price_format = 'share_0_1'`.

- Kalshi (no fees for this example):
  - Heat win share: `raw_price = 0.60`, `price_format = 'share_0_1'`.
  - Magic win share: `raw_price = 0.48`, `price_format = 'share_0_1'`.

Normalized payoffs:
- Polymarket, Heat win:
  - `p = 0.55`.
  - If Heat wins:
    - Gross PnL: `1 - 0.55 = 0.45`.
    - Net PnL: `0.45 * (1 - 0.02) = 0.441`.
  - If Heat loses:
    - `PnL = -0.55`.

- Kalshi, Magic win:
  - `p = 0.48`.
  - If Magic wins:
    - `PnL = 1 - 0.48 = 0.52`.
  - If Magic loses:
    - `PnL = -0.48`.

The pure arbitrage engine (Part 4) will later use these `win_pnl` and `lose_pnl` per share as inputs to solve for how many shares of each outcome/venue to buy to construct risk‑free, covered portfolios.

Part 3’s responsibility is only to ensure that each leg has a correct, venue‑adjusted payoff profile expressed in a common unit.

---

### 3.6 Code and schema placement

Schema:
- `quotes` gains or uses fields for normalized metrics:
  - `share_price` (normalized).
  - Optionally `decimal_odds`, `implied_prob_raw`.
  - Optionally `net_pnl_if_win_per_share`, `net_pnl_if_lose_per_share`.

Code modules:
- `core/odds.py`:
  - Odds format conversions and `share_price_from_raw`.
- `core/payoffs.py`:
  - Functions that, given `share_price` and `venue.fee_model`, compute `win_pnl` and `lose_pnl`.
- `core/normalize.py` (or similar helper module):
  - Provides a consolidated `normalize_quote` interface that the arb engine can consume.

---

### 3.7 Definition of done for Part 3

Part 3 is complete when:
- For any `market_outcome` and raw quote from any configured venue:
  - We can derive a normalized `share_price ∈ (0, 1)` using odds conversion utilities.
  - Using `venue.fee_model`, we can compute:
    - `net_pnl_if_win_per_share`.
    - `net_pnl_if_lose_per_share`.
  - These calculations are accessible via a clear Python API and (where appropriate) persisted in `quotes`.
- On a small test set (e.g. synthetic prices for Miami Heat @ Orlando Magic), normalized payoffs match the venue’s economic rules, including fees.

With Part 3 in place, the pure arbitrage engine (Part 4) can treat each leg as “buy N shares with known per‑share PnL in each state” and focus solely on solving for stake sizes that produce risk‑free payoffs across venues and outcomes.

