# Relay — "Is this normal for us?"

Each location's last complete week, compared with its own previous 8 weeks, so a customer admin can see on Monday morning which sites need attention. Full reasoning, decisions D1–D15 and their alternatives are in [PLAN.md](PLAN.md); this README is the short version.

## Running it

**You need:** Docker with Compose v2 (`docker compose version`), git, and `make`. Without `make`, run the command shown next to each target in the `Makefile`. Ports 5432, 8000 and 5173 must be free, or set the variables below.

```bash
git clone <this repo> && cd <repo folder>
docker compose up --build
```

The first build takes a few minutes. When the frontend logs `Configuration complete; ready for start up` (a few seconds after the backend's `Uvicorn running`), open **<http://localhost:5173>** and pick an account. On first start the backend creates the schema with migrations and loads `data/seed.sql` once; later starts skip the seed.

The account and as-of date live in the URL (`/?account=6&as_of=2026-04-20`), so reloading or sharing a link keeps them. Stop with `Ctrl+C`, or `docker compose down` (add `-v` to delete the database too).

| Variable | Default | What it sets |
|---|---|---|
| `DB_PORT` | `5432` | Host port for Postgres |
| `BACKEND_PORT` | `8000` | Host port for the API (interactive docs at `/docs`) |
| `FRONTEND_PORT` | `5173` | Host port for the UI |

**Tests:** `make test` (backend: rules, aggregation, seed known answers, API) and `make test-frontend` (UI). Both run in Docker against throwaway databases, with nothing installed locally.

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

## How I read it

- **"Normal for us" means normal for this location**, compared with its own recent history, not with peers. Sites within one account differ too much in size for site-vs-site comparison to mean anything.
- **"This week" on a Monday morning means the last complete Mon–Sun week**, in the account's own timezone.
- **Multi-location is the core case:** one list per account, with the locations that need attention first.
- **The answer has to fit one line an admin can trust:** "Site B: 2 events, typical 4–12". With ML out of scope, the rule must be explainable.

## Key decisions and trade-offs

Full list with alternatives: [PLAN.md §2](PLAN.md). Thresholds live in `backend/relay/thresholds.py`.

| Decision | What it buys | What it costs |
|---|---|---|
| Baseline = **median of the previous 8 weeks**; typical range = **middle 6 of those 8** (D3, D4) | A one-off spike (account 6 logged 880 events in a week; its median week is 76) doesn't distort the baseline or the range | Only 8 weeks, so no seasonality; slower to notice a gradual trend |
| **Status on the location total**, with per-type counts as context only (D5) | Enough volume to say anything; split by type, 91% of location × type combinations are too small | Calls, leads and appointments are summed into one number |
| **Minimum volume applies to the baseline median** (≥ 5/week), not to this week (D6) | A drop to zero gets flagged, which is the most important Monday signal | Very small sites always read "too little activity to tell" |
| **Flag only when clearly outside the range**: at least 30% of a normal week beyond the edge (D13) | 3 flagged locations instead of 18 at the latest week (7–9 in the April weeks checked); one stray event never flags | Near misses show only as "slightly below/above" (see "To revisit with product") |
| **One global as-of date**; weeks bucketed in each account's IANA timezone (D1, D2) | A location that went quiet can't silently fall back to an older week; daylight-saving switches are handled | Default as-of edge case, see "Known limitations" |
| **Exact duplicates removed at query time**, near-duplicates kept (D9) | The seed stays as-is; near-duplicates differ in outcome or duration, so they look like real separate events | Any fuzzy duplicates in production would still be counted |

### Why the typical ranges look wide

Locations are small. A typical location sees about 6–7 events a week, and at that size ordinary weeks swing a lot: at locations averaging 5–7 events a week, 43% of weeks land more than 30% from the location's own median, and 1 in 5 more than 50%. The typical range (usually about 0.7× to 1.4× the median) shows that noise instead of hiding it. That's why a week has to be clearly outside the range before it's flagged.

## Stack and why

- **Postgres:** its `AT TIME ZONE` handles IANA zones and daylight saving natively, and local-time bucketing is the riskiest correctness area.
- **FastAPI + Pydantic:** the response models are the API contract.
- **SQLAlchemy 2.0 (sync) + Alembic:** for the connection layer and migrations.
- **React + TypeScript (strict) + Vite:** served by nginx, which also proxies `/api`, so there's no CORS setup.
- **Docker Compose:** runs Postgres, the backend and the frontend with one command; tests run in containers too.

Notable choices inside the stack:

- **Raw SQL for the aggregation, Alembic's schema operations for the schema.** The weekly aggregation (removing duplicates, local-time conversion, `generate_series` to fill empty weeks) is one readable SQL query with bound parameters (`relay/weekly.py`), tested on synthetic rows. An ORM would hide the part that most needs to be visible. The schema is defined through Alembic migrations, with a duplicate-free view (`activity_events_dedup`).
- **SQL buckets the data; pure Python applies the rule.** `relay/normality.py` has no database access and uses exact `Fraction` arithmetic, so a distance of exactly 0.3 is flagged, and every rule is unit-tested in isolation.
- **The URL is the only UI state.** Account and as-of are read from and written to the query string. Reload, share and back/forward all work, and there is no second copy of the state to drift.
- **The frontend renders and never ranks.** The API returns locations already ordered, with an explicit `flagged` field.
- **Independent reference calculation.** `analysis/reference.py` recomputes everything with SQLite and Python's `zoneinfo`, sharing no code with the app. The seed known-answer tests use its output, never the app's own.

## Deliberately deferred

- **Missed-call rate:** time went to tests instead. It also needs a minimum number of calls, and per location probably a 4-week window, since a location gets about 4 calls a week.
- **Alerting, notifications, ML/forecasting:** out of scope per product.
- **An LLM in the feature:** the answer is already a deterministic line that admins need to trust. See [PLAN.md §10](PLAN.md) for where one could fit later.
- **Account-level flags, configurable week definitions or a rolling window, editable thresholds:** each needs a product decision first.
- **Authentication and tenant isolation, peer benchmarks, fuzzy duplicate matching:** not needed to answer the ticket.

## With another day

1. Sit down with product and tune `MIN_FLAG_DISTANCE` and `MIN_BASELINE_MEDIAN` using the seed examples below.
2. Add the missed-call rate per account, with a minimum number of calls.
3. Make the default as-of "today" and show how fresh the data is, which fixes the edge case below.
4. Add a 9-week sparkline per location, so the range and this week can be seen at a glance.
5. Set up CI that runs `docker compose up` from scratch and both test suites, plus one browser smoke test for reload and back/forward.

## Known limitations

- **Account totals (not defined in PLAN.md).** The header's per-type totals are the sums of the location numbers: this week's count always adds up to the rows. The baseline sums each location's weeks from its own history start. The median and range use the same rule and thresholds as locations. Totals are context only and never flagged.
- **The default as-of is the UTC date of the latest event (D2).** If data arrives up to a Sunday evening in a US timezone, the UTC date is already Monday, so the default picks a week that hasn't ended locally. The seed isn't affected (its last event is Monday 2026-07-27 22:20 UTC). In production the default should be today's date.

## To revisit with product

- **Account totals are never flagged, even well outside their range.** Example: Pacific Smiles (account 5), week of Jul 13 (as-of 2026-07-20), appointments 9 vs typical 4–6. By design for v1, since totals are context only.
- **`MIN_FLAG_DISTANCE` (0.3) sits close to cases a person would call worrying.** Example: account 6 Site N, week of Apr 13 (as-of 2026-04-20), 1 event vs typical 3–8. The distance is 2/7 ≈ 0.29, so it shows only as "slightly below". Examples like this are what to tune the threshold with.
- **Above and below typical share the same highlight on purpose.** Whether more activity is good depends on the business, so the UI stays neutral until product decides.

## Repository layout

```
backend/relay/      thresholds.py · normality.py (rule) · weekly.py (SQL) · summary.py · api.py
backend/migrations/ schema, indexes, dedup view
backend/tests/      rules, aggregation, seed known answers, API
frontend/src/       React app and its tests (App.test.tsx)
analysis/           independent reference calculation
data/               seed.sql (unchanged starter data) and the reference schema.sql
```
