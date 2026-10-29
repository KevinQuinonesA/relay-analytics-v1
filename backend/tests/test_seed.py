"""Expected values come from data/seed.sql itself (grep counts, sha256sum, rows copied verbatim)."""
import hashlib
from datetime import datetime

from sqlalchemy import text

from relay.seed import SEED_PATH, seed

SEED_SHA256 = "40e60ee81d999eb32057b4437bc84e9ec197265d4e58c13c0bfbad150e6eaea2"


def counts(engine):
    with engine.connect() as conn:
        return (
            conn.execute(text("SELECT count(*) FROM accounts")).scalar_one(),
            conn.execute(text("SELECT count(*) FROM activity_events")).scalar_one(),
        )


def event(engine, event_id):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT account_id, location, event_type, occurred_at, duration_seconds, outcome "
                "FROM activity_events WHERE id = :id"
            ),
            {"id": event_id},
        ).one()


def test_seed_file_is_the_unmodified_starter_dataset():
    assert hashlib.sha256(SEED_PATH.read_bytes()).hexdigest() == SEED_SHA256


def test_seed_loads_every_row(migrated_db_url, engine_for):
    assert seed(migrated_db_url) is True
    assert counts(engine_for(migrated_db_url)) == (20, 12626)


def test_seed_is_idempotent(migrated_db_url, engine_for):
    assert seed(migrated_db_url) is True
    assert seed(migrated_db_url) is False
    assert counts(engine_for(migrated_db_url)) == (20, 12626)


def test_seed_values_round_trip(migrated_db_url, engine_for):
    seed(migrated_db_url)
    engine = engine_for(migrated_db_url)
    assert event(engine, 1) == (5, "Site B", "call_received", datetime(2026, 2, 1, 10, 57, 44), 621, "missed")
    assert event(engine, 12626) == (10, "Site A", "call_received", datetime(2026, 7, 27, 22, 20, 34), 894, "missed")
    assert event(engine, 36) == (6, "Site A", "call_received", datetime(2026, 2, 2, 12, 32, 11), None, "missed")
    assert event(engine, 66) == (1, "Site E", "lead_created", datetime(2026, 2, 2, 16, 12, 47), None, None)


def test_timestamps_are_not_shifted_by_session_timezone(migrated_db_url, engine_for):
    # occurred_at is naive UTC; a non-UTC session must read the same wall-clock value.
    seed(migrated_db_url)
    with engine_for(migrated_db_url).connect() as conn:
        conn.execute(text("SET TIME ZONE 'America/New_York'"))
        value = conn.execute(text("SELECT occurred_at FROM activity_events WHERE id = 1")).scalar_one()
    assert value == datetime(2026, 2, 1, 10, 57, 44)
