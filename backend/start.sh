#!/bin/sh
set -e
alembic upgrade head
python -m relay.seed
