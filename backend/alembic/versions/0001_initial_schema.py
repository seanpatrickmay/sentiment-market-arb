from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venues",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("base_currency", sa.String(length=10), nullable=False),
        sa.Column("fee_model", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "sports_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sport", sa.String(length=20), nullable=False),
        sa.Column("league", sa.String(length=50), nullable=True),
        sa.Column("home_team", sa.String(length=100), nullable=False),
        sa.Column("away_team", sa.String(length=100), nullable=False),
        sa.Column("event_start_time_utc", sa.DateTime(), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("canonical_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "markets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("venue_id", sa.String(length=50), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("sports_event_id", sa.Integer(), sa.ForeignKey("sports_events.id"), nullable=True),
        sa.Column("venue_market_key", sa.String(length=100), nullable=False),
        sa.Column("market_type", sa.String(length=50), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("outcome_group", sa.String(length=100), nullable=True),
        sa.Column("listing_time_utc", sa.DateTime(), nullable=True),
        sa.Column("expiration_time_utc", sa.DateTime(), nullable=True),
        sa.Column("settlement_time_utc", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("parsed_sport", sa.String(length=20), nullable=True),
        sa.Column("parsed_league", sa.String(length=50), nullable=True),
        sa.Column("parsed_home_team", sa.String(length=100), nullable=True),
        sa.Column("parsed_away_team", sa.String(length=100), nullable=True),
        sa.Column("parsed_start_time_hint", sa.DateTime(), nullable=True),
        sa.Column("parsed_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "market_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("line", sa.Numeric(10, 3), nullable=True),
        sa.Column("side", sa.String(length=20), nullable=True),
        sa.Column("group_id", sa.String(length=50), nullable=True),
        sa.Column("is_exhaustive_group", sa.Boolean(), nullable=False),
        sa.Column("settlement_value", sa.Integer(), nullable=True),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "quotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("market_outcome_id", sa.Integer(), sa.ForeignKey("market_outcomes.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("raw_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("price_format", sa.String(length=20), nullable=False),
        sa.Column("bid_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("ask_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("share_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("net_pnl_if_win_per_share", sa.Numeric(18, 8), nullable=True),
        sa.Column("net_pnl_if_lose_per_share", sa.Numeric(18, 8), nullable=True),
        sa.Column("decimal_odds", sa.Numeric(18, 8), nullable=True),
        sa.Column("implied_prob_raw", sa.Numeric(18, 8), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "event_market_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sports_event_id", sa.Integer(), sa.ForeignKey("sports_events.id"), nullable=False),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("link_type", sa.String(length=50), nullable=False),
        sa.Column("confirmed_by_user", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "mapping_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("candidate_sports_event_id", sa.Integer(), sa.ForeignKey("sports_events.id"), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("mapping_candidates")
    op.drop_table("event_market_links")
    op.drop_table("quotes")
    op.drop_table("market_outcomes")
    op.drop_table("markets")
    op.drop_table("sports_events")
    op.drop_table("venues")

