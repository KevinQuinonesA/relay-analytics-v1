.PHONY: up down migrate seed test test-frontend psql screenshots

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

test-frontend:
	docker compose run --rm --build frontend-test

psql:
	docker compose exec db psql -U relay -d relay

# README screenshots; needs a running stack (make up). Uses Playwright's image, nothing installed locally.
screenshots:
	docker run --rm --add-host=host.docker.internal:host-gateway -e UI_URL=http://host.docker.internal:$${FRONTEND_PORT:-5173} \
		-u $$(id -u):$$(id -g) -e HOME=/tmp -v "$$PWD:/w" -w /w \
		mcr.microsoft.com/playwright/python:v1.49.1-noble sh -c \
		"pip install -q --user --break-system-packages playwright==1.49.1 && python3 scripts/screenshots.py"
