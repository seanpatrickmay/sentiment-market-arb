## Part 2 – Ingestion & Mapping Automation (Sports, Pure Arbitrage)

Goal: continuously ingest sports markets from Polymarket and Kalshi into Postgres, parse them into structured metadata, and automatically propose `market → sports_event` mappings with confidence scores for manual review. This sets up clean, cross‑venue game/event structure for the pure arbitrage engine.

Scope:
- Only sports markets (e.g. NBA, NFL) for now.
- Only structural mapping: no fair‑value modeling, no probabilistic signals.
- Mapping process must be modular so the engine can be swapped out later (e.g. ML/embeddings) without changing the rest of the system.

---

### 2.1 Venue ingestion architecture

We separate ingestion into two layers: venue-specific fetch/normalize, and a generic DB upsert step.

**2.1.1 Venue ingestors (`ingestion/`)**

For each venue we implement a small module:

- `ingestion/polymarket.py`
  - `fetch_raw_markets() -> list[RawMarket]`
  - `normalize_market(raw: RawMarket) -> NormalizedMarket`

- `ingestion/kalshi.py`
  - Same interface: fetch raw data, normalize to `NormalizedMarket`.

`NormalizedMarket` fields (example):
- `venue_id`
- `venue_market_key`
- `market_type` (e.g. `moneyline`, `spread`, `total`)
- `question_text`
- `listing_time_utc`
- `expiration_time_utc`
- `status`
- Optional: `raw_json` for debugging.

**2.1.2 Persistence into `markets`**

We use a thin persistence layer that writes normalized markets into the Part 1 schema:

- `upsert_market(normalized: NormalizedMarket) -> markets.id`
  - Inserts new rows into `markets` if `venue_market_key` is new for that `venue_id`.
  - Updates mutable fields (`question_text`, `listing_time_utc`, `expiration_time_utc`, `status`) if the venue data changes.
  - Does not overwrite `sports_event_id` or other manually curated fields unless explicitly instructed.

Ingestion jobs:
- `polymarket_ingest_job`:
  - Fetch raw markets → normalize → `upsert_market()`.
- `kalshi_ingest_job`:
  - Same pattern.

**2.1.3 Scheduling**

For now:
- Simple loop or cron‑like scheduler that runs each ingest job periodically (e.g. every N minutes).

Later:
- Can move to a more robust task queue (Celery/RQ) without changing the ingestion interface.

Definition of done (ingestion):
- Running the ingestion jobs populates `markets` with current sports markets for Polymarket and Kalshi.
- `venue_id`, `venue_market_key`, `market_type`, `question_text`, times, and `status` are consistently filled.

---

### 2.2 Parsing & metadata extraction (`sports_parser`)

Goal: enrich each `markets` row with structured sports metadata derived from `question_text` and other venue fields, so we can match markets to canonical `sports_events`.

**2.2.1 Parsed metadata structure**

We define a small parsed metadata object, e.g. `ParsedMarketMetadata`:
- `sport` – e.g. `NBA`.
- `league` – same as sport or more specific.
- `home_team` – canonical home team name.
- `away_team` – canonical away team name.
- `event_start_time_hint` – datetime or `NULL` (best guess based on text and/or venue fields).
- `teams_raw_tokens` – list of lowercased team tokens for fuzzy matching.
- Optional: `line`, `side` for spreads/totals.
- Optional: `notes` or `extra` for debugging.

We store parsed fields either:
- As dedicated columns on `markets` (`parsed_sport`, `parsed_home_team`, `parsed_away_team`, `parsed_start_time_hint`, etc.), and/or
- In a `parsed_metadata` JSON column.

**2.2.2 Parsing logic (`mapping/sports_parser.py`)**

Responsibilities:
- Use regex patterns and league/team dictionaries to:
  - Extract teams and determine home vs away (`A @ B`, `A at B`, `A vs B`, etc.).
  - Extract or infer `sport` and `league`.
  - Extract date/time hints from the text (e.g. `"Jan 12, 2026"`).
