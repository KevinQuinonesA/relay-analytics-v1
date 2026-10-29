"""Aggregation tests on synthetic rows: dedup, local Mon-Sun weeks, zero-fill, history start.

Local times in comments are worked out by hand from the UTC values:
EDT = UTC-4 (from 2026-03-08), EST = UTC-5 (before), PDT = UTC-7, Phoenix MST = UTC-7 all year.
"""
from datetime import date

import pytest

from relay.weekly import location_weeks

NY, PHX, UTC_TZ, LA = 1, 2, 3, 4


@pytest.fixture(autouse=True)
def accounts(rows):
    rows.account(NY, "America/New_York")
    rows.account(PHX, "America/Phoenix")
    rows.account(UTC_TZ, "UTC")
    rows.account(LA, "America/Los_Angeles")


def target_counts(conn, account_id, week):
    """{location: total in the target week}. The last row of each location is the target week."""
    result = {}
    for lw in location_weeks(conn, account_id, week):
        assert lw.weeks[-1].week_start == week
        result[lw.location] = lw.weeks[-1].total
    return result


def totals_by_week(conn, account_id, week):
    return {lw.location: {w.week_start: w.total for w in lw.weeks} for lw in location_weeks(conn, account_id, week)}


# --- local Mon-Sun weeks ------------------------------------------------------------

def test_sunday_late_evening_local_stays_in_its_week(conn, rows):
    rows.event(NY, "Site A", "2026-07-27 03:30:00")  # Sun 07-26 23:30 EDT
    assert target_counts(conn, NY, date(2026, 7, 20)) == {"Site A": 1}
    assert target_counts(conn, NY, date(2026, 7, 27)) == {"Site A": 0}


def test_monday_just_after_midnight_local_starts_the_next_week(conn, rows):
    rows.event(NY, "Site A", "2026-07-27 04:30:00")  # Mon 07-27 00:30 EDT
    assert target_counts(conn, NY, date(2026, 7, 27)) == {"Site A": 1}
    assert target_counts(conn, NY, date(2026, 7, 20)) == {}  # did not exist yet


def test_utc_monday_that_is_still_sunday_locally(conn, rows):
    rows.event(LA, "Site A", "2026-07-20 03:00:00")  # Sun 07-19 20:00 PDT
    assert target_counts(conn, LA, date(2026, 7, 13)) == {"Site A": 1}


def test_before_daylight_saving_uses_standard_offset(conn, rows):
    # Sun 03-01 23:30 EST; a fixed UTC-4 would make it Mon 00:30 (week 03-02)
    rows.event(NY, "Site A", "2026-03-02 04:30:00")
    assert target_counts(conn, NY, date(2026, 2, 23)) == {"Site A": 1}


def test_after_daylight_saving_uses_daylight_offset(conn, rows):
    # Mon 03-16 00:30 EDT; a fixed UTC-5 would make it Sun 23:30 (week 03-09)
    rows.event(NY, "Site A", "2026-03-16 04:30:00")
    assert target_counts(conn, NY, date(2026, 3, 16)) == {"Site A": 1}
    assert target_counts(conn, NY, date(2026, 3, 9)) == {}


def test_phoenix_does_not_observe_daylight_saving(conn, rows):
    rows.event(PHX, "Site A", "2026-07-27 06:30:00")  # Sun 07-26 23:30 MST (Denver would be Mon 00:30)
    assert target_counts(conn, PHX, date(2026, 7, 20)) == {"Site A": 1}


def test_utc_account_week_boundary(conn, rows):
    rows.event(UTC_TZ, "Site A", "2026-07-26 23:59:59")
    rows.event(UTC_TZ, "Site B", "2026-07-27 00:00:00")
    assert target_counts(conn, UTC_TZ, date(2026, 7, 20)) == {"Site A": 1}
    assert target_counts(conn, UTC_TZ, date(2026, 7, 27)) == {"Site A": 0, "Site B": 1}


# --- duplicates -----------------------------------------------------------------------

def test_exact_duplicates_count_once_including_null_columns(conn, rows):
    rows.event(NY, "Site A", "2026-07-21 15:00:00", n=2)  # NULL duration and outcome
    rows.event(NY, "Site A", "2026-07-22 15:00:00", outcome="connected", duration=300, n=2)
    assert target_counts(conn, NY, date(2026, 7, 20)) == {"Site A": 2}


def test_near_duplicates_and_same_second_different_values_are_kept(conn, rows):
    rows.event(NY, "Site A", "2026-07-21 15:00:00", outcome="connected", duration=644)
    rows.event(NY, "Site A", "2026-07-21 15:00:04", outcome="connected", duration=644)
    rows.event(NY, "Site A", "2026-07-22 15:00:00", outcome="connected")
    rows.event(NY, "Site A", "2026-07-22 15:00:00", outcome="missed")
    rows.event(NY, "Site A", "2026-07-23 15:00:00", event_type="call_received")
    rows.event(NY, "Site A", "2026-07-23 15:00:00", event_type="lead_created")
    assert target_counts(conn, NY, date(2026, 7, 20)) == {"Site A": 6}


