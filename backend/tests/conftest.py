import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from relay.db import migrate

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://relay:relay@localhost:5432/relay_test"
)


@pytest.fixture
def empty_db_url():
    """A freshly created, empty test database."""
    url = make_url(TEST_DATABASE_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()
    return url.render_as_string(hide_password=False)


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
