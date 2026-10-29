"""Known answers on the real seed.

Every expected value is copied from the output of analysis/reference.py, an
independent implementation (SQLite + zoneinfo, no shared code). Never update
these from the app's own output.
"""
from collections import Counter
from datetime import date
from fractions import Fraction as F

import pytest
from sqlalchemy import text

from relay.summary import weekly_summary
from relay.weekly import default_as_of, location_weeks

ACCOUNTS = range(1, 21)


def ranked(summary):
    return [
        (a.location, a.status.value, a.count, a.median, a.typical_low, a.typical_high, a.distance)
        for a in (loc.assessment for loc in summary.locations)
    ]


def test_exact_duplicates_are_removed(seeded_conn):
    assert seeded_conn.execute(text("SELECT count(*) FROM activity_events")).scalar_one() == 12626
    assert seeded_conn.execute(text("SELECT count(*) FROM activity_events_dedup")).scalar_one() == 12614


def test_spike_week_total_for_account_6(seeded_conn):
    weeks = location_weeks(seeded_conn, 6, date(2026, 6, 1))
    assert sum(lw.weeks[-1].total for lw in weeks) == 880


def test_history_starts(seeded_conn):
    starts = Counter(lw.history_start for a in ACCOUNTS for lw in location_weeks(seeded_conn, a, date(2026, 7, 20)))
    assert starts == {date(2026, 2, 2): 51, date(2026, 2, 9): 18}


def test_default_as_of_and_dates(seeded_conn):
    assert default_as_of(seeded_conn) == date(2026, 7, 27)
    s = weekly_summary(seeded_conn, 15)
    assert (s.as_of, s.week_start, s.week_end) == (date(2026, 7, 27), date(2026, 7, 20), date(2026, 7, 26))
    assert (s.baseline_start, s.baseline_end) == (date(2026, 5, 25), date(2026, 7, 19))


@pytest.mark.parametrize(
    "as_of, expected",
    [
        (date(2026, 7, 27), {"above_typical": 1, "below_typical": 2, "slightly_above": 9, "slightly_below": 6,
                             "too_little_activity": 8, "typical": 43}),
        (date(2026, 4, 20), {"above_typical": 1, "below_typical": 6, "slightly_above": 3, "slightly_below": 9,
                             "too_little_activity": 10, "typical": 40}),
        (date(2026, 4, 13), {"above_typical": 4, "below_typical": 5, "slightly_above": 5, "slightly_below": 4,
                             "too_little_activity": 10, "typical": 41}),
        (date(2026, 4, 6), {"above_typical": 4, "below_typical": 4, "insufficient_history": 18, "slightly_above": 6,
                            "slightly_below": 3, "too_little_activity": 10, "typical": 24}),
    ],
)
def test_status_counts_across_all_locations(seeded_conn, as_of, expected):
    statuses = Counter(
        loc.assessment.status.value
        for a in ACCOUNTS
        for loc in weekly_summary(seeded_conn, a, as_of=as_of).locations
    )
    assert statuses == expected


@pytest.mark.parametrize(
    "as_of, expected",
    [
        (date(2026, 7, 27), {(15, "Site C"), (15, "Site B"), (14, "Site B")}),
        (date(2026, 4, 20), {(11, "Site A"), (2, "Site C"), (14, "Site D"), (1, "Site C"),
                             (6, "Site G"), (6, "Site I"), (1, "Site E")}),
    ],
)
def test_flagged_locations(seeded_conn, as_of, expected):
    flagged = {
        (a, loc.assessment.location)
        for a in ACCOUNTS
        for loc in weekly_summary(seeded_conn, a, as_of=as_of).locations
        if loc.assessment.flagged
    }
    assert flagged == expected


def test_account_15_latest_week(seeded_conn):
    assert ranked(weekly_summary(seeded_conn, 15)) == [
        ("Site C", "above_typical", 12, 6, 4, 7, F(5, 6)),
        ("Site B", "below_typical", 2, F(11, 2), 4, 12, F(4, 11)),
        ("Site A", "typical", 6, F(13, 2), 5, 9, 0),
    ]


def test_account_15_site_b_by_event_type(seeded_conn):
    site_b = next(l for l in weekly_summary(seeded_conn, 15).locations if l.assessment.location == "Site B")
    assert site_b.by_event_type == {"call_received": 0, "lead_created": 1, "appointment_set": 1}


def test_account_6_week_of_site_g_outage(seeded_conn):
    # Site G had no events at all that week; ties with Site I at 4/11 and sorts first by name
    assert ranked(weekly_summary(seeded_conn, 6, as_of=date(2026, 4, 20))) == [
        ("Site G", "below_typical", 0, F(11, 2), 2, 7, F(4, 11)),
        ("Site I", "below_typical", 2, F(11, 2), 4, 9, F(4, 11)),
        ("Site N", "slightly_below", 1, 7, 3, 8, F(2, 7)),
        ("Site E", "slightly_below", 3, 5, 4, 6, F(1, 5)),
        ("Site A", "typical", 7, F(11, 2), 5, 8, 0),
        ("Site C", "typical", 3, 5, 2, 8, 0),
        ("Site J", "typical", 5, 6, 3, 7, 0),
        ("Site K", "typical", 3, 5, 3, 7, 0),
        ("Site L", "typical", 5, 5, 2, 6, 0),
        ("Site O", "typical", 7, 6, 3, 10, 0),
        ("Site B", "too_little_activity", 4, 4, 2, 9, None),
        ("Site D", "too_little_activity", 4, F(9, 2), 4, 7, None),
        ("Site F", "too_little_activity", 6, 4, 3, 5, None),
        ("Site H", "too_little_activity", 1, F(9, 2), 3, 6, None),
        ("Site M", "too_little_activity", 4, F(7, 2), 2, 8, None),
    ]


def test_account_6_latest_week_spike_does_not_widen_ranges(seeded_conn):
    # the 880-event spike week (06-01) is inside this baseline; ranges stay at single digits
    assert ranked(weekly_summary(seeded_conn, 6)) == [
        ("Site A", "typical", 9, 6, 3, 9, 0),
        ("Site B", "typical", 7, 5, 2, 9, 0),
        ("Site C", "typical", 6, 6, 3, 11, 0),
        ("Site E", "typical", 4, 6, 4, 9, 0),
        ("Site F", "typical", 4, 5, 3, 9, 0),
        ("Site H", "typical", 7, 5, 2, 8, 0),
        ("Site K", "typical", 4, 5, 2, 9, 0),
        ("Site L", "typical", 4, F(11, 2), 4, 10, 0),
        ("Site D", "too_little_activity", 4, F(9, 2), 3, 6, None),
        ("Site G", "too_little_activity", 6, F(9, 2), 3, 6, None),
        ("Site I", "too_little_activity", 6, 4, 3, 6, None),
        ("Site J", "too_little_activity", 5, F(7, 2), 3, 11, None),
        ("Site M", "too_little_activity", 7, F(7, 2), 2, 6, None),
        ("Site N", "too_little_activity", 6, F(9, 2), 3, 7, None),
        ("Site O", "too_little_activity", 8, F(9, 2), 3, 9, None),
    ]


def test_account_without_events(seeded_conn):
    assert weekly_summary(seeded_conn, 20).locations == []
