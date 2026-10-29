from dataclasses import dataclass
from datetime import date


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
    weeks: list


def target_week(as_of):
    raise NotImplementedError


def default_as_of(conn):
    raise NotImplementedError


def location_weeks(conn, account_id, week):
    raise NotImplementedError
