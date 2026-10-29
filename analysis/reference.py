"""Independent reference calculation of the DASH-247 rule on the seed.

Shares no code with backend/: SQLite instead of Postgres, Python zoneinfo for
local time, its own median/range/ranking. Its output is copied by hand into
backend/tests/test_seed_known_answers.py; tests never run this script.

    python3 -I analysis/reference.py data/schema.sql data/seed.sql
"""
import collections
import sqlite3
import sys
from datetime import date, datetime, timedelta
from fractions import Fraction
from zoneinfo import ZoneInfo

WEEKS, TRIM, MIN_MEDIAN, MIN_FLAG = 8, 1, 5, Fraction(3, 10)
UTC = ZoneInfo("UTC")

db = sqlite3.connect(":memory:")
for path in sys.argv[1:3]:
    db.executescript(open(path).read())

tz = {a: ZoneInfo(t) for a, t in db.execute("SELECT id, timezone FROM accounts")}
rows = set(db.execute(
    "SELECT account_id, location, event_type, occurred_at, duration_seconds, outcome FROM activity_events"
))  # exact duplicates collapse here
latest_utc = max(datetime.fromisoformat(r[3]) for r in rows)

monday = lambda d: d - timedelta(days=d.weekday())
weekly = collections.Counter()      # (account, location, week) -> total
by_type = collections.Counter()     # (account, location, week, event_type) -> n
first_day = {}
for a, loc, et, ts, _, _ in rows:
    d = datetime.fromisoformat(ts).replace(tzinfo=UTC).astimezone(tz[a]).date()
    weekly[a, loc, monday(d)] += 1
    by_type[a, loc, monday(d), et] += 1
    first_day[a, loc] = min(first_day.get((a, loc), d), d)
history_start = {k: d + timedelta(days=(7 - d.weekday()) % 7) for k, d in first_day.items()}


def median(xs):
    xs = sorted(xs); n = len(xs)
    return Fraction(xs[n // 2]) if n % 2 else Fraction(xs[n // 2 - 1] + xs[n // 2], 2)


def assess_account(account, as_of):
    week = monday(as_of) - timedelta(weeks=1)
    out = []
    for (a, loc), start in history_start.items():
        if a != account or first_day[a, loc] > week + timedelta(days=6):
            continue
        cur = weekly[a, loc, week]
        base_weeks = [week - timedelta(weeks=n) for n in range(WEEKS, 0, -1)]
        if base_weeks[0] < start:
            out.append((loc, "insufficient_history", cur, None, None, None, None)); continue
        b = sorted(weekly[a, loc, w] for w in base_weeks)
        med, lo, hi = median(b), b[TRIM], b[-1 - TRIM]
        if med < MIN_MEDIAN:
            out.append((loc, "too_little_activity", cur, med, lo, hi, None)); continue
        if lo <= cur <= hi:
            out.append((loc, "typical", cur, med, lo, hi, Fraction(0))); continue
        below = cur < lo
        dist = Fraction(lo - cur if below else cur - hi) / med
        status = ("below_typical" if below else "above_typical") if dist >= MIN_FLAG else ("slightly_below" if below else "slightly_above")
        out.append((loc, status, cur, med, lo, hi, dist))
    group = {"above_typical": 0, "below_typical": 0, "slightly_above": 1, "slightly_below": 1,
             "typical": 2, "too_little_activity": 3, "insufficient_history": 4}
    return week, sorted(out, key=lambda r: (group[r[1]], -(r[6] or 0), r[0]))


TYPES = ("call_received", "lead_created", "appointment_set")


def account_totals(account, as_of):
    """Per event type: this week's count, plus median/range over the baseline, summing each
    location's weeks from its own history start (the target week always counts)."""
    week = monday(as_of) - timedelta(weeks=1)
    base_weeks = [week - timedelta(weeks=n) for n in range(WEEKS, 0, -1)]
    locs = [(a, l) for (a, l) in history_start if a == account and first_day[a, l] <= week + timedelta(days=6)]
    out = {}
    for et in TYPES:
        cur = sum(by_type[a, l, week, et] for a, l in locs)
        if not locs or base_weeks[0] < min(history_start[k] for k in locs):
            out[et] = (cur, None, None, None); continue
        b = sorted(sum(by_type[a, l, w, et] for a, l in locs if w >= history_start[a, l]) for w in base_weeks)
        out[et] = (cur, median(b), b[TRIM], b[-1 - TRIM])
    return out


def fmt(r):
    loc, status, cur, med, lo, hi, dist = r
    return f"{loc}: {status} count={cur} median={med} range={lo}..{hi} distance={dist}"


print("rows raw/dedup:", db.execute("SELECT count(*) FROM activity_events").fetchone()[0], len(rows))
print("latest event (UTC):", latest_utc, "-> default as_of", latest_utc.date())
print("account 6 week 2026-06-01 total:", sum(v for (a, _, w), v in weekly.items() if a == 6 and w == date(2026, 6, 1)))
print("history starts:", sorted(collections.Counter(history_start.values()).items()))
for as_of in (date(2026, 7, 27), date(2026, 4, 20), date(2026, 4, 13), date(2026, 4, 6)):
    statuses = collections.Counter(); flagged = []
    for account in sorted(tz):
        week, res = assess_account(account, as_of)
        statuses.update(r[1] for r in res)
        flagged += [(account, r) for r in res if r[1] in ("above_typical", "below_typical")]
    print(f"\nas_of {as_of}: week {week}, baseline {week - timedelta(weeks=WEEKS)}..{week - timedelta(days=1)}")
    print("  statuses:", dict(sorted(statuses.items())))
    for account, r in sorted(flagged, key=lambda x: (-x[1][6], x[0], x[1][0])):
        print(f"  flagged acct {account} {fmt(r)}")
for account, as_of in ((15, date(2026, 7, 27)), (6, date(2026, 4, 20)), (6, date(2026, 7, 27)), (20, date(2026, 7, 27))):
    week, res = assess_account(account, as_of)
    print(f"\naccount {account} as_of {as_of} ranked:")
    for r in res:
        print("  ", fmt(r))
print("\naccount 15 Site B week 2026-07-20 by type:",
      {et: by_type[15, "Site B", date(2026, 7, 20), et] for et in ("call_received", "lead_created", "appointment_set")})
for account, as_of in ((15, date(2026, 7, 27)), (6, date(2026, 4, 20)), (1, date(2026, 3, 2))):
    print(f"account {account} as_of {as_of} totals (count, median, low, high):", account_totals(account, as_of))
print("account 6 Site G week 2026-04-13 by type:",
      {et: by_type[6, "Site G", date(2026, 4, 13), et] for et in TYPES})
