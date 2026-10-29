"""Thin contract tests for the HTTP layer, on the seed.

Expected values: location counts from the initial SQLite profile of the seed;
summary values from analysis/reference.py output.
"""
import pytest
from fastapi.testclient import TestClient

from relay.api import app, get_conn


@pytest.fixture(scope="module")
def client(seeded_conn):
    app.dependency_overrides[get_conn] = lambda: seeded_conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_accounts(client):
    r = client.get("/api/accounts")
    assert r.status_code == 200
    accounts = r.json()
    assert [a["id"] for a in accounts] == list(range(1, 21))
    assert accounts[14] == {"id": 15, "name": "Sierra Pest Solutions", "timezone": "America/Phoenix", "location_count": 3}
    assert {a["id"]: a["location_count"] for a in accounts if a["id"] in (6, 20)} == {6: 15, 20: 0}


def test_weekly_summary_defaults_to_latest_data(client):
    r = client.get("/api/accounts/15/weekly-summary")
    assert r.status_code == 200
    body = r.json()
    assert body["account"] == {"id": 15, "name": "Sierra Pest Solutions", "timezone": "America/Phoenix"}
    assert body["as_of"] == "2026-07-27"
    assert body["week"] == {"start": "2026-07-20", "end": "2026-07-26"}
    assert body["baseline"] == {"start": "2026-05-25", "end": "2026-07-19", "weeks": 8}
    assert body["thresholds"] == {
        "baseline_weeks": 8, "range_trim": 1, "min_baseline_median": 5, "min_flag_distance": 0.3,
    }
    assert [(l["location"], l["status"], l["flagged"]) for l in body["locations"]] == [
        ("Site C", "above_typical", True),
        ("Site B", "below_typical", True),
        ("Site A", "typical", False),
    ]
    assert body["account_totals"] == {
        "call_received": {"count": 9, "median": 12, "typical_low": 11, "typical_high": 19},
        "lead_created": {"count": 6, "median": 3.5, "typical_low": 2, "typical_high": 7},
        "appointment_set": {"count": 5, "median": 3.5, "typical_low": 1, "typical_high": 4},
    }
    site_b = body["locations"][1]
    assert site_b["by_event_type"] == {"call_received": 0, "lead_created": 1, "appointment_set": 1}
    assert (site_b["count"], site_b["median"], site_b["typical_low"], site_b["typical_high"]) == (2, 5.5, 4, 12)
    assert site_b["distance"] == pytest.approx(4 / 11)


def test_weekly_summary_explicit_as_of(client):
    body = client.get("/api/accounts/6/weekly-summary", params={"as_of": "2026-04-20"}).json()
    assert body["week"] == {"start": "2026-04-13", "end": "2026-04-19"}
    assert [l["location"] for l in body["locations"][:2]] == ["Site G", "Site I"]


def test_not_assessable_locations_have_null_fields(client):
    body = client.get("/api/accounts/6/weekly-summary").json()
    site_d = next(l for l in body["locations"] if l["location"] == "Site D")
    assert site_d["status"] == "too_little_activity"
    assert (site_d["median"], site_d["distance"]) == (4.5, None)
    early = client.get("/api/accounts/1/weekly-summary", params={"as_of": "2026-03-02"}).json()
    assert {l["status"] for l in early["locations"]} == {"insufficient_history"}
    assert early["locations"][0]["median"] is None


def test_account_without_events(client):
    body = client.get("/api/accounts/20/weekly-summary").json()
    assert body["locations"] == []


def test_unknown_account_is_404(client):
    assert client.get("/api/accounts/999/weekly-summary").status_code == 404


@pytest.mark.parametrize("as_of", ["2026-13-01", "yesterday", "27-07-2026", "0001-01-01", "0001-02-15", "1999-12-31", "2101-01-01"])
def test_malformed_as_of_is_422(client, as_of):
    assert client.get("/api/accounts/15/weekly-summary", params={"as_of": as_of}).status_code == 422


@pytest.mark.parametrize("as_of", ["2000-01-01", "2100-12-31"])
def test_as_of_range_edges_are_accepted(client, as_of):
    assert client.get("/api/accounts/15/weekly-summary", params={"as_of": as_of}).status_code == 200


def test_weekly_series_for_sparklines(client):
    body = client.get("/api/accounts/15/weekly-summary").json()
    site_c = body["locations"][0]
    assert len(site_c["weeks"]) == 9
    assert site_c["weeks"][0] == {"start": "2026-05-25", "end": "2026-05-31", "count": 4}
    assert site_c["weeks"][-1] == {"start": "2026-07-20", "end": "2026-07-26", "count": 12}
    total = body["account_total"]
    assert (total["count"], total["median"], total["typical_low"], total["typical_high"]) == (20, 19, 15, 24)
    assert [w["count"] for w in total["weeks"]] == [15, 33, 23, 14, 24, 16, 19, 19, 20]


def test_weeks_before_history_are_null(client):
    body = client.get("/api/accounts/1/weekly-summary", params={"as_of": "2026-03-02"}).json()
    assert [w["count"] for w in body["account_total"]["weeks"]][:5] == [None] * 5
    assert body["account_total"]["median"] is None
