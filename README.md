# Relay — "Is this normal for us?"

Weekly activity per location compared against each location's own recent history, so a customer admin can see on Monday morning which sites need attention.

The plan, decisions and their alternatives are in [PLAN.md](PLAN.md).

## The ticket

> **DASH-247 — Help customers understand whether their recent activity is normal**
>
> Customers looking at their dashboard can't tell whether this week's numbers are good, bad, or typical for them. Product wants the dashboard to help a customer answer *"is this normal for us?"* at a glance, without exporting data or calling their account manager.
>
> **Notes from product:**
>
> - probably involves comparing against some baseline
> - multi-location customers matter
> - a customer admin should be able to look at this Monday morning and act on it
>
> **Out of scope per product:** alerting/notifications, ML/forecasting.

## Running it

Requires Docker.

```bash
docker compose up --build   # Postgres, migrations, seed (loaded once)
make test                   # backend tests against a throwaway database
```

| Variable | Default | What it sets |
|---|---|---|
| `DB_PORT` | `5432` | Host port for Postgres |
| `BACKEND_PORT` | `8000` | Host port for the API (from phase 4) |

## Data

`data/seed.sql` is the starter dataset, unchanged (a test checks its hash). `data/schema.sql` is the reference DDL that the Alembic migrations in `backend/migrations` reproduce.

## Status

Work in progress; see the implementation order in PLAN.md section 8.

## Next steps

- Missed-call rate per account, with a minimum number of calls (PLAN.md section 9).
