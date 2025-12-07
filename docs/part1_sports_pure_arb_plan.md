## Part 1 – Domain & Data Model (Sports, Pure Arbitrage)

Goal: define the core schema and concepts so we can:
- Represent sports events and markets consistently across venues.
- Attach venue-specific markets to canonical events via a mapping pipeline.
- Store odds/quotes in a way that supports pure, covered-outcome arbitrage.
- Keep everything friendly to a future FastAPI backend, Postgres, Docker, and a frontend.

Scope constraints:
- Only sports betting events for now.
- Only pure arbitrage: portfolios that have non-negative payoff in every outcome and positive payoff in at least one outcome, after fees.
- Venues: start with Polymarket and Kalshi, but keep the design extensible to other books/exchanges.

---

### 1.1 Core entities

We model the domain around five main concepts:

- `venues` – platforms that offer markets (Polymarket, Kalshi, future books).
- `sports_events` – canonical games/matches, independent of venue.
- `markets` – venue-specific contracts tied to a sports event.
- `market_outcomes` – individual outcomes within each market.
- `quotes` – time-stamped odds/prices for each outcome.

We also have mapping-related tables:
- `event_market_links` – confirmed mappings between markets and sports events.
- `mapping_candidates` – suggested mappings awaiting manual review.

These are all backed by Postgres models (e.g., SQLAlchemy) and exposed through a backend API (FastAPI planned).

---

### 1.2 `venues`

Purpose: centralize platform metadata and fee assumptions.

Suggested fields:
- `id` (PK, short string, e.g. `"polymarket"`, `"kalshi"`).
- `name` – human-readable platform name.
- `base_currency` – e.g. `USD`, `USDC`.
- `fee_model` – JSON or enum + parameters describing trading/commission assumptions.
- `created_at`, `updated_at` – timestamps.

The pure arbitrage engine will use `fee_model` to translate quoted odds/prices into effective payoffs per unit stake.

---

### 1.3 `sports_events` (canonical games/matches)

Each row represents a single sports game or match, independent of venue.

Suggested fields:
- `id` (PK).
- `sport` – e.g. `NFL`, `NBA`, `EPL`.
- `league` – optional if distinct from `sport`.
- `home_team` – canonical home team name.
- `away_team` – canonical away team name.
- `event_start_time_utc` – scheduled start time in UTC.
- `location` – optional.
- `canonical_name` – e.g. `"Lakers @ Warriors 2025-01-12"`.
- `status` – `scheduled`, `in_progress`, `finished`, `cancelled`.
- `source` – optional, where the event was first derived from (venue or external feed).
- `created_at`, `updated_at` – timestamps.

Notes:
- Team names should be canonicalized via a parser/normalizer so that different string variants map to the same underlying team.
- All cross-venue comparison and arbitrage logic is anchored at `sports_events` – we only compare markets attached to the same event.

---

### 1.4 `markets` (venue-specific contracts)

Each `markets` row represents a specific bettable contract on a venue about a `sports_event`.

Suggested fields:
- `id` (PK).
- `venue_id` → `venues.id`.
- `sports_event_id` → `sports_events.id` (nullable until mapped).
- `venue_market_key` – venue’s own identifier (slug, ticker, etc.).
- `market_type` – enum: `moneyline`, `spread`, `total`, `prop`, etc.
- `question_text` – verbatim text from the venue.
- `outcome_group` – string label to group markets of the same “dimension” (e.g. `"Moneyline"` for that event).
- `listing_time_utc` – when the market opened.
- `expiration_time_utc` – last tradable time.
- `settlement_time_utc` – if known/available.
- `status` – `open`, `suspended`, `settled`, `void`.
- `created_at`, `updated_at` – timestamps.

Notes:
- `sports_event_id` being nullable allows us to ingest markets first and attach them to canonical events later via the mapping pipeline.
- `market_type` and `outcome_group` help ensure we only compare structurally similar markets across venues when looking for arbitrage.

---

### 1.5 `market_outcomes`

Each market can have 2 or more outcomes. We model them explicitly so we can reason about payoff coverage.

Suggested fields:
- `id` (PK).
- `market_id` → `markets.id`.
- `label` – internal label, e.g. `home_win`, `away_win`, `draw`, `over`, `under`.
- `display_name` – human-friendly text, e.g. `"Lakers"`, `"Warriors"`, `"Over 220.5"`.
- `line` – numeric line for spreads/totals (e.g. `220.5`), where applicable.
- `side` – for spreads/totals, e.g. `over` or `under`.
- `group_id` – optional, to group outcomes into exhaustive partitions if a market has multiple groups.
- `is_exhaustive_group` – bool or derived flag indicating that the set of outcomes in this group fully covers all possibilities for that betting dimension.
- Settlement:
  - `settlement_value` – typically `0` or `1` for binary outcomes (null until settled).
  - `settled_at` – timestamp when settlement was recorded.

Notes:
- For pure arbitrage detection, we must know which set of outcomes forms a complete partition (e.g. `home_win`, `away_win` in a two-way “draw no bet” market; or `home_win`, `draw`, `away_win` in a three-way market).
- The arb engine will use this structure to ensure that proposed portfolios cover all relevant outcomes for the market type.

