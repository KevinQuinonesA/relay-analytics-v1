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
make test-frontend          # frontend tests (Vitest + Testing Library)
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

- **Account totals (not defined in PLAN.md).** The header's per-type totals are the sums of the location numbers. This week's count is the sum of the locations' counts, so it always adds up to the rows. The baseline sums each location's weeks from its own history start, beginning at the account's earliest location history. Median and typical range use the same rule and thresholds as locations. Totals are context only and never flagged.

- **Default as-of uses the UTC date of the latest event (D2).** If data arrives up to a Sunday evening in a US timezone, the UTC date is already Monday, so the default picks a week that hasn't ended locally. The seed isn't affected: its last event is Monday 2026-07-27 22:20 UTC. In production the default should be today's date.

## To revisit with product

- **Account totals are never flagged, even well outside their range.** Example: Pacific Smiles (account 5), week of Jul 13 (as-of 2026-07-20), appointments 9 vs typical 4–6. This is by design for v1, since totals are context only. Whether the account level should get its own marker is a product call.
- **`MIN_FLAG_DISTANCE` (0.3) sits close to cases a person would call worrying.** Example: account 6 Site N, week of Apr 13 (as-of 2026-04-20), 1 event vs typical 3–8. The distance is 2/7 ≈ 0.29, so it shows only as "slightly below". Examples like this are what to tune the threshold with.
- **Above and below typical share the same highlight on purpose.** Whether more activity is good depends on the business (more calls can mean demand or a problem), so the UI stays neutral until product decides.

## Next steps

- Missed-call rate per account, with a minimum number of calls (PLAN.md section 9).
