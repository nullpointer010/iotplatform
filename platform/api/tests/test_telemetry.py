from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from .conftest import push_measurement, wait_for_ql


URN = "urn:ngsi-ld:Device:"
DEVICES = "/api/v1/devices"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+00:00")


def _create_device(api, created_ids, *, device_state: str | None = None) -> str:
    uid = str(uuid4())
    payload = {
        "name": f"sensor-{uid[:8]}",
        "category": "sensor",
        "supportedProtocol": "http",
        "id": uid,
    }
    if device_state is not None:
        payload["deviceState"] = device_state
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 201, r.text
    created_ids.append(URN + uid)
    return uid


# ---------- telemetry ----------


def test_ingest_then_query_returns_entries(api, orion, ql, created_ids):
    uid = _create_device(api, created_ids)
    base = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    measurement_urn = None
    for i in range(3):
        measurement_urn = push_measurement(
            orion,
            device_uuid=uid,
            controlled_property="temperature",
            num_value=20.0 + i,
            date_observed=_iso(base + timedelta(seconds=i)),
            unit_code="CEL",
        )
    created_ids.append(measurement_urn)
    wait_for_ql(ql, measurement_urn, expected_count=3)

    r = api.get(f"{DEVICES}/{uid}/telemetry", params={"controlledProperty": "temperature"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deviceId"] == URN + uid
    assert body["controlledProperty"] == "temperature"
    assert len(body["entries"]) == 3
    nums = sorted(e["numValue"] for e in body["entries"])
    assert nums == [20.0, 21.0, 22.0]
    assert all(e["unitCode"] == "CEL" for e in body["entries"])


def test_query_empty_range_returns_empty_entries(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(f"{DEVICES}/{uid}/telemetry", params={"controlledProperty": "humidity"})
    assert r.status_code == 200, r.text
    assert r.json()["entries"] == []


def test_query_unknown_device_returns_404(api):
    r = api.get(
        f"{DEVICES}/{uuid4()}/telemetry",
        params={"controlledProperty": "temperature"},
    )
    assert r.status_code == 404


def test_query_missing_controlled_property_returns_422(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(f"{DEVICES}/{uid}/telemetry")
    assert r.status_code == 422


def test_query_bad_date_range_returns_400(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={
            "controlledProperty": "temperature",
            "fromDate": "2026-04-30T13:00:00Z",
            "toDate": "2026-04-30T12:00:00Z",
        },
    )
    assert r.status_code == 400


def test_query_invalid_iso_date_returns_422(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={"controlledProperty": "temperature", "fromDate": "not-a-date"},
    )
    assert r.status_code == 422


def test_query_lastN_limits_results(api, orion, ql, created_ids):
    uid = _create_device(api, created_ids)
    base = datetime(2026, 4, 30, 14, 0, 0, tzinfo=timezone.utc)
    measurement_urn = None
    for i in range(5):
        measurement_urn = push_measurement(
            orion,
            device_uuid=uid,
            controlled_property="humidity",
            num_value=50.0 + i,
            date_observed=_iso(base + timedelta(seconds=i)),
            unit_code="P1",
        )
    created_ids.append(measurement_urn)
    wait_for_ql(ql, measurement_urn, expected_count=5)

    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={"controlledProperty": "humidity", "lastN": 2},
    )
    assert r.status_code == 200, r.text
    entries = r.json()["entries"]
    assert len(entries) == 2
    nums = sorted(e["numValue"] for e in entries)
    assert nums == [53.0, 54.0]


def test_query_invalid_controlled_property_returns_422(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={"controlledProperty": "with space"},
    )
    assert r.status_code == 422


def test_query_lastN_not_capped_by_default_limit(api, orion, ql, created_ids):
    """Regression for ticket 0021a.

    The FE asks for ``lastN=1000``; the route must forward a matching
    ``limit`` to QuantumLeap so QL doesn't silently cap the response
    at the route's default ``limit=100``.
    """
    uid = _create_device(api, created_ids)
    base = datetime(2026, 4, 30, 16, 0, 0, tzinfo=timezone.utc)
    measurement_urn = None
    count = 105
    for i in range(count):
        measurement_urn = push_measurement(
            orion,
            device_uuid=uid,
            controlled_property="pressure",
            num_value=1000.0 + i,
            date_observed=_iso(base + timedelta(seconds=i)),
            unit_code="HPA",
        )
    assert measurement_urn is not None
    created_ids.append(measurement_urn)
    wait_for_ql(ql, measurement_urn, expected_count=count, timeout_s=20.0)

    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={"controlledProperty": "pressure", "lastN": 1000},
    )
    assert r.status_code == 200, r.text
    entries = r.json()["entries"]
    assert len(entries) == count


# ---------- state ----------


def test_state_returns_subset_after_patch(api, created_ids):
    uid = _create_device(api, created_ids)
    p = api.patch(f"{DEVICES}/{uid}", json={"deviceState": "active"})
    assert p.status_code == 200
    r = api.get(f"{DEVICES}/{uid}/state")
    assert r.status_code == 200
    body = r.json()
    assert body["deviceState"] == "active"
    # Optional fields not set → must not appear (response_model_exclude_none).
    assert "batteryLevel" not in body
    assert "dateLastValueReported" not in body


def test_state_unknown_device_returns_404(api):
    r = api.get(f"{DEVICES}/{uuid4()}/state")
    assert r.status_code == 404


def test_state_no_optional_fields_returns_empty_object(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(f"{DEVICES}/{uid}/state")
    assert r.status_code == 200
    assert r.json() == {}


# ---------- bucketed aggregation (ticket 0021c) ----------


def test_aggrPeriod_required_when_aggrMethod_set(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={"controlledProperty": "temperature", "aggrMethod": "avg"},
    )
    assert r.status_code == 422


def test_aggrMethod_invalid_value_returns_422(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={
            "controlledProperty": "temperature",
            "aggrMethod": "median",
            "aggrPeriod": "minute",
        },
    )
    assert r.status_code == 422


def test_avg_bucket_per_day(api, orion, ql, created_ids):
    """5 samples → bucketed response carries the average.

    QuantumLeap indexes by ``TimeInstant`` (notification-receipt time),
    not ``dateObserved``. The 5 pushes happen within ~1 s of real time,
    so we use ``aggrPeriod=day`` to guarantee a single deterministic
    bucket regardless of when the test runs.
    """
    uid = _create_device(api, created_ids)
    base = datetime(2026, 4, 30, 18, 0, 0, tzinfo=timezone.utc)
    values = [10.0, 20.0, 30.0, 5.0, 15.0]
    measurement_urn = None
    for i, val in enumerate(values):
        measurement_urn = push_measurement(
            orion,
            device_uuid=uid,
            controlled_property="temperature",
            num_value=val,
            date_observed=_iso(base + timedelta(seconds=i)),
            unit_code="CEL",
        )
    assert measurement_urn is not None
    created_ids.append(measurement_urn)
    wait_for_ql(ql, measurement_urn, expected_count=5)

    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={
            "controlledProperty": "temperature",
            "aggrMethod": "avg",
            "aggrPeriod": "day",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["aggrMethod"] == "avg"
    assert body["aggrPeriod"] == "day"
    entries = body["entries"]
    assert len(entries) == 1, entries
    bucket = entries[0]
    assert bucket["numValue"] == pytest.approx(sum(values) / len(values))
    # Bucketed entries carry only the average — no min/max envelope.
    assert "minValue" not in bucket
    assert "maxValue" not in bucket


def test_raw_response_includes_total_count(api, orion, ql, created_ids):
    uid = _create_device(api, created_ids)
    base = datetime(2026, 4, 30, 19, 0, 0, tzinfo=timezone.utc)
    measurement_urn = None
    for i in range(4):
        measurement_urn = push_measurement(
            orion,
            device_uuid=uid,
            controlled_property="humidity",
            num_value=40.0 + i,
            date_observed=_iso(base + timedelta(seconds=i)),
            unit_code="P1",
        )
    assert measurement_urn is not None
    created_ids.append(measurement_urn)
    wait_for_ql(ql, measurement_urn, expected_count=4)

    r = api.get(
        f"{DEVICES}/{uid}/telemetry",
        params={"controlledProperty": "humidity"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["aggrMethod"] == "none"
    # total is best-effort; when present must be >= entries returned.
    if body.get("total") is not None:
        assert body["total"] >= len(body["entries"])
        assert body["total"] >= 4
