"""Load data/seed.sql unchanged, once. Safe to run on every start."""
from pathlib import Path

from sqlalchemy import create_engine

from relay.db import database_url

SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "seed.sql"


def seed(database_url, seed_path=SEED_PATH):
    """Load the seed into an empty database. Returns False if data is already there."""
    engine = create_engine(database_url)
    try:
        conn = engine.raw_connection()
        try:
            with conn.cursor() as cur:
                # Serialize concurrent starts; the lock is released at commit/rollback.
                cur.execute("LOCK TABLE accounts IN EXCLUSIVE MODE")
                cur.execute("SELECT EXISTS (SELECT 1 FROM accounts)")
                if cur.fetchone()[0]:
                    conn.rollback()
                    return False
                # No parameters, so psycopg sends the multi-statement file as one simple query.
                cur.execute(seed_path.read_text())
            conn.commit()
            return True
        finally:
            conn.close()
    finally:
        engine.dispose()


if __name__ == "__main__":
    print("seeded" if seed(database_url()) else "already seeded, skipping")
