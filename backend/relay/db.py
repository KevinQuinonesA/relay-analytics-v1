import os
from pathlib import Path

from alembic import command
from alembic.config import Config

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def database_url():
    return os.environ["DATABASE_URL"]


def _alembic_config(database_url):
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def migrate(database_url, revision="head"):
    command.upgrade(_alembic_config(database_url), revision)


def downgrade(database_url, revision):
    command.downgrade(_alembic_config(database_url), revision)
