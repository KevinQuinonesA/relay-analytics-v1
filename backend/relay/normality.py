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
    distance: Fraction | None = None

    @property
    def flagged(self):
        raise NotImplementedError


def assess(location, count, baseline, limits=Thresholds()):
    raise NotImplementedError


def rank(assessments):
    raise NotImplementedError