- Normalize team names:
  - Maintain a per‑league `team_aliases` configuration (e.g. YAML/JSON) mapping spelling variants to canonical team names.

Definition of done (parser):
- For a selected initial subset (e.g. NBA and/or NFL), the parser correctly extracts `sport`, `home_team`, `away_team`, and a reasonable start-time hint for most relevant markets.
- Parsed fields are persisted on `markets` so they can be used by the mapping engine.

---

### 2.3 Event creation / lookup (`sports_events`)

Goal: ensure we have a canonical `sports_events` row to represent each game or match that appears in markets, using parsed metadata to create or attach to events.

**2.3.1 Event key and lookup**

We define a deterministic event key from parsed metadata:
- `event_key = f(sport, canonical_home_team, canonical_away_team, date_bucket)`
  - `date_bucket` could be the UTC date or a coarse time bucket around the game start (e.g. nearest hour/day).

When a new or updated market is parsed:
1. Compute `event_key` from parsed fields.
2. Search `sports_events` for candidates where:
   - `sport` matches.
   - Team combination matches (`home_team`, `away_team`, order considered).
   - `event_start_time_utc` is within a small window of `event_start_time_hint` if available.

**2.3.2 Event creation rules**

Cases:
- **Clear match** (one `sports_events` row matches the parsed game):
  - Use that event as the candidate `sports_event_id`.
- **Multiple plausible matches**:
  - Defer final decision to the mapping engine (multiple candidates with differing scores).
- **No plausible match**:
  - Create a new `sports_events` row with:
    - `sport`, `league`, `home_team`, `away_team` from the parser.
    - `event_start_time_utc` set from the hint if available, otherwise `NULL`.
    - `canonical_name` constructed (e.g. `"Team A @ Team B YYYY-MM-DD"`).
    - `status = 'scheduled'`, `source = 'auto'`.

These events are then used as candidates by the mapping suggestion engine.

Definition of done (events):
- For each parsed market, we can either:
  - Identify an existing plausible `sports_event`, or
  - Create a new one if none exists.
- `sports_events` remains reasonably deduplicated via the event key and lookup rules.

---

### 2.4 Mapping suggestion engine (`mapping/engine.py`)

Goal: for each unmapped `market`, generate one or more candidate `sports_events` mappings with confidence scores and store them in `mapping_candidates`, without directly changing confirmed mappings.

**2.4.1 Engine interface**

We keep a simple, swappable interface:

- `suggest_for_market(market_id: int) -> list[MappingCandidateSuggestion]`
- `bulk_suggest_for_unmapped_markets(limit: int) -> None`

Where `MappingCandidateSuggestion` contains:
- `market_id`
- `candidate_sports_event_id`
- `confidence_score`
- `features` (dict to be serialized into `features_json`).

**2.4.2 Candidate search and feature computation**

For each unmapped `market`:
1. Use parsed metadata (`sport`, teams, start_time_hint) to search `sports_events` for candidates:
   - Same `sport` or compatible.
   - Team combination matches or is close via canonical names / aliases.
   - `event_start_time_utc` within a configurable time window of `event_start_time_hint`, if available.

2. For each candidate event, compute features such as:
   - `team_match_score`:
     - `1.0` if both teams match exactly.
     - Lower if only one team matches or fuzzy match.
   - `time_score`:
     - Higher if start times are closer (e.g. ≤ 2 hours).
   - `league_match`:
     - `1.0` if league matches (when known).

3. Combine features into a `confidence_score`, e.g.:
   - `score = w_team * team_match_score + w_time * time_score + w_league * league_match`
   - Normalize or keep in a known range (e.g. 0–1).

If no existing event scores above a minimal threshold:
- Create a new `sports_events` row from parsed metadata (per 2.3.2).
- Generate a candidate mapping to that new event with an appropriate confidence score and a feature flag like `"new_event": true`.

**2.4.3 Writing to `mapping_candidates`**

