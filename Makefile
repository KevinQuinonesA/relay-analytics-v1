.PHONY: up down migrate seed test psql

up:
	docker compose up --build

down:
	docker compose down

migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose run --rm backend python -m relay.seed

test:
	docker compose run --rm backend pytest $(ARGS)

psql:
	docker compose exec db psql -U relay -d relay
