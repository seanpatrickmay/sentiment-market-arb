from alembic import op
import sqlalchemy as sa


revision = "0002_arbitrage_tables"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "arbitrage_opportunities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sports_event_id", sa.Integer(), sa.ForeignKey("sports_events.id"), nullable=False),
        sa.Column("market_type", sa.String(length=50), nullable=False),
        sa.Column("outcome_group", sa.String(length=100), nullable=True),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("num_outcomes", sa.Integer(), nullable=False),
        sa.Column("total_stake", sa.Numeric(18, 8), nullable=False),
        sa.Column("worst_case_pnl", sa.Numeric(18, 8), nullable=False),
        sa.Column("best_case_pnl", sa.Numeric(18, 8), nullable=False),
        sa.Column("worst_case_roi", sa.Numeric(18, 8), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("detection_version", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "arbitrage_legs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("arbitrage_opportunity_id", sa.Integer(), sa.ForeignKey("arbitrage_opportunities.id"), nullable=False),
        sa.Column("venue_id", sa.String(length=50), nullable=False),
        sa.Column("market_outcome_id", sa.Integer(), sa.ForeignKey("market_outcomes.id"), nullable=False),
        sa.Column("outcome_label", sa.String(length=50), nullable=False),
        sa.Column("stake_shares", sa.Numeric(18, 8), nullable=False),
        sa.Column("share_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("win_pnl_per_share", sa.Numeric(18, 8), nullable=False),
        sa.Column("lose_pnl_per_share", sa.Numeric(18, 8), nullable=False),
        sa.Column("source_quote_id", sa.Integer(), sa.ForeignKey("quotes.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("arbitrage_legs")
    op.drop_table("arbitrage_opportunities")

