"""One account's week: aggregation + rule + ranking."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction

from relay.normality import Assessment, Thresholds, assess, rank
from relay.weekly import account_row, account_rows, account_weeks, default_as_of, location_weeks, target_week


EVENT_TYPES = ("call_received", "lead_created", "appointment_set")


@dataclass(frozen=True)
class TypeTotals:
    """Account-wide count for one event type, with its baseline median and typical range (context only)."""
    count: int
    median: Fraction | None
    typical_low: int | None
    typical_high: int | None


@dataclass(frozen=True)
class AccountTotal:
    """All of the account's events: this week's count, the baseline median and typical range
    (context only, never flagged) and the 9-week series."""
    count: int
    median: Fraction | None
    typical_low: int | None
    typical_high: int | None
    weeks: list  # (week start, count or None before history), oldest first; the last one is this week


@dataclass(frozen=True)
class LocationSummary:
    assessment: Assessment
    by_event_type: dict
    weeks: list  # (week start, count or None before history), oldest first; the last one is this week


@dataclass(frozen=True)
class Summary:
    account_id: int
    account_name: str
    timezone: str
    as_of: date
    week_start: date
    week_end: date
    baseline_start: date
    baseline_end: date
    thresholds: Thresholds
    account_totals: dict  # event type -> TypeTotals
    account_total: AccountTotal
    locations: list  # LocationSummary, ranked


def accounts(conn):
    return account_rows(conn)


def weekly_summary(conn, account_id, as_of=None, limits=Thresholds()):
    """The ranked weekly summary for one account, or None if the account doesn't exist."""
    account = account_row(conn, account_id)
    if account is None:
        return None
    as_of = as_of or default_as_of(conn) or datetime.now(timezone.utc).date()
    week = target_week(as_of)

    window = [week - timedelta(weeks=n) for n in range(limits.baseline_weeks, -1, -1)]
    by_location = {}
    for lw in location_weeks(conn, account_id, week, limits.baseline_weeks):
        *baseline, current = lw.weeks
        assessment = assess(lw.location, current.total, [w.total for w in baseline], limits)
        by_location[lw.location] = LocationSummary(
            assessment, {et: getattr(current, et) for et in EVENT_TYPES}, _series(lw.weeks, window)
        )
    aw = account_weeks(conn, account_id, week, limits.baseline_weeks)

    return Summary(
        account_id=account.id,
        account_name=account.name,
        timezone=account.timezone,
        as_of=as_of,
        week_start=week,
        week_end=week + timedelta(days=6),
        baseline_start=week - timedelta(weeks=limits.baseline_weeks),
        baseline_end=week - timedelta(days=1),
        thresholds=limits,
        account_totals=_account_totals(aw, limits),
        account_total=_account_total(aw, window, limits),
        locations=[by_location[a.location] for a in rank(l.assessment for l in by_location.values())],
    )


def _series(week_counts, window):
    """Totals per week over the window; None for weeks the counts don't cover (before history)."""
    by_week = {w.week_start: w.total for w in week_counts}
    return [(w, by_week.get(w)) for w in window]


def _account_total(aw, window, limits):
    *baseline, current = aw.weeks if aw else [None]
    count = current.total if current else 0
    a = assess("account", count, [w.total for w in baseline], limits)
    weeks = _series(aw.weeks, window) if aw else [(w, None) for w in window[:-1]] + [(window[-1], 0)]
    return AccountTotal(count, a.median, a.typical_low, a.typical_high, weeks)


def _account_totals(aw, limits):
    """Per event type: the account's count this week, with median and typical range over its
    baseline (context only, never flagged). Built from account_weeks, so every event of the
    account counts, including a new location's partial first week."""
    *baseline, current = aw.weeks if aw else [None]
    totals = {}
    for et in EVENT_TYPES:
        count = getattr(current, et) if current else 0
        a = assess(et, count, [getattr(w, et) for w in baseline], limits)
        totals[et] = TypeTotals(count, a.median, a.typical_low, a.typical_high)
    return totals
