import itertools
import os
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from relay.db import migrate
from relay.seed import seed

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://relay:relay@localhost:5432/relay_test"
)


def create_database(name):
    """(Re)create an empty database next to the test database and return its URL."""
    url = make_url(TEST_DATABASE_URL).set(database=name)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()
    return url.render_as_string(hide_password=False)


@pytest.fixture
def empty_db_url():
    """A freshly created, empty test database."""
    return create_database(make_url(TEST_DATABASE_URL).database)


@pytest.fixture
def migrated_db_url(empty_db_url):
    migrate(empty_db_url)
    return empty_db_url


@pytest.fixture
def engine_for():
    engines = []

    def make(url):
        engine = create_engine(url)
        engines.append(engine)
        return engine

    yield make
    for engine in engines:
        engine.dispose()


@pytest.fixture(scope="session")
def seeded_db_url():
    """The full seed, loaded once per test session. Read-only."""
    url = create_database(make_url(TEST_DATABASE_URL).database + "_seeded")
    migrate(url)
    seed(url)
    return url


@pytest.fixture(scope="session")
def seeded_conn(seeded_db_url):
    engine = create_engine(seeded_db_url)
    with engine.connect() as conn:
        yield conn
    engine.dispose()


class Rows:
    """Inserts synthetic accounts and events. Timestamps are naive UTC, like the seed."""

    def __init__(self, conn):
        self.conn = conn
        self.ids = itertools.count(1)

    def account(self, account_id, timezone, name=None):
        self.conn.execute(
            text(
                "INSERT INTO accounts (id, name, industry, timezone, created_at) "
                "VALUES (:id, :name, 'Test', :tz, '2025-01-01 00:00:00')"
            ),
            {"id": account_id, "name": name or f"Account {account_id}", "tz": timezone},
        )

    def event(self, account_id, location, utc, event_type="call_received", outcome=None, duration=None, n=1):
        occurred_at = datetime.fromisoformat(utc) if isinstance(utc, str) else utc
        self.conn.execute(
            text(
                "INSERT INTO activity_events "
                "(id, account_id, location, event_type, occurred_at, duration_seconds, outcome) "
                "VALUES (:id, :account_id, :location, :event_type, :occurred_at, :duration, :outcome)"
            ),
            [
                {
                    "id": next(self.ids), "account_id": account_id, "location": location,
                    "event_type": event_type, "occurred_at": occurred_at,
                    "duration": duration, "outcome": outcome,
                }
                for _ in range(n)
            ],
        )


@pytest.fixture
def conn(migrated_db_url, engine_for):
    with engine_for(migrated_db_url).connect() as connection:
        yield connection


@pytest.fixture
def rows(conn):
    return Rows(conn)
