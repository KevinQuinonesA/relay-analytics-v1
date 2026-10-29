"""Expected columns come from data/schema.sql, the starter's reference DDL."""
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from relay.db import downgrade


def columns(engine, table):
    return {c["name"]: c for c in inspect(engine).get_columns(table)}


def assert_column(col, type_, length=None, nullable=False):
    assert isinstance(col["type"], type_), col
    if length is not None:
        assert col["type"].length == length, col
    assert col["nullable"] is nullable, col


def test_accounts_matches_reference_schema(migrated_db_url, engine_for):
    cols = columns(engine_for(migrated_db_url), "accounts")
    assert list(cols) == ["id", "name", "industry", "timezone", "created_at"]
    assert_column(cols["id"], postgresql.INTEGER)
    assert_column(cols["name"], postgresql.VARCHAR, 120)
    assert_column(cols["industry"], postgresql.VARCHAR, 60)
    assert_column(cols["timezone"], postgresql.VARCHAR, 60)
    assert_column(cols["created_at"], postgresql.TIMESTAMP)
    assert cols["created_at"]["type"].timezone is False


def test_activity_events_matches_reference_schema(migrated_db_url, engine_for):
    cols = columns(engine_for(migrated_db_url), "activity_events")
    assert list(cols) == [
        "id", "account_id", "location", "event_type", "occurred_at", "duration_seconds", "outcome",
    ]
    assert_column(cols["id"], postgresql.INTEGER)
    assert_column(cols["account_id"], postgresql.INTEGER)
    assert_column(cols["location"], postgresql.VARCHAR, 80)
    assert_column(cols["event_type"], postgresql.VARCHAR, 40)
    assert_column(cols["occurred_at"], postgresql.TIMESTAMP)
    assert cols["occurred_at"]["type"].timezone is False
    assert_column(cols["duration_seconds"], postgresql.INTEGER, nullable=True)
    assert_column(cols["outcome"], postgresql.VARCHAR, 40, nullable=True)


def test_primary_keys_are_plain_integers_without_sequences(migrated_db_url, engine_for):
    # The seed supplies ids; the reference schema has no SERIAL/IDENTITY.
    engine = engine_for(migrated_db_url)
    for table in ("accounts", "activity_events"):
        assert inspect(engine).get_pk_constraint(table)["constrained_columns"] == ["id"]
        assert columns(engine, table)["id"]["default"] is None
        assert columns(engine, table)["id"].get("identity") is None


def test_activity_events_references_accounts(migrated_db_url, engine_for):
    fks = inspect(engine_for(migrated_db_url)).get_foreign_keys("activity_events")
    assert [(fk["constrained_columns"], fk["referred_table"], fk["referred_columns"]) for fk in fks] == [
        (["account_id"], "accounts", ["id"])
    ]


def test_query_indexes_exist(migrated_db_url, engine_for):
    indexes = {
        i["name"]: i["column_names"]
        for i in inspect(engine_for(migrated_db_url)).get_indexes("activity_events")
    }
    assert indexes == {
        "ix_activity_events_account_occurred": ["account_id", "occurred_at"],
        "ix_activity_events_account_location_occurred": ["account_id", "location", "occurred_at"],
    }


def test_downgrade_to_base_removes_everything(migrated_db_url, engine_for):
    downgrade(migrated_db_url, "base")
    inspector = inspect(engine_for(migrated_db_url))
    assert set(inspector.get_table_names()) == {"alembic_version"}
    assert inspector.get_view_names() == []
