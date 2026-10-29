# PLAN — DASH-247: "Is this normal for us?"

## 1. Interpretation

A customer admin opens the dashboard on Monday morning and should see, at a glance, whether last week's activity at each of their locations was typical, and which locations need attention.

- **"Normal" means normal for this location**, judged against its own recent history. Peers and industry don't come into it. Locations within one account differ a lot in size (weekly medians range from 4 to 11 events), so comparing a site to its siblings would mostly show which sites are bigger.
- **"This week" means the last complete week.** On a Monday morning the current week has barely started.
- **Multi-location is the core case.** The account view is a list of locations ranked by how far each one is from its own normal, with the flagged ones at the top.
- **The output has to be explainable in one line**, for example "Site B: 2 events this week, typical 4–12". The out-of-scope list rules out ML and forecasting, and z-scores are hard to read at a glance.

## 2. Decisions

| # | Decision | Alternatives considered | Why |
|---|---|---|---|
| D1 | **The week is the last complete Mon–Sun week in the account's local time**: the most recent week that ends before the as-of date. | A rolling 7 days ending on the as-of date; a calendar month. | Matches the Monday-morning use case, and every week contains the same mix of weekdays and weekend days. A rolling window can become a dashboard setting later. |
| D2 | **The as-of date is global.** It defaults to the date of the latest event in the whole dataset and can be overridden with `?as_of=`. | Using each account's or location's own latest event. | With a per-location default, a location that has gone quiet would silently use an older week and look fine. |
| D3 | **Baseline: median of the 8 previous complete weeks.** | Mean ± standard deviation; z-scores; a longer window (26 weeks); the same week last year; comparing to peers. | A mean breaks on the account 6 spike (8-week mean 168 vs median 66). Median/MAD z-scores over-flag at small counts because the MAD collapses to 1. There is no year-ago history. 8 weeks still reacts to recent change. |
| D4 | **Typical range: the middle 6 of the 8 baseline weeks**, i.e. the 2nd to 7th sorted values. | The full min–max; the interquartile range. | Min–max lets the spike leak in: account 6 Site A calls have weeks [2,2,2,3,5,5,5,26], so min–max would be 2–26 for 8 weeks. Trimming one week at each end removes it with no special rule. |
| D5 | **Status is computed on the location total**, all event types summed. The per-type counts are shown as context, without a flag. | Flagging every location × event type. | Per type, the baselines are tiny (calls median 4/week, leads 1.5, appointments 1), so 188 of 207 cells would read "too little to tell". For location totals it's 8 of 69. |
| D6 | **The minimum-volume rule applies to the baseline median, not to this week's count.** If the median is below `MIN_BASELINE_MEDIAN`, the status is "too little activity to tell". | Applying the minimum to this week's count. | Applying it to this week would mean a drop to zero can never be flagged, and that is the most important Monday signal. Example: account 6 Site G had 0 events in the week of 04-13 against a median of 5.5. |
| D7 | **Ranking by distance**, where distance = events beyond the edge of the typical range ÷ baseline median. Flagged locations come first by distance, then slightly-outside ones by distance, then typical, then too little activity, then insufficient history. Ties are broken by location name. | Raw percentage change (puts tiny sites on top); absolute difference (puts big sites on top). | Scales across site sizes. The median-volume rule (D6) rules out dividing by zero. |
| D8 | **The spike stays in raw totals.** There is no special handling; D3 and D4 already keep it out of the baseline. | Excluding flagged days; annotating them. | We keep the data as-is, and the week of the spike itself correctly shows as above typical. |
| D9 | **Exact duplicates are removed at query time.** A duplicate matches on every column except `id`. | Deleting them in a migration; fuzzy matching on time. | The data is used as-is. Near-duplicates (25 pairs within 60 seconds) differ in outcome or duration, so they look like separate events. |
| D10 | **Thresholds are named constants in one module**, not literals in SQL: `BASELINE_WEEKS = 8`, `RANGE_TRIM = 1`, `MIN_BASELINE_MEDIAN = 5`, `MIN_FLAG_DISTANCE = 0.3` (see D13). | Inline values. | Product will tune them, and tests refer to them by name. |
| D11 | **SQL buckets, Python decides.** SQL removes duplicates, converts to local time, buckets into weeks and fills empty weeks with zero. A pure Python module applies the rule. | Everything in SQL (the middle-6 range is awkward there and hard to unit test); everything in Python (pulls every row, doesn't scale). | The rule can be unit tested without a database, and the database does the timezone work. |
| D12 | **Stack:** Postgres, Python/FastAPI, Alembic migrations, React + TypeScript + Vite. | SQLite (no IANA timezone support, so conversion would happen in app code); a Node backend. | Postgres's `AT TIME ZONE` handles IANA zones and daylight saving natively, which is the riskiest correctness area. |
| D13 | **Flag only when the week is clearly outside its range:** distance ≥ `MIN_FLAG_DISTANCE` (0.3). Below that it's "slightly above/below": the range is shown, but there's no flag. Compared with exact arithmetic, so a distance of exactly 0.3 is flagged. | (a) Flag anything outside the range: about 30% of locations each week, most only 1–2 events out. (c) Widen the range toward min–max, which brings the spike back in. | **What 0.3 means:** this week is past the edge of its usual range by at least 30% of a normal week. A typical week of 10 must be at least 3 events beyond the range edge; a typical week of 6 needs 2. Combined with `MIN_BASELINE_MEDIAN = 5`, the smallest flaggable miss is 2 events, so one stray event never raises a flag. Product can tune it. |
| D14 | **The selected account and as-of date live in the URL** (`/?account=15&as_of=2026-07-27`), so they survive a reload, can be shared, and work with back/forward. Without `as_of`, the server default (D2) applies. | Component state only; `localStorage`. | Reload and share are requirements; local storage is per-browser and invisible. |
| D15 | **One command runs everything:** `docker compose up --build` starts `db` (Postgres), `backend` (migrates, seeds if empty, serves the API) and `frontend` (built and served, proxying `/api` to the backend). | Separate run steps per service. | A reviewer runs one command. Seeding only when empty makes restarts safe. |

## 3. Assumptions I'd confirm with product

1. **Is summing calls, leads and appointments into one activity count meaningful?** One customer may produce all three (call → lead → appointment), so the total may count one journey more than once.
2. **Is "below typical" bad and "above typical" good?** For v1 the wording stays neutral and the UI doesn't color results as good or bad.
3. **Week start:** Monday vs Sunday. Many US businesses think in Sun–Sat weeks.
4. **Are 8 weeks, a minimum median of 5 and a flag distance of 0.3 acceptable?** And should a location with a tiny baseline that suddenly jumps (median 2, this week 40) be flagged anyway? Under D6 it reads "too little activity to tell".
5. **Was the account 6 spike on 2026-06-03 real?** (804 events in one day after removing duplicates, against a weekday median of 13.) It affects nothing in v1, but it is worth knowing.
6. **Is `UTC` correct for Capital City Storage**, or was it left as a default? We use it as-is.
7. **What should a location with fewer than 8 complete weeks of history show?** The plan says "not enough history yet". The alternative is to use what's available, with some minimum.
8. **Leads:** does `open` change to `converted` later? It doesn't matter for volume, but it matters once rates come back.

## 4. Data handling

- **Loading:**
  - An Alembic migration creates the schema from `schema.sql`, with the same types.
  - A second migration adds indexes on `(account_id, occurred_at)` and `(account_id, location, occurred_at)`.
  - The seed is loaded unchanged by a separate `make seed` command, not as a migration, so schema and data stay separate.
- **Duplicates:** a `dedup_events` CTE/view uses `SELECT DISTINCT` over every column except `id`. That removes 12 rows, leaving 12,614 of 12,626.
- **Timezones:**
  - `occurred_at` is converted with `(occurred_at AT TIME ZONE 'UTC') AT TIME ZONE accounts.timezone`.
  - Weeks are bucketed with `date_trunc('week', …)`, which uses ISO weeks starting on Monday.
  - 17 of the 20 accounts observe daylight saving, and the March 2026 switch falls inside the data range.
- **Location identity** is the pair `(account_id, location)`. There is no locations table, and "Site A" of one account is a different place from "Site A" of another.
- **Location history** starts on the first Monday on or after the location's first event, so a partial first week never enters a baseline. In the seed, 51 locations start on 02-02 and 18 on 02-09. Earlier weeks count as no history, not as zero.
- **Zero-fill:** `generate_series` over the weeks from history start to the target week, left-joined to the counts. A week with no events counts as 0.
- **Nulls:** a null `outcome` still counts toward volume. `duration_seconds` is not used: its distribution is the same for connected, missed and voicemail calls.
- **Accounts with no data:** account 20 has no events, so it returns an empty location list and a "no activity yet" state.

## 5. API

`GET /api/accounts` returns `[{id, name, timezone, location_count}]`.

`GET /api/accounts/{account_id}/weekly-summary?as_of=YYYY-MM-DD` (`as_of` is optional and defaults per D2):

```json
{
  "account": {"id": 15, "name": "Sierra Pest Solutions", "timezone": "America/Phoenix"},
  "as_of": "2026-07-27",
  "week": {"start": "2026-07-20", "end": "2026-07-26"},
  "baseline": {"start": "2026-05-25", "end": "2026-07-19", "weeks": 8},
  "thresholds": {"baseline_weeks": 8, "range_trim": 1, "min_baseline_median": 5, "min_flag_distance": 0.3},
  "account_totals": {
    "call_received": {"count": 0, "median": 0, "typical_low": 0, "typical_high": 0}
  },
  "locations": [
    {
      "location": "Site C",
      "status": "above_typical", "flagged": true,
      "count": 12, "median": 6, "typical_low": 4, "typical_high": 7, "distance": 0.83,
      "by_event_type": {"call_received": 0, "lead_created": 0, "appointment_set": 0}
    }
  ]
}
```

The `account_totals` and `by_event_type` values above are placeholders. The Site C numbers are real. Both fields come in phase 5 (section 8); until then they are left out of the response.

- `status` is one of:
  - flagged: `above_typical`, `below_typical`;
  - shown with the range but no flag: `slightly_above`, `slightly_below`;
  - `typical`, `too_little_activity`, `insufficient_history`.
- `flagged: true|false` is returned explicitly, so the client doesn't have to work out which statuses count as flagged.
- `locations` arrive already sorted per D7, so the client never re-ranks.
- `404` for an unknown account; `422` for a malformed `as_of`.
- An `as_of` with no 8-week history before it returns `insufficient_history` for each affected location. It is not an error.

## 6. UI

One page with an account picker and an as-of date picker that defaults to the latest data. Both live in the URL (D14): changing them updates the query string, and loading the page reads it back. An unknown account in the URL shows a "not found" state, not a blank page.

```
Sierra Pest Solutions                         Week of Jul 20–26 · compared with previous 8 weeks
Calls N (typical a–b) · Leads N (a–b) · Appointments N (a–b)            ← context, no flags

▲ Site C   12 events   typical 4–7      calls n · leads n · appts n      ← flagged
▼ Site B    2 events   typical 4–12     calls 0 · leads 1 · appts 1      ← flagged
  Site A    n events   typical a–b      slightly below                  ← range shown, no flag
  Site X    Too little activity to tell (typically under 5 a week)
```

The Site C and Site B values are real seed answers. Everything else in the sketch is a placeholder.

- The wording is neutral ("above typical" / "below typical") until product answers assumption 2. Status is shown with an icon and text, not color alone.
- Empty states: no activity yet (account 20); not enough history; too little activity.
- Kept simple on purpose: no charts in v1. A 9-week sparkline per location is the first thing I'd add.

## 7. Testing approach

TDD for every layer: write a failing test, make it pass, then refactor. Tests are committed before the code they cover, so the history shows it. **Expected values come from hand-worked synthetic cases or from an independent calculation, never from running the implementation.**

**1. Rule unit tests** (pure Python, synthetic, one or more per rule):
- Median of an even-length baseline; the middle-6 range (with ties as well).
- Inside the range, at the boundary, below, above.
- `MIN_FLAG_DISTANCE`:
  - distance just under 0.3 gives slightly below/above, no flag;
  - exactly 0.3 (e.g. 3 beyond the edge with median 10, or 6 with median 20) is flagged, which tests the exact comparison;
  - above 0.3 is flagged.
- A baseline with one huge week: the median and range ignore it.
- `MIN_BASELINE_MEDIAN`:
  - median 4.5 with this week at 0 gives too little activity;
  - median 5 with this week at 0 gives below typical.
- Fewer than 8 weeks of history gives insufficient history.
- Distance math, ranking order across all statuses, and the tie-break.
- Changing the constants changes the outcome, which proves nothing is hard-coded.

**2. Data and SQL tests** (real Postgres, synthetic rows):
- Local-week bucketing:
  - Sunday 23:30 local stays in its week;
  - Monday 00:30 local starts the next week;
  - a UTC timestamp on the next day is pulled back to the local day.
- Daylight saving switches (2026-03-08 for New York) and accounts that don't switch (Phoenix, UTC).
- Exact duplicates are removed; a pair 4 seconds apart is kept.
- Zero-filled weeks; history starting on the first Monday.
- Null outcomes are counted.

**3. API tests:** response shape, default vs explicit `as_of`, sort order, 404 and 422, the empty account.

**4. Seed known-answer tests.** These values come from an independent reference calculation written for this plan: SQLite plus Python `zoneinfo`, separate from the app code. The script will be committed under `analysis/` so the values can be traced.

| Case | Expected |
|---|---|
| Rows after removing duplicates | 12,614 (from 12,626) |
| Account 6, local day 2026-06-03 | 804 events |
| Default `as_of` | 2026-07-27, so the week is 07-20..07-26 and the baseline is 05-25..07-13 |
| Default as-of status counts (69 locations) | 43 typical, 9 slightly above, 6 slightly below, 1 above, 2 below, 8 too little |
| Flagged at default, in order | 15 Site C: 12 vs 4–7, median 6, distance 5/6 · 15 Site B: 2 vs 4–12, median 5.5, distance 4/11 · 14 Site B: 2 vs 4–8, median 6.5, distance 4/13 |
| `as_of` 2026-04-20 status counts | 40 typical, 3 slightly above, 9 slightly below, 1 above, 6 below, 10 too little |
| Account 6 Site G, `as_of` 2026-04-20 (the outage) | 0 vs 2–7, median 5.5, below (4/11); ties with Site I (4/11), and G sorts before I |
| Account 6 Site D (default) | median 4.5, too little activity |
| Account 20 | no locations |
| First as-of where every location has a full baseline | 2026-04-13 |

**5. Frontend (light, phase 5):** Vitest + Testing Library. It renders each status with its text, keeps the order from the API, renders the empty states, and reads and writes the URL state. No end-to-end suite in v1.

**Running tests:** `make test` runs the backend suite in the compose `backend` container against a separate test database.

## 8. Implementation order

Each phase is test-first and ends with a commit. If time runs short, phase 5 is what gets cut.

1. **Skeleton:** repo layout; compose `db`; Alembic schema and index migrations; idempotent seed command.
2. **Rules:** constants module and the pure rule module (median, range, statuses, distance, ranking), with unit tests on synthetic data.
3. **Data:** the queries that remove duplicates, bucket by local week, fill zero weeks and apply the history start, with SQL tests on synthetic rows, then the seed known-answer tests.
4. **Endpoint**, with API tests. Then a **minimal UI**: account picker, as-of picker, URL state, the ranked location list with statuses and ranges. Wire `backend` and `frontend` into compose so `docker compose up --build` runs everything.
5. **Refinement, cut first:** per-type context per location, account totals, frontend tests.
6. **README:** how to run and test, a decision summary pointing to this plan, and next steps (missed-call rate first).

## 9. Out of scope

- Alerting and notifications; ML and forecasting (per product).
- **Missed-call rate and the other rates.** Listed in the README as the next step, with a minimum number of calls; per location it will probably need a 4-week window.
- Configurable week definitions or a rolling window; editable thresholds in the UI.
- Fuzzy deduplication; annotating or excluding anomalies such as the spike.
- Peer or industry benchmarks; year-over-year comparison.
- Authentication and tenant isolation; the account is chosen in the UI.
- Charts beyond the list; mobile polish beyond a responsive layout.

## 10. Where would an LLM fit?

