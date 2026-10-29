#!/bin/sh
set -e
alembic upgrade head
python -m relay.seed
exec uvicorn relay.api:app --host 0.0.0.0 --port 8000
