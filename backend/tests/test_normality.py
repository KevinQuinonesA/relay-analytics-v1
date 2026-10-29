"""Rule tests on synthetic weekly counts. Expected values are worked by hand in the comments."""
import random
from fractions import Fraction

import pytest

from relay import thresholds
from relay.normality import Status, Thresholds, assess, rank

# sorted: 8 9 10 10 10 10 11 12 -> median 10, middle 6 = 9..11
STEADY_10 = [10, 8, 11, 10, 9, 12, 10, 10]


def test_defaults_are_the_agreed_constants():
    assert thresholds.BASELINE_WEEKS == 8
    assert thresholds.RANGE_TRIM == 1
    assert thresholds.MIN_BASELINE_MEDIAN == 5
    assert thresholds.MIN_FLAG_DISTANCE == Fraction(3, 10)
    assert Thresholds() == Thresholds(8, 1, 5, Fraction(3, 10))


# --- median and typical range -------------------------------------------------

def test_median_of_even_baseline_and_middle_six_range():
    # sorted 5..12: median (8+9)/2 = 8.5, drop 5 and 12 -> 6..11
    a = assess("Site A", 9, [12, 5, 9, 6, 11, 8, 10, 7])
    assert a.median == Fraction(17, 2)
    assert (a.typical_low, a.typical_high) == (6, 11)


def test_range_with_ties():
    # sorted 4 4 4 4 6 6 6 6: median 5, middle 6 = 4..6
    a = assess("Site A", 5, [6, 4, 6, 4, 6, 4, 6, 4])
    assert a.median == 5
    assert (a.typical_low, a.typical_high) == (4, 6)


def test_one_huge_week_does_not_move_median_or_range():
    # sorted 8 9 10 10 10 11 12 200: median 10, middle 6 = 9..12
    a = assess("Site A", 10, [10, 9, 200, 10, 8, 11, 12, 10])
    assert a.median == 10
    assert (a.typical_low, a.typical_high) == (9, 12)
    assert a.status is Status.TYPICAL


def test_only_the_most_recent_baseline_weeks_are_used():
    # baseline is oldest -> newest; the two oldest weeks (100s) fall outside the 8-week window
    a = assess("Site A", 10, [100, 100] + STEADY_10)
    assert a.median == 10
    assert (a.typical_low, a.typical_high) == (9, 11)


# --- status inside / at edges / outside ------------------------------------------

@pytest.mark.parametrize("count", [9, 10, 11])
def test_inside_range_or_on_its_edges_is_typical(count):
    a = assess("Site A", count, STEADY_10)
    assert a.status is Status.TYPICAL
    assert a.distance == 0
    assert a.flagged is False


def test_slightly_below_shows_range_without_flag():
    # (9 - 7) / 10 = 0.2 < 0.3
    a = assess("Site A", 7, STEADY_10)
    assert a.status is Status.SLIGHTLY_BELOW
    assert a.distance == Fraction(1, 5)
    assert a.flagged is False
    assert (a.typical_low, a.typical_high) == (9, 11)


def test_exactly_min_flag_distance_below_is_flagged():
    # (9 - 6) / 10 = 3/10 exactly
    a = assess("Site A", 6, STEADY_10)
    assert a.status is Status.BELOW_TYPICAL
    assert a.distance == Fraction(3, 10)
    assert a.flagged is True


def test_exactly_min_flag_distance_above_is_flagged():
    # sorted 17 18 19 20 20 21 22 23: median 20, middle 6 = 18..22; (28 - 22) / 20 = 3/10
    baseline = [20, 17, 23, 19, 21, 18, 22, 20]
    a = assess("Site A", 28, baseline)
    assert a.median == 20
    assert a.status is Status.ABOVE_TYPICAL
    assert a.distance == Fraction(3, 10)


def test_just_under_min_flag_distance_above_is_slightly_above():
    # sorted 8 9 10 10 11 11 12 13: median 10.5, middle 6 = 9..12
    # 15: (15 - 12) / 10.5 = 2/7 ~ 0.286 -> slightly; 16: 4/10.5 = 8/21 ~ 0.381 -> flagged
    baseline = [11, 8, 13, 10, 12, 9, 11, 10]
    slightly = assess("Site A", 15, baseline)
    assert slightly.status is Status.SLIGHTLY_ABOVE
    assert slightly.distance == Fraction(2, 7)
    flagged = assess("Site A", 16, baseline)
    assert flagged.status is Status.ABOVE_TYPICAL
    assert flagged.distance == Fraction(8, 21)


def test_far_above_is_flagged_with_distance_relative_to_median():
    # (200 - 11) / 10 = 189/10
    a = assess("Site A", 200, STEADY_10)
    assert a.status is Status.ABOVE_TYPICAL
    assert a.distance == Fraction(189, 10)


# --- minimum volume on the baseline ---------------------------------------------

def test_drop_to_zero_is_flagged_when_baseline_median_meets_minimum():
    # sorted 3 4 5 5 5 5 6 7: median 5, middle 6 = 4..6; (4 - 0) / 5 = 4/5
    a = assess("Site A", 0, [5, 3, 7, 5, 4, 6, 5, 5])
    assert a.status is Status.BELOW_TYPICAL
    assert a.distance == Fraction(4, 5)


def test_baseline_median_below_minimum_is_too_little_activity_even_at_zero():
    # sorted 3 3 4 4 5 5 6 6: median 4.5 < 5
    a = assess("Site A", 0, [3, 6, 4, 5, 3, 6, 4, 5])
    assert a.status is Status.TOO_LITTLE_ACTIVITY
    assert a.median == Fraction(9, 2)
    assert (a.typical_low, a.typical_high) == (3, 6)
    assert a.distance is None
    assert a.flagged is False