---

### 1.6 `quotes` (odds/prices over time)

We store time-stamped odds for each `market_outcome` so that we can:
- Reconstruct the odds state at any point in time.
- Run historical arbitrage detection and PnL simulations.
- Support live scanning for pure arb opportunities.

Suggested fields:
- `id` (PK).
- `market_outcome_id` → `market_outcomes.id`.
- `timestamp` – when the quote was observed.
- `raw_price` – odds/price exactly as given by the venue (decimal odds, American odds, or share price).
- `price_format` – enum: `decimal`, `american`, `share_0_1`, etc.
- `bid_price` – best bid (if order book is available).
- `ask_price` – best ask (if order book is available).
- `source` – `orderbook`, `mid`, `last`, etc.
- Optional normalized fields (filled by later stages):
  - `implied_prob_raw` – implied probability before fees/commission.
  - `net_payoff_per_unit_if_win` – effective payoff per unit stake after fees, for use in arb calculations.
  - `stake_unit` – definition of the unit stake (e.g. per `$1` staked or per share).

Notes:
- Normalization details (fees, vig removal, payoff units) are handled in later parts, but the schema anticipates storing pre-computed values for speed.

---

### 1.7 Mapping support: `event_market_links` and `mapping_candidates`

We separate suggested mappings from confirmed mappings to keep the process modular and reviewable.

#### 1.7.1 `event_market_links` (confirmed mappings)

Represents the finalized relationship between `markets` and `sports_events`.

Suggested fields:
- `id` (PK).
- `sports_event_id` → `sports_events.id`.
- `market_id` → `markets.id`.
- `link_type` – e.g. `primary` (main market about the event) or `secondary` (derivative/related markets).
- `confirmed_by_user` – boolean, whether a human has confirmed the mapping.
- `source` – `auto` or `manual`, indicating how the mapping was created.
- `created_at`, `updated_at` – timestamps.

When a mapping candidate is accepted, we insert/update a row in `event_market_links` and set `markets.sports_event_id` accordingly.

#### 1.7.2 `mapping_candidates` (suggested mappings)

Holds suggestions from the automated mapping engine, awaiting human review.

Suggested fields:
- `id` (PK).
- `market_id` → `markets.id`.
- `candidate_sports_event_id` → `sports_events.id` (nullable if the suggestion is “create a new event”).
- `confidence_score` – float between 0 and 1, higher = more confident.
- `features_json` – JSON blob with underlying features (parsed team names, time deltas, similarity scores, etc.).
- `status` – `pending`, `accepted`, `rejected`.
- `created_at` – when the suggestion was generated.
- `reviewed_at` – when it was accepted/rejected (nullable until reviewed).

Workflow:
- The mapping engine only writes into `mapping_candidates`.
- A separate review process (CLI/API/UI) reads pending candidates, sorted by `confidence_score`.
- On acceptance:
  - Create/update `event_market_links`.
  - Optionally set `markets.sports_event_id`.
  - Mark the candidate `accepted`.
- On rejection:
  - Mark `status = rejected` for that candidate.

This keeps the mapping logic modular: we can replace the engine later (e.g. with an ML/embedding approach) without touching the rest of the system.

---

### 1.8 How Part 1 supports pure arbitrage

With this schema in place:
- For a given `sports_event`, we can query all attached `markets` across all venues.
- For each `market`, we know its `market_type` and `outcome_group`, so we only compare structurally compatible markets (e.g. moneyline vs moneyline).
- For each `market_outcome`, we have explicit outcome definitions and know which sets of outcomes form a complete partition of the game’s results.
- For each `market_outcome`, we can access current and historical `quotes` and convert them into a common payoff representation using the venue’s `fee_model`.

The pure arbitrage engine (later parts) will:
- Take a `sports_event_id` and a `market_type` (e.g. moneyline).
- Gather the best available odds/prices across venues for each relevant outcome.
- Solve for stakes across outcomes/venues such that:
  - Payoff ≥ 0 for every possible outcome.
  - Payoff > 0 for at least one outcome.

Part 1’s deliverable is a coherent, Postgres-backed data model that makes this arbitrage logic straightforward to implement and reason about.

---

### 1.9 Implementation notes and infra alignment

- Tech stack:
  - Backend: Python (FastAPI planned), SQLAlchemy for ORM.
  - Database: Postgres, running in Docker via `docker-compose`.
- This Part 1 schema will be implemented as:
  - SQLAlchemy models and Alembic migrations.
  - Basic API endpoints to inspect `sports_events`, `markets`, `market_outcomes`, and `mapping_candidates`.
- Frontend readiness:
  - Future UI can call endpoints like:
    - `GET /sports-events`
    - `GET /sports-events/{id}`
    - `GET /mapping-candidates?status=pending`
    - `POST /mapping-candidates/{id}/accept` / `reject`
  - These will sit directly on top of the Part 1 schema.

This file is the reference specification for Part 1 and should guide the initial implementation of models, migrations, and early API endpoints.

