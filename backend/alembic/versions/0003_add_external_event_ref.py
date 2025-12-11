from alembic import op
import sqlalchemy as sa


revision = "0003_add_external_event_ref"
down_revision = "0002_arbitrage_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sports_events",
        sa.Column("external_event_ref", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sports_events", "external_event_ref")

