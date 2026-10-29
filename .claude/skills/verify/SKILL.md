---
name: verify
description: Audit every number and factual claim about the Relay data before it reaches the user. Use whenever an answer reports counts, averages, medians, percentages, ratios, baselines, date ranges, spikes, gaps, duplicates, nulls or any statement about what the seed data contains or how it is shaped — including summaries, data profiles, ticket analysis and plan inputs — and when the user types /verify or asks "where does that number come from", "check your numbers", "is that right". Re-runs anything not actually executed and corrects mistakes.
---

# Verify data claims

Go back over the answer being verified (the latest one, unless the user names another) and audit it. Do not trust memory of earlier tool output; re-check against the data.

## Steps

1. **List every claim**: each number, and each qualitative statement about the data ("mostly weekdays", "no gaps", "looks like a backfill").
2. **Trace each one** to the exact query or code that produced it in this session, and its raw output.
3. **Re-run** any claim that was eyeballed, rounded from memory, derived by mental arithmetic, or never actually computed. Write the query, run it, and show the raw output.
4. **Flag** claims that come from reasoning or general knowledge (e.g. "probably a backfill", DST rules, industry norms) as `inferred`. These are allowed, but must be labelled as such, never presented as data.
5. **Fix**: if a re-run disagrees with the answer, state the wrong value, the correct value and why it was wrong (wrong slice, wrong denominator, UTC vs local, spike included, no zero-fill...). Carry the fix into anything built on it.

## Data access

Load the seed into a scratch SQLite DB (never into the repo):

```bash
python3 -I -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); [c.executescript(open(f).read()) for f in ('data/schema.sql','data/seed.sql')]; c.commit()" "$SCRATCH/relay.db"
```

Pitfalls to check every time:
- **Time zones**: day/week buckets must be in the account's local time. Use `zoneinfo` (or the DB's tz functions); don't hard-code UTC offsets.
- **Zero-fill**: averages over "days with events" overstate typical activity; build a calendar.
- **Denominators**: per-account vs per-location vs per-week; weekday vs weekend.
- **Outliers and duplicates**: say whether the account 6 spike on 2026-06-03 and the exact duplicate rows are included.
- **Partial periods**: data ends 2026-07-27, so July and the last week are partial.

## Output

Keep it short. One table, then corrections:

| # | Claim | Source (query/code) | Raw output | Status |
|---|---|---|---|---|

Status is one of `verified`, `re-run ✓`, `corrected`, `inferred`. Put long queries in a collapsed block or in a file in the scratchpad and reference it. End with **Corrections**: what changed, or "none".
