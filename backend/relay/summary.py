"""One account's week: aggregation + rule + ranking."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction

from relay.normality import Assessment, Thresholds, assess, rank
from relay.weekly import account_row, account_rows, default_as_of, location_weeks, target_week


EVENT_TYPES = ("call_received", "lead_created", "appointment_set")


@dataclass(frozen=True)
class TypeTotals:
    """Account-wide count for one event type, with its baseline median and typical range (context only)."""
    count: int
    median: Fraction | None
    typical_low: int | None
    typical_high: int | None


@dataclass(frozen=True)
class LocationSummary:
    assessment: Assessment
    by_event_type: dict


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

    weeks = location_weeks(conn, account_id, week, limits.baseline_weeks)
    by_location = {}
    for lw in weeks:
        *baseline, current = lw.weeks
        assessment = assess(lw.location, current.total, [w.total for w in baseline], limits)
        by_location[lw.location] = LocationSummary(assessment, {et: getattr(current, et) for et in EVENT_TYPES})

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
        account_totals=_account_totals(weeks, week, limits),
        locations=[by_location[a.location] for a in rank(l.assessment for l in by_location.values())],
    )


def _account_totals(weeks, week, limits):
    """Sums of the location numbers per event type. The account's baseline starts at its
    earliest location history; each location counts from its own history start, which
    location_weeks already applies (weeks before it are absent)."""
    baseline_weeks = [week - timedelta(weeks=n) for n in range(limits.baseline_weeks, 0, -1)]
    if weeks:
        start = min(lw.history_start for lw in weeks)
        baseline_weeks = [w for w in baseline_weeks if w >= start]
    else:
        baseline_weeks = []
    totals = {}
    for et in EVENT_TYPES:
        per_week = {w: 0 for w in baseline_weeks + [week]}
        for lw in weeks:
            for wc in lw.weeks:
                per_week[wc.week_start] += getattr(wc, et)
        current = per_week.pop(week)
        a = assess(et, current, [per_week[w] for w in baseline_weeks], limits)
        totals[et] = TypeTotals(current, a.median, a.typical_low, a.typical_high)
    return totals
