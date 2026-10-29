"""Tunable thresholds for the weekly normality rule (PLAN.md D3-D6, D13)."""
from fractions import Fraction

BASELINE_WEEKS = 8
RANGE_TRIM = 1
MIN_BASELINE_MEDIAN = 5
MIN_FLAG_DISTANCE = Fraction(3, 10)
