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


def totals(summary):
    return {et: (t.count, t.median, t.typical_low, t.typical_high) for et, t in summary.account_totals.items()}


def test_account_totals_sum_the_locations(conn, three_sites):
    # calls per baseline week = Site A + Site B (1/week): 11 9 12 11 10 13 11 11
    # sorted 9 10 11 11 11 11 12 13 -> median 11, middle 6 = 10..12; this week 6 (A) + 0 (B) + 2 (C) = 8
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert totals(s) == {
        "call_received": (8, 11, 10, 12),
        "lead_created": (0, 0, 0, 0),
        "appointment_set": (0, 0, 0, 0),
    }


def test_account_baseline_counts_a_new_locations_partial_first_week(conn, rows):
    rows.account(NY, "America/New_York")
    for monday in BASELINE_MONDAYS:
        rows.event(NY, "Site A", f"{monday} 16:00:00", n=10)
    rows.event(NY, "Site B", "2026-06-24 16:00:00", n=5)  # Wed of week 06-22: B's partial first week
    for monday in BASELINE_MONDAYS[-3:]:                  # 06-29, 07-06, 07-13
        rows.event(NY, "Site B", f"{monday} 16:00:00", n=2)
    # weeks: 10 10 10 10 15 (06-22 includes B's 5) 12 12 12
    # sorted 10 10 10 10 12 12 12 15 -> median 11, middle 6 = 10..12
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert totals(s)["call_received"] == (0, 11, 10, 12)


def test_account_baseline_starts_at_the_accounts_own_history_start(conn, rows):
    rows.account(NY, "America/New_York")
    rows.event(NY, "Site A", "2026-05-27 16:00:00", n=7)  # Wed of week 05-25: account history from 06-01
    for monday in BASELINE_MONDAYS[1:]:                   # 06-01 .. 07-13: 7 full weeks
        rows.event(NY, "Site A", f"{monday} 16:00:00", n=10)
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert totals(s)["call_received"] == (0, None, None, None)


def test_account_totals_without_enough_history(conn, rows):
    rows.account(NY, "America/New_York")
    rows.event(NY, "Site A", "2026-07-21 16:00:00", n=3)
    rows.event(NY, "Site A", "2026-07-22 16:00:00", event_type="lead_created")
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert totals(s) == {
        "call_received": (3, None, None, None),
        "lead_created": (1, None, None, None),
        "appointment_set": (0, None, None, None),
    }


def test_account_without_events_has_zero_totals_and_no_baseline(conn, rows):
    rows.account(NY, "America/New_York")
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert set(totals(s).values()) == {(0, None, None, None)}


# --- 9-week series for the sparklines ----------------------------------------------------

WINDOW = BASELINE_MONDAYS + [date(2026, 7, 20)]  # 05-25 .. 07-13, then this week


def test_each_location_has_its_nine_week_series(conn, three_sites):
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    series = {l.assessment.location: [(p.week_start, p.count) for p in l.weeks] for l in s.locations}
    assert series["Site A"] == list(zip(WINDOW, [10, 8, 11, 10, 9, 12, 10, 10, 6]))
    assert series["Site B"] == list(zip(WINDOW, [1] * 8 + [0]))
    # Site C was first seen this week: no history before it
    assert series["Site C"] == list(zip(WINDOW, [None] * 8 + [2]))


def account_total(summary):
    t = summary.account_total
    return (t.count, t.median, t.typical_low, t.typical_high, [p.count for p in t.weeks])


def test_account_total_covers_every_event_with_the_same_rule(conn, three_sites):
    # per week Site A + Site B: 11 9 12 11 10 13 11 11; this week 6 + 0 + 2 = 8
    # sorted 9 10 11 11 11 11 12 13 -> median 11, middle 6 = 10..12
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert account_total(s) == (8, 11, 10, 12, [11, 9, 12, 11, 10, 13, 11, 11, 8])
    assert [p.week_start for p in s.account_total.weeks] == WINDOW


def test_account_total_without_enough_history(conn, rows):
    rows.account(NY, "America/New_York")
    rows.event(NY, "Site A", "2026-07-21 16:00:00", n=3)
    rows.event(NY, "Site A", "2026-07-22 16:00:00", event_type="lead_created")
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert account_total(s) == (4, None, None, None, [None] * 8 + [4])


def test_account_total_for_an_account_without_events(conn, rows):
    rows.account(NY, "America/New_York")
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    assert account_total(s) == (0, None, None, None, [None] * 8 + [0])


def by_type(points):
    return [None if p.by_event_type is None else
            (p.by_event_type["call_received"], p.by_event_type["lead_created"], p.by_event_type["appointment_set"])
            for p in points]


def test_each_week_carries_its_per_type_counts(conn, rows):
    rows.account(NY, "America/New_York")
    for monday in BASELINE_MONDAYS:
        rows.event(NY, "Site A", f"{monday} 16:00:00", n=2)                           # 2 calls every week
    rows.event(NY, "Site A", "2026-06-09 16:00:00", event_type="lead_created")         # week 06-08
    rows.event(NY, "Site A", "2026-06-10 16:00:00", event_type="appointment_set")      # week 06-08
    rows.event(NY, "Site A", "2026-07-21 16:00:00")                                    # this week: 1 call
    rows.event(NY, "Site A", "2026-07-22 16:00:00", event_type="lead_created", n=2)    # this week: 2 leads
    rows.event(NY, "Site B", "2026-07-23 16:00:00", event_type="appointment_set")      # first seen this week
    s = weekly_summary(conn, NY, as_of=date(2026, 7, 27))
    sites = {l.assessment.location: l.weeks for l in s.locations}
    assert by_type(sites["Site A"]) == [(2, 0, 0), (2, 0, 0), (2, 1, 1)] + [(2, 0, 0)] * 5 + [(1, 2, 0)]
    assert by_type(sites["Site B"]) == [None] * 8 + [(0, 0, 1)]
    assert by_type(s.account_total.weeks) == [(2, 0, 0), (2, 0, 0), (2, 1, 1)] + [(2, 0, 0)] * 5 + [(1, 2, 1)]
