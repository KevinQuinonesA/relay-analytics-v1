"""One account's week: aggregation + rule + ranking."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from relay.normality import Assessment, Thresholds, assess, rank
from relay.weekly import default_as_of, location_weeks, target_week


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
    locations: list  # LocationSummary, ranked


def weekly_summary(conn, account_id, as_of=None, limits=Thresholds()):
    """The ranked weekly summary for one account, or None if the account doesn't exist."""
    account = conn.execute(
        text("SELECT id, name, timezone FROM accounts WHERE id = :id"), {"id": account_id}
    ).one_or_none()
    if account is None:
        return None
    as_of = as_of or default_as_of(conn) or datetime.now(timezone.utc).date()
    week = target_week(as_of)

    by_location = {}
    for lw in location_weeks(conn, account_id, week, limits.baseline_weeks):
        *baseline, current = lw.weeks
        assessment = assess(lw.location, current.total, [w.total for w in baseline], limits)
        by_location[lw.location] = LocationSummary(
            assessment,
            {
                "call_received": current.call_received,
                "lead_created": current.lead_created,
                "appointment_set": current.appointment_set,
            },
        )

    return Summary(
        account_id=account.id,
        account_name=account.name,
        timezone=account.timezone,
        as_of=as_of,
        week_start=week,
        week_end=week + timedelta(days=6),
        baseline_start=week - timedelta(weeks=limits.baseline_weeks),
        baseline_end=week - timedelta(days=1),
        locations=[by_location[a.location] for a in rank(l.assessment for l in by_location.values())],
    )
