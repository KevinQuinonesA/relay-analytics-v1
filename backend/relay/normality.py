"""The weekly normality rule (PLAN.md section 2). Pure functions over weekly counts.

A location's week is compared with the median and the middle of its previous
`baseline_weeks` weeks. Arithmetic is exact (Fraction), so a distance of
exactly `min_flag_distance` is flagged.
"""
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from relay import thresholds


class Status(StrEnum):
    ABOVE_TYPICAL = "above_typical"
    BELOW_TYPICAL = "below_typical"
    SLIGHTLY_ABOVE = "slightly_above"
    SLIGHTLY_BELOW = "slightly_below"
    TYPICAL = "typical"
    TOO_LITTLE_ACTIVITY = "too_little_activity"
    INSUFFICIENT_HISTORY = "insufficient_history"


FLAGGED = {Status.ABOVE_TYPICAL, Status.BELOW_TYPICAL}
SLIGHTLY = {Status.SLIGHTLY_ABOVE, Status.SLIGHTLY_BELOW}
# Ranking groups; within the first two, larger distance first.
GROUP_ORDER = [FLAGGED, SLIGHTLY, {Status.TYPICAL}, {Status.TOO_LITTLE_ACTIVITY}, {Status.INSUFFICIENT_HISTORY}]


@dataclass(frozen=True)
class Thresholds:
    baseline_weeks: int = thresholds.BASELINE_WEEKS
    range_trim: int = thresholds.RANGE_TRIM
    min_baseline_median: int = thresholds.MIN_BASELINE_MEDIAN
    min_flag_distance: Fraction = thresholds.MIN_FLAG_DISTANCE


@dataclass(frozen=True)
class Assessment:
    location: str
    count: int
    status: Status
    median: Fraction | None = None
    typical_low: int | None = None
    typical_high: int | None = None
    # Events beyond the edge of the typical range / median; None when not assessable.
    distance: Fraction | None = None

    @property
    def flagged(self):
        return self.status in FLAGGED


def _median(sorted_counts):
    n = len(sorted_counts)
    mid = n // 2
    if n % 2:
        return Fraction(sorted_counts[mid])
    return Fraction(sorted_counts[mid - 1] + sorted_counts[mid], 2)


def _validate(limits):
    if limits.baseline_weeks < 1 or limits.range_trim < 0 or 2 * limits.range_trim >= limits.baseline_weeks:
        raise ValueError(f"range_trim {limits.range_trim} must leave weeks of {limits.baseline_weeks}")
    if limits.min_baseline_median <= 0:
        raise ValueError("min_baseline_median must be positive (the median divides the distance)")
    if limits.min_flag_distance < 0:
        raise ValueError("min_flag_distance must not be negative")


def assess(location, count, baseline, limits=Thresholds()):
    """Assess this week's `count` against `baseline`: weekly counts before this week, oldest first, zero-filled."""
    _validate(limits)
    if len(baseline) < limits.baseline_weeks:
        return Assessment(location, count, Status.INSUFFICIENT_HISTORY)

    window = sorted(baseline[-limits.baseline_weeks:])
    median = _median(window)
    low, high = window[limits.range_trim], window[-1 - limits.range_trim]
    if median < limits.min_baseline_median:
        return Assessment(location, count, Status.TOO_LITTLE_ACTIVITY, median, low, high)

    if count < low:
        distance, flagged, slightly = Fraction(low - count) / median, Status.BELOW_TYPICAL, Status.SLIGHTLY_BELOW
    elif count > high:
        distance, flagged, slightly = Fraction(count - high) / median, Status.ABOVE_TYPICAL, Status.SLIGHTLY_ABOVE
    else:
        return Assessment(location, count, Status.TYPICAL, median, low, high, Fraction(0))
    status = flagged if distance >= limits.min_flag_distance else slightly
    return Assessment(location, count, status, median, low, high, distance)


def rank(assessments):
    """Flagged first, then slightly outside (each by distance, largest first), then the rest; ties by name."""
    def key(a):
        group = next(i for i, statuses in enumerate(GROUP_ORDER) if a.status in statuses)
        return (group, -(a.distance or 0), a.location)

    return sorted(assessments, key=key)
