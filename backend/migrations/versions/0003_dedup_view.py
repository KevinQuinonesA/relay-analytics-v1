"""activity_events_dedup: activity_events with exact duplicates collapsed.

Rows that match on every column except id count once (DISTINCT treats NULLs
as equal). Near-duplicates are kept: they differ in outcome or duration.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE VIEW activity_events_dedup AS
        SELECT DISTINCT account_id, location, event_type, occurred_at, duration_seconds, outcome
        FROM activity_events
        """
    )


def downgrade():
    op.execute("DROP VIEW activity_events_dedup")