def test_too_little_activity_ignores_this_weeks_count():
    # the minimum applies to the baseline, so a jump from a tiny baseline is still "too little to tell"
    a = assess("Site A", 40, [2, 1, 3, 2, 2, 1, 3, 2])
    assert a.status is Status.TOO_LITTLE_ACTIVITY


def test_all_zero_baseline_is_too_little_activity_without_dividing_by_zero():
    a = assess("Site A", 3, [0] * 8)
    assert a.status is Status.TOO_LITTLE_ACTIVITY
    assert a.median == 0


# --- history ----------------------------------------------------------------------

@pytest.mark.parametrize("baseline", [[], [10] * 7])
def test_fewer_than_baseline_weeks_is_insufficient_history(baseline):
    a = assess("Site A", 10, baseline)
    assert a.status is Status.INSUFFICIENT_HISTORY
    assert (a.median, a.typical_low, a.typical_high, a.distance) == (None, None, None, None)
    assert a.count == 10
    assert a.flagged is False


# --- thresholds are parameters, not literals ----------------------------------------

def test_lower_flag_distance_turns_slightly_below_into_flagged():
    # distance 1/5 from test_slightly_below...
    a = assess("Site A", 7, STEADY_10, Thresholds(min_flag_distance=Fraction(1, 5)))
    assert a.status is Status.BELOW_TYPICAL


def test_lower_minimum_median_makes_small_baseline_assessable():
    # median 4.5, middle 6 = 3..6; (3 - 0) / 4.5 = 2/3
    a = assess("Site A", 0, [3, 6, 4, 5, 3, 6, 4, 5], Thresholds(min_baseline_median=4))
    assert a.status is Status.BELOW_TYPICAL
    assert a.distance == Fraction(2, 3)


def test_shorter_baseline_window():
    # last 4 weeks of STEADY_10 are 9 12 10 10 -> sorted 9 10 10 12: median 10, trim 1 -> 10..10
    a = assess("Site A", 11, STEADY_10, Thresholds(baseline_weeks=4))
    assert a.median == 10
    assert (a.typical_low, a.typical_high) == (10, 10)
    assert a.status is Status.SLIGHTLY_ABOVE  # (11 - 10) / 10 = 1/10
    assert assess("Site A", 10, [10] * 3, Thresholds(baseline_weeks=4)).status is Status.INSUFFICIENT_HISTORY


def test_no_trim_uses_min_max():
    a = assess("Site A", 10, STEADY_10, Thresholds(range_trim=0))
    assert (a.typical_low, a.typical_high) == (8, 12)


@pytest.mark.parametrize("bad", [Thresholds(baseline_weeks=2, range_trim=1), Thresholds(baseline_weeks=0)])
def test_trim_must_leave_at_least_one_week(bad):
    with pytest.raises(ValueError):
        assess("Site A", 10, [10] * 8, bad)


@pytest.mark.parametrize(
    "bad",
    [
        Thresholds(min_baseline_median=0),          # baseline [0 0 0 0 0 0 3 9] -> median 0 -> divide by zero
        Thresholds(min_baseline_median=-1),
        Thresholds(range_trim=-1),                  # would invert the range (high < low)
        Thresholds(min_flag_distance=Fraction(-1, 10)),
    ],
)
def test_thresholds_outside_their_valid_range_are_rejected(bad):
    with pytest.raises(ValueError):
        assess("Site A", 5, [0, 0, 0, 0, 0, 0, 3, 9], bad)


# --- ranking ------------------------------------------------------------------------

def make(location, count, baseline=STEADY_10):
    return assess(location, count, baseline)


def test_rank_orders_flagged_then_slightly_then_typical_then_little_then_no_history():
    below = make("Site B", 1)            # (9 - 1) / 10 = 4/5, flagged
    above = make("Site A", 16)           # (16 - 11) / 10 = 1/2, flagged
    slightly_below = make("Site D", 7)   # 1/5
    slightly_above = make("Site C", 12)  # 1/10
    typical = make("Site E", 10)
    little = make("Site F", 0, [1] * 8)
    no_history = make("Site G", 5, [5] * 3)
    shuffled = [typical, no_history, slightly_above, little, below, slightly_below, above]
    assert [a.location for a in rank(shuffled)] == [
        "Site B", "Site A", "Site D", "Site C", "Site E", "Site F", "Site G",
    ]


def test_rank_breaks_distance_ties_by_location_name():
    # both (9 - 5) / 10 = 2/5
    i, g = make("Site I", 5), make("Site G", 5)
    assert i.distance == g.distance
    assert [a.location for a in rank([i, g])] == ["Site G", "Site I"]


def test_rank_sorts_unflagged_groups_by_name():
    names = ["Site C", "Site A", "Site B"]
    typical = [make(n, 10) for n in names]
    little = [make(n, 0, [1] * 8) for n in names]
    assert [a.location for a in rank(little + typical)] == ["Site A", "Site B", "Site C"] * 2


def test_rank_does_not_depend_on_input_order():
    items = [make(f"Site {c}", n) for c, n in zip("ABCDEFGH", [0, 3, 6, 7, 10, 12, 16, 30])]
    expected = [a.location for a in rank(items)]
    for seed in range(5):
        shuffled = items[:]
        random.Random(seed).shuffle(shuffled)
        assert [a.location for a in rank(shuffled)] == expected


def test_zero_flag_distance_is_allowed_and_flags_anything_outside_the_range():
    # option (a) from the plan: (9 - 8) / 10 = 1/10 >= 0 -> flagged
    assert assess("Site A", 8, STEADY_10, Thresholds(min_flag_distance=Fraction(0))).status is Status.BELOW_TYPICAL
