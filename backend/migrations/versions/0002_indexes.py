"""Indexes for per-account and per-location time-range queries.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_activity_events_account_occurred", "activity_events", ["account_id", "occurred_at"])
    op.create_index(
        "ix_activity_events_account_location_occurred",
        "activity_events",
        ["account_id", "location", "occurred_at"],
    )


def downgrade():
    op.drop_index("ix_activity_events_account_location_occurred", table_name="activity_events")
    op.drop_index("ix_activity_events_account_occurred", table_name="activity_events")