# --- window, zero-fill, history start ----------------------------------------------------

def test_weeks_without_events_are_zero_filled_within_the_window(conn, rows):
    rows.event(NY, "Site A", "2026-05-05 16:00:00")        # Tue -> history from 05-11; outside the window
    rows.event(NY, "Site A", "2026-06-02 16:00:00", n=2)   # week 06-01
    rows.event(NY, "Site A", "2026-06-16 16:00:00")        # week 06-15
    rows.event(NY, "Site A", "2026-07-21 16:00:00", n=3)   # target week 07-20
    assert totals_by_week(conn, NY, date(2026, 7, 20)) == {
        "Site A": {
            date(2026, 5, 25): 0, date(2026, 6, 1): 2, date(2026, 6, 8): 0, date(2026, 6, 15): 1,
            date(2026, 6, 22): 0, date(2026, 6, 29): 0, date(2026, 7, 6): 0, date(2026, 7, 13): 0,
            date(2026, 7, 20): 3,
        }
    }


@pytest.mark.parametrize(
    "first_utc, history_start",
    [
        ("2026-07-01 16:00:00", date(2026, 7, 6)),  # Wednesday -> next Monday
        ("2026-07-05 16:00:00", date(2026, 7, 6)),  # Sunday -> next day
        ("2026-07-06 16:00:00", date(2026, 7, 6)),  # Monday -> that Monday
    ],
)
def test_history_starts_on_first_monday_on_or_after_first_event(conn, rows, first_utc, history_start):
    rows.event(NY, "Site A", first_utc)
    [lw] = location_weeks(conn, NY, date(2026, 7, 20))
    assert lw.history_start == history_start
    assert [w.week_start for w in lw.weeks] == [date(2026, 7, 6), date(2026, 7, 13), date(2026, 7, 20)]


def test_partial_first_week_is_not_part_of_history(conn, rows):
    rows.event(NY, "Site A", "2026-07-01 16:00:00", n=4)  # week 06-29, before history start 07-06
    [lw] = location_weeks(conn, NY, date(2026, 7, 20))
    assert date(2026, 6, 29) not in {w.week_start for w in lw.weeks}
    assert sum(w.total for w in lw.weeks) == 0


def test_location_first_seen_during_target_week_has_only_the_target_week(conn, rows):
    rows.event(NY, "Site A", "2026-07-22 16:00:00", n=2)  # Wednesday of the target week
    [lw] = location_weeks(conn, NY, date(2026, 7, 20))
    assert lw.history_start == date(2026, 7, 27)
    assert [(w.week_start, w.total) for w in lw.weeks] == [(date(2026, 7, 20), 2)]


def test_location_first_seen_after_target_week_is_excluded(conn, rows):
    rows.event(NY, "Site A", "2026-07-21 16:00:00")
    rows.event(NY, "Site B", "2026-07-28 16:00:00")
    assert target_counts(conn, NY, date(2026, 7, 20)) == {"Site A": 1}


def test_events_after_the_target_week_are_not_counted(conn, rows):
    rows.event(NY, "Site A", "2026-07-21 16:00:00")
    rows.event(NY, "Site A", "2026-07-28 16:00:00", n=5)
    assert target_counts(conn, NY, date(2026, 7, 20)) == {"Site A": 1}


def test_window_is_target_week_plus_eight_baseline_weeks(conn, rows):
    rows.event(NY, "Site A", "2026-01-06 16:00:00")  # long history
    [lw] = location_weeks(conn, NY, date(2026, 7, 20))
    assert [w.week_start for w in lw.weeks][0] == date(2026, 5, 25)
    assert len(lw.weeks) == 9


# --- what is counted -------------------------------------------------------------------------

def test_counts_per_event_type_and_nulls_count_as_volume(conn, rows):
    rows.event(NY, "Site A", "2026-07-21 16:00:00", outcome="connected", duration=60)
    rows.event(NY, "Site A", "2026-07-21 17:00:00")                                # call, NULL outcome
    rows.event(NY, "Site A", "2026-07-22 16:00:00", event_type="lead_created")    # NULL outcome
    rows.event(NY, "Site A", "2026-07-23 16:00:00", event_type="appointment_set", outcome="completed")
    [lw] = location_weeks(conn, NY, date(2026, 7, 20))
    target = lw.weeks[-1]
    assert (target.call_received, target.lead_created, target.appointment_set, target.total) == (2, 1, 1, 4)


def test_same_location_name_in_another_account_is_a_different_location(conn, rows):
    rows.event(NY, "Site A", "2026-07-21 16:00:00")
    rows.event(LA, "Site A", "2026-07-21 16:00:00", n=3)
    assert target_counts(conn, NY, date(2026, 7, 20)) == {"Site A": 1}
    assert target_counts(conn, LA, date(2026, 7, 20)) == {"Site A": 3}


def test_locations_are_returned_in_name_order(conn, rows):
    for name in ("Site C", "Site A", "Site B"):
        rows.event(NY, name, "2026-07-21 16:00:00")
    assert [lw.location for lw in location_weeks(conn, NY, date(2026, 7, 20))] == ["Site A", "Site B", "Site C"]
