"""Weekly counts per location in the account's local time (PLAN.md section 4).

Weeks are Monday-Sunday in the account's IANA timezone. A location's history
starts on the first Monday on or after its first event, so a partial first
week never enters a baseline; weeks inside the history with no events are 0.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import text

from relay import thresholds


@dataclass(frozen=True)
class WeekCounts:
    week_start: date
    call_received: int
    lead_created: int
    appointment_set: int
    total: int


@dataclass(frozen=True)
class LocationWeeks:
    location: str
    history_start: date
    weeks: list  # WeekCounts, oldest first; the last one is the target week


def target_week(as_of):
    """Monday of the last complete Mon-Sun week that ends before `as_of`."""
    return as_of - timedelta(days=as_of.weekday()) - timedelta(weeks=1)


def default_as_of(conn):
    """UTC date of the latest event in the whole dataset (one as-of for every account)."""
    return conn.execute(text("SELECT max(occurred_at)::date FROM activity_events")).scalar_one()


WEEKS_SQL = text(
    """
    WITH events AS (
        SELECT e.location, e.event_type,
               ((e.occurred_at AT TIME ZONE 'UTC') AT TIME ZONE a.timezone)::date AS local_day
        FROM activity_events_dedup e
        JOIN accounts a ON a.id = e.account_id
        WHERE e.account_id = :account_id
    ),
    locations AS (
        SELECT location,
               date_trunc('week', min(local_day)::timestamp)::date
                 + CASE WHEN extract(isodow FROM min(local_day)) = 1 THEN 0 ELSE 7 END AS history_start
        FROM events
        GROUP BY location
        HAVING min(local_day) <= :target_end
    ),
    weeks AS (
        SELECT generate_series(CAST(:window_start AS timestamp), CAST(:target_week AS timestamp),
                               interval '1 week')::date AS week_start
    ),
    counts AS (
        SELECT location, date_trunc('week', local_day::timestamp)::date AS week_start,
               count(*) FILTER (WHERE event_type = 'call_received') AS call_received,
               count(*) FILTER (WHERE event_type = 'lead_created') AS lead_created,
               count(*) FILTER (WHERE event_type = 'appointment_set') AS appointment_set,
               count(*) AS total
        FROM events
        WHERE local_day BETWEEN :window_start AND :target_end
        GROUP BY 1, 2
    )
    SELECT l.location, l.history_start, w.week_start,
           coalesce(c.call_received, 0), coalesce(c.lead_created, 0),
           coalesce(c.appointment_set, 0), coalesce(c.total, 0)
    FROM locations l
    CROSS JOIN weeks w
    LEFT JOIN counts c ON c.location = l.location AND c.week_start = w.week_start
    WHERE w.week_start >= l.history_start OR w.week_start = :target_week
    ORDER BY l.location, w.week_start
    """
)


def location_weeks(conn, account_id, week, baseline_weeks=thresholds.BASELINE_WEEKS):
    """Each location's counts for `week` and the `baseline_weeks` before it (within its history)."""
    params = {
        "account_id": account_id,
        "target_week": week,
        "target_end": week + timedelta(days=6),
        "window_start": week - timedelta(weeks=baseline_weeks),
    }
    result = {}
    for location, history_start, week_start, *counts in conn.execute(WEEKS_SQL, params):
        lw = result.setdefault(location, LocationWeeks(location, history_start, []))
        lw.weeks.append(WeekCounts(week_start, *counts))
    return list(result.values())


ACCOUNTS_SQL = text(
    """
    SELECT a.id, a.name, a.timezone, count(DISTINCT e.location) AS location_count
    FROM accounts a
    LEFT JOIN activity_events_dedup e ON e.account_id = a.id
    GROUP BY a.id, a.name, a.timezone
    ORDER BY a.id
    """
)


def account_rows(conn):
    """Every account with its number of locations (id, name, timezone, location_count)."""
    return conn.execute(ACCOUNTS_SQL).all()
