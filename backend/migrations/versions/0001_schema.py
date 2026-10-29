"""Seed schema: accounts and activity_events, as in data/schema.sql.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("industry", sa.String(60), nullable=False),
        sa.Column("timezone", sa.String(60), nullable=False),  # IANA timezone
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),  # UTC
    )
    op.create_table(
        "activity_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("location", sa.String(80), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=False), nullable=False),  # UTC
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("outcome", sa.String(40), nullable=True),
    )


def downgrade():
    op.drop_table("activity_events")
    op.drop_table("accounts")
