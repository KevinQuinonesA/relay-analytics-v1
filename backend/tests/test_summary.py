"""Wiring of aggregation + rule into one account summary, on synthetic rows."""
from datetime import date, timedelta
from fractions import Fraction

import pytest

from relay.normality import Status, Thresholds
from relay.summary import weekly_summary
from relay.weekly import default_as_of, target_week

NY = 1
BASELINE_MONDAYS = [date(2026, 5, 25) + timedelta(weeks=n) for n in range(8)]  # 05-25 .. 07-13


@pytest.mark.parametrize(
    "as_of, week",
    [
        (date(2026, 7, 27), date(2026, 7, 20)),  # Monday: last week is complete
        (date(2026, 7, 26), date(2026, 7, 13)),  # Sunday: the week ending today is not complete
        (date(2026, 7, 28), date(2026, 7, 20)),
    ],
)
def test_target_week_is_last_complete_week_before_as_of(as_of, week):
    assert target_week(as_of) == week


def test_default_as_of_is_utc_date_of_latest_event(conn, rows):
    assert default_as_of(conn) is None
    rows.account(NY, "America/New_York")
    rows.event(NY, "Site A", "2026-07-20 12:00:00")
    rows.event(NY, "Site A", "2026-07-27 22:20:34")
    assert default_as_of(conn) == date(2026, 7, 27)


@pytest.fixture
def three_sites(rows):
    rows.account(NY, "America/New_York", name="Summit")
    # Mondays 16:00 UTC = 12:00 EDT, so history starts 05-25 and 8 full baseline weeks exist
    for monday, n in zip(BASELINE_MONDAYS, [10, 8, 11, 10, 9, 12, 10, 10]):
        rows.event(NY, "Site A", f"{monday} 16:00:00", n=n)
    for monday in BASELINE_MONDAYS:
        rows.event(NY, "Site B", f"{monday} 16:00:00")
    rows.event(NY, "Site A", "2026-07-21 16:00:00", n=6)  # target: (9 - 6) / 10 = 3/10 -> below
    rows.event(NY, "Site C", "2026-07-22 16:00:00", n=2)  # first seen this week


def test_summary_assesses_and_ranks_each_location(conn, three_sites):
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert (s.account_id, s.account_name, s.timezone) == (NY, "Summit", "America/New_York")
    assert (s.as_of, s.week_start, s.week_end) == (date(2026, 7, 27), date(2026, 7, 20), date(2026, 7, 26))
    assert (s.baseline_start, s.baseline_end) == (date(2026, 5, 25), date(2026, 7, 19))
    assert [(l.assessment.location, l.assessment.status, l.assessment.count) for l in s.locations] == [
        ("Site A", Status.BELOW_TYPICAL, 6),
        ("Site B", Status.TOO_LITTLE_ACTIVITY, 0),
        ("Site C", Status.INSUFFICIENT_HISTORY, 2),
    ]
    a = s.locations[0].assessment
    assert (a.median, a.typical_low, a.typical_high, a.distance) == (10, 9, 11, Fraction(3, 10))
    assert s.locations[0].by_event_type == {"call_received": 6, "lead_created": 0, "appointment_set": 0}


def test_summary_defaults_as_of_to_latest_event(conn, three_sites, rows):
    rows.event(NY, "Site B", "2026-07-27 22:20:34")
    s = weekly_summary(conn, NY)
    assert (s.as_of, s.week_start) == (date(2026, 7, 27), date(2026, 7, 20))


def test_summary_passes_thresholds_through(conn, three_sites):
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27), limits=Thresholds(min_flag_distance=Fraction(1, 2)))
    assert s.locations[0].assessment.status is Status.SLIGHTLY_BELOW


def test_unknown_account_is_none(conn, three_sites):
    assert weekly_summary(conn, 999, as_of=date(2026, 7, 27)) is None


def test_account_without_events_has_no_locations(conn, three_sites, rows):
    rows.account(2, "America/Chicago")
    assert weekly_summary(conn, 2, as_of=date(2026, 7, 27)).locations == []
