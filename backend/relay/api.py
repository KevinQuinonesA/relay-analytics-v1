"""HTTP layer: validation and serialization only; the logic is in relay.summary."""
from datetime import date
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine

from relay import summary
from relay.db import database_url
from relay.normality import Status

app = FastAPI(title="Relay weekly normality")

# Outside this range an as_of is a typo, and near year 1 the week arithmetic overflows.
AsOf = Annotated[date | None, Query(ge=date(2000, 1, 1), le=date(2100, 12, 31))]


@lru_cache
def _engine():
    return create_engine(database_url(), pool_pre_ping=True)


def get_conn():
    with _engine().connect() as conn:
        yield conn


class AccountOut(BaseModel):
    id: int
    name: str
    timezone: str
    location_count: int


class AccountRef(BaseModel):
    id: int
    name: str
    timezone: str


class Period(BaseModel):
    start: date
    end: date


class BaselineOut(Period):
    weeks: int


class ThresholdsOut(BaseModel):
    baseline_weeks: int
    range_trim: int
    min_baseline_median: int
    min_flag_distance: float


class EventTypeCounts(BaseModel):
    call_received: int
    lead_created: int
    appointment_set: int


class TypeTotalsOut(BaseModel):
    count: int
    median: float | None
    typical_low: int | None
    typical_high: int | None


class AccountTotalsOut(BaseModel):
    call_received: TypeTotalsOut
    lead_created: TypeTotalsOut
    appointment_set: TypeTotalsOut


class LocationOut(BaseModel):
    location: str
    status: Status
    flagged: bool
    count: int
    median: float | None
    typical_low: int | None
    typical_high: int | None
    distance: float | None  # events beyond the typical range / median
    by_event_type: EventTypeCounts  # context only, not flagged


class WeeklySummaryOut(BaseModel):
    account: AccountRef
    as_of: date
    week: Period
    baseline: BaselineOut
    thresholds: ThresholdsOut
    account_totals: AccountTotalsOut  # context only, not flagged
    locations: list[LocationOut]  # ranked; the client must not re-sort


@app.get("/api/accounts", response_model=list[AccountOut])
def list_accounts(conn=Depends(get_conn)):
    return [AccountOut(**row._mapping) for row in summary.accounts(conn)]


@app.get("/api/accounts/{account_id}/weekly-summary", response_model=WeeklySummaryOut)
def weekly_summary(account_id: int, as_of: AsOf = None, conn=Depends(get_conn)):
    s = summary.weekly_summary(conn, account_id, as_of)
    if s is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return _summary_out(s)


def _summary_out(s):
    t = s.thresholds
    return WeeklySummaryOut(
        account=AccountRef(id=s.account_id, name=s.account_name, timezone=s.timezone),
        as_of=s.as_of,
        week=Period(start=s.week_start, end=s.week_end),
        baseline=BaselineOut(start=s.baseline_start, end=s.baseline_end, weeks=t.baseline_weeks),
        thresholds=ThresholdsOut(
            baseline_weeks=t.baseline_weeks,
            range_trim=t.range_trim,
            min_baseline_median=t.min_baseline_median,
            min_flag_distance=float(t.min_flag_distance),
        ),
        account_totals=AccountTotalsOut(**{
            et: TypeTotalsOut(
                count=t.count, median=_float(t.median), typical_low=t.typical_low, typical_high=t.typical_high,
            )
            for et, t in s.account_totals.items()
        }),
        locations=[
            LocationOut(
                location=loc.assessment.location,
                status=loc.assessment.status,
                flagged=loc.assessment.flagged,
                count=loc.assessment.count,
                median=_float(loc.assessment.median),
                typical_low=loc.assessment.typical_low,
                typical_high=loc.assessment.typical_high,
                distance=_float(loc.assessment.distance),
                by_event_type=EventTypeCounts(**loc.by_event_type),
            )
            for loc in s.locations
        ],
    )


def _float(value):
    return None if value is None else float(value)
