# CLAUDE.md

DASH-247: show customers whether last week's activity per location is normal for them. The ticket is quoted in README.md.

## Running things

```bash
make up                     # docker compose up --build: db, migrations, seed (loaded once)
make test                   # backend tests in the container, against throwaway databases
make test ARGS="-q tests/test_weekly.py"
make migrate | make seed | make psql | make down
python3 -I analysis/reference.py data/schema.sql data/seed.sql   # independent reference answers
```

Ports: `DB_PORT` (default 5432), `BACKEND_PORT` (default 8000).

## Where things live

- `PLAN.md`: interpretation, decisions D1–D15 with alternatives, product assumptions, implementation order (section 8). Progress is in `git log`.
- `backend/relay/thresholds.py`: the tunable constants. Never put threshold literals in SQL or other code.
- `backend/relay/normality.py`: the rule and ranking, pure functions in exact arithmetic (`Fraction`).
- `backend/relay/weekly.py`: the aggregation SQL. `backend/relay/summary.py`: wires aggregation and rule together for one account.
- `analysis/reference.py`: independent implementation (SQLite + `zoneinfo`) that shares no code with the backend.
- `docs/` is gitignored; it's context, not part of the repo.

## Data rules

- `data/seed.sql` is used as-is. Never edit, regenerate or extend it; a test checks its hash.
- Count from the `activity_events_dedup` view: exact duplicates (equal on every column except `id`, NULLs included) count once. Near-duplicates are kept.
- Local time comes from each account's IANA `timezone` (Postgres `AT TIME ZONE`, `zoneinfo` in analysis). Never use fixed offsets. Weeks are Mon–Sun in local time.
- The as-of date is global: by default the UTC date of the latest event in the whole dataset, never per account or location. The target week is the last complete week before it.
- A location's history starts on the first Monday on or after its first event. Weeks inside the history with no events are 0; weeks before it are no history.
- Status is computed on location totals; per-type counts are context only. NULL outcomes count toward volume. `duration_seconds` is not used.
- The account 6 spike (2026-06-03) stays in the raw totals, with no special handling.

## Working rules

- **TDD.** Commit the failing tests before the code that makes them pass.
- **Expected values** come from hand-worked synthetic cases (arithmetic in a comment) or from `analysis/reference.py` output, never from running the app code. If the code disagrees, investigate; never change a test to match the code.
- **Testing effort** goes to the rules and the aggregation. Schema, API and frontend tests stay thin.
- **Check that new tests bite:** inject the bug they target, confirm a failure, restore.
- **Any number or claim about the data** comes with the query that produced it and its raw output. Run `/verify` and label inferences as inferred.
- **`PLAN.md` is not edited unless the user says so.** Deviations and known limitations go in README.md.

## Stack conventions

### Backend (FastAPI + SQLAlchemy 2.0 + Postgres)

- Route handlers stay thin: validate input, call `relay.summary`, return. No SQL or rule logic in routes.
- Every endpoint has a Pydantic response model; that's the API contract.
- SQL lives in `relay/weekly.py`, always with bound parameters, never f-strings.
- Sync SQLAlchemy is fine here, don't introduce async without a reason.
- Errors are real status codes (404 unknown account, 422 bad input), never a 200 with an error body.
- Never edit an applied migration, add a new one. Every migration has a working downgrade.
- No new dependency without saying why.

### Frontend (React + TypeScript + Vite)

- TypeScript strict, no `any`.
- Function components and hooks. Data fetching lives in hooks (e.g. `useWeeklySummary`), components just render.
- The URL is the single source of truth for account and as-of. No `useState` copy of it.
- Every fetch handles loading, error and empty states explicitly.
- The frontend never computes or re-ranks, it renders what the API returns.
- Plain CSS, no UI library. Status is shown with text or icon, never color alone.
- Tests use Testing Library from the user's point of view (roles, visible text), not implementation details.

### Commits

- Small, one concern each. The message says what and why.