For each suggestion, we insert into `mapping_candidates`:
- `market_id`
- `candidate_sports_event_id`
- `confidence_score`
- `features_json` (serialized features dict)
- `status = 'pending'`
- `created_at` timestamp

Idempotency:
- On each run, we either:
  - Replace existing pending candidates for a given `market_id`, or
  - Only insert new candidates when something material changes.

Definition of done (mapping engine):
- Running `bulk_suggest_for_unmapped_markets` populates `mapping_candidates` for most unmapped `markets`.
- Obvious mappings (e.g. identical game names across venues) receive high `confidence_score` and rise to the top.

---

### 2.5 Manual review & confirmation workflow

Goal: give you a simple way to review and confirm/reject mapping suggestions, which then update the canonical linkage tables used by the arb engine.

**2.5.1 API endpoints**

We design endpoints that a CLI or web frontend can consume:

- `GET /mapping-candidates?status=pending&limit=N`
  - Returns pending candidates sorted by `confidence_score DESC`.
  - Each item includes:
    - Candidate id.
    - Market summary: venue, `question_text`, parsed teams/time.
    - Candidate `sports_event` summary: canonical teams, start time, `canonical_name`.
    - Confidence score and key features.

- `POST /mapping-candidates/{id}/accept`
  - Transactionally:
    - Insert or update `event_market_links` with:
      - `sports_event_id`, `market_id`, `link_type = 'primary'` (default), `confirmed_by_user = true`, `source = 'manual'`.
    - Update `markets.sports_event_id` for that `market_id`.
    - Set `mapping_candidates.status = 'accepted'`, `reviewed_at = now()`.

- `POST /mapping-candidates/{id}/reject`
  - Sets `mapping_candidates.status = 'rejected'`, `reviewed_at = now()`.
  - Optionally records that this `market_id` + `sports_event_id` pair should not be suggested again.

**2.5.2 “Pair” view**

While the underlying data model is `market → sports_event`, the API/CLI/UI can present suggestions as cross‑venue pairs:
- For a given `sports_event`, show attached markets from each venue.
- For pending candidates, show venue questions side‑by‑side and highlight differences, sorted by `confidence_score`.

Definition of done (review):
- You can list pending suggestions, see clearly which market and sports event they relate to, and accept/reject them.
- Accepted mappings appear in `event_market_links` and `markets.sports_event_id` and are no longer shown as pending.

---

### 2.6 Modularity and future upgrades

We keep the ingestion/mapping pipeline modular:
- Ingestors:
  - Each venue has its own module implementing `fetch_raw_markets` and `normalize_market`.
- Parser:
  - `sports_parser` is a pure function from venue text/payload to `ParsedMarketMetadata`.
  - We can replace regexes with ML/embeddings later without touching DB schema.
- Mapping engine:
  - `mapping/engine.py` exposes `suggest_for_market` and `bulk_suggest_for_unmapped_markets`.
  - Internals (features, scoring, ML models) can be upgraded freely as long as the interface and DB outputs (`mapping_candidates`) stay the same.

This satisfies the requirement that mapping is automated, reviewable, and easily swappable.

---

### 2.7 Definition of done for Part 2

Part 2 is considered complete when:
- Ingestion:
  - Polymarket and Kalshi sports markets are being ingested into `markets` on a schedule.
  - Basic fields (`market_type`, `question_text`, times, `status`) are normalized.
- Parsing:
  - For the targeted initial leagues (e.g. NBA/NFL), `parsed_*` fields on `markets` are filled with correct sport, teams, and reasonable start-time hints for most relevant markets.
- Events:
  - `sports_events` is populated with canonical games created or found via parsed metadata.
- Mapping:
  - Running the mapping engine populates `mapping_candidates` with sensible confidence scores.
  - You can review candidates via API/CLI, accept/reject them, and see:
    - Confirmed mappings in `event_market_links`.
    - `markets.sports_event_id` set for accepted mappings.

With Part 2 in place, we will have a clean, cross‑venue representation of sports events and markets ready for the pure arbitrage computations defined in later parts.

