from pathlib import Path

SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "seed.sql"


def seed(database_url):
    raise NotImplementedError
