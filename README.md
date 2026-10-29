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
docker compose up --build   # Postgres, migrations, seed (loaded once), API, UI
make test                   # backend tests against a throwaway database
```

Then open <http://localhost:5173>. The selected account and as-of date are in the URL (`/?account=15&as_of=2026-04-20`), so a reload or a shared link keeps them.

| Variable | Default | What it sets |
|---|---|---|
| `DB_PORT` | `5432` | Host port for Postgres |
| `BACKEND_PORT` | `8000` | Host port for the API |
| `FRONTEND_PORT` | `5173` | Host port for the UI |

API: `GET /api/accounts` and `GET /api/accounts/{id}/weekly-summary?as_of=YYYY-MM-DD` (`as_of` optional, defaults to the latest data). Interactive docs at `/docs` on the backend port.

## Data

`data/seed.sql` is the starter dataset, unchanged (a test checks its hash). `data/schema.sql` is the reference DDL that the Alembic migrations in `backend/migrations` reproduce.

## Status

Work in progress; see the implementation order in PLAN.md section 8.

## Deviations from PLAN.md and known limitations

- **Default as-of uses the UTC date of the latest event (D2).** If data arrives up to a Sunday evening in a US timezone, the UTC date is already Monday, so the default picks a week that hasn't ended locally. The seed isn't affected: its last event is Monday 2026-07-27 22:20 UTC. In production the default should be today's date.

## Next steps

- Missed-call rate per account, with a minimum number of calls (PLAN.md section 9).
