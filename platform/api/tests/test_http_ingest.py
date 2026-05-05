"""HTTP/LoRaWAN ingest endpoint tests (ticket 0019)."""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable

import httpx
import pytest

from tests.conftest import API_BASE


def _wait_until(predicate: Callable[[], Any], timeout_s: float = 5.0, interval: float = 0.25) -> Any:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        v = predicate()
        if v:
            return v
        time.sleep(interval)
    return None


def _make_http_device(
    api: httpx.Client,
    created_ids: list[str],
    data_types: dict[str, str] | None = None,
) -> str:
    dev_uuid = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "id": dev_uuid,
        "category": "sensor",
        "name": f"http-test-{dev_uuid[:6]}",
        "supportedProtocol": "http",
    }
    # `dataTypes` belongs to the mqtt protocol bag, but we accept it for
    # http devices via Orion (the API does not gate it on protocol). We
    # set it here to drive the ingest validation.
    if data_types:
        payload["dataTypes"] = data_types
        payload["supportedProtocol"] = "mqtt"  # only mqtt protocol carries dataTypes
        payload["mqttTopicRoot"] = f"test-http/{dev_uuid[:8]}"
        payload["mqttClientId"] = f"http-sensor-{dev_uuid[:6]}"
    r = api.post("/api/v1/devices", json=payload)
    assert r.status_code == 201, r.text
    eid = r.json()["id"]
    created_ids.append(eid)
    return eid


def _issue_key(api: httpx.Client, eid: str) -> str:
    r = api.post(f"/api/v1/devices/{eid}/ingest-key")
    assert r.status_code == 201, r.text
    return r.json()["key"]


@pytest.fixture
def anon() -> httpx.Client:
    """A client without the admin Bearer (used to call ingest with only X-Device-Key)."""
    with httpx.Client(base_url=API_BASE, timeout=30.0) as c:
        yield c


# ─── key management ─────────────────────────────────────────────────


def test_issue_then_rotate_changes_key(api, created_ids):
    eid = _make_http_device(api, created_ids)
    r1 = api.post(f"/api/v1/devices/{eid}/ingest-key")
    assert r1.status_code == 201, r1.text
    k1 = r1.json()["key"]
    assert k1.startswith("dik_")
    r2 = api.post(f"/api/v1/devices/{eid}/ingest-key")
    assert r2.status_code == 201
    k2 = r2.json()["key"]
    assert k1 != k2


def test_revoke_then_ingest_unauthorized(api, anon, created_ids):
    eid = _make_http_device(api, created_ids)
    key = _issue_key(api, eid)
    # delete (admin client = api fixture is admin)
    r = api.delete(f"/api/v1/devices/{eid}/ingest-key")
    assert r.status_code == 204
    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={"controlledProperty": "temperature", "value": 1.0},
        headers={"X-Device-Key": key},
    )
    assert r.status_code == 401


def test_ingest_key_endpoint_requires_role(anon, api, created_ids):
    eid = _make_http_device(api, created_ids)
    r = anon.post(f"/api/v1/devices/{eid}/ingest-key")
    assert r.status_code == 401  # no bearer


# ─── ingest happy paths ─────────────────────────────────────────────


def test_ingest_single_lands_in_state_and_telemetry(api, anon, orion, created_ids):
    eid = _make_http_device(api, created_ids)
    key = _issue_key(api, eid)

    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={"controlledProperty": "temperature", "value": 24.7},
        headers={"X-Device-Key": key},
    )
    assert r.status_code == 202, r.text
    assert r.json() == {"accepted": 1}

    state = _wait_until(
        lambda: (
            api.get(f"/api/v1/devices/{eid}/state").json()
            if api.get(f"/api/v1/devices/{eid}/state").status_code == 200
            and api.get(f"/api/v1/devices/{eid}/state").json().get("attributes", {}).get("temperature", {}).get("value") == 24.7
            else None
        ),
        timeout_s=4.0,
    )
    assert state is not None
    assert state.get("dateLastValueReported")

    entries = _wait_until(
        lambda: (
            api.get(
                f"/api/v1/devices/{eid}/telemetry",
                params={"controlledProperty": "temperature", "limit": 10},
            ).json().get("entries")
            if api.get(
                f"/api/v1/devices/{eid}/telemetry",
                params={"controlledProperty": "temperature", "limit": 10},
            ).status_code == 200
            and api.get(
                f"/api/v1/devices/{eid}/telemetry",
                params={"controlledProperty": "temperature", "limit": 10},
            ).json().get("entries")
            else None
        ),
        timeout_s=8.0,
    )
    assert entries
    assert any(e["numValue"] == 24.7 for e in entries)

    device_uuid = eid.rsplit(":", 1)[-1]
    m_urn = f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:Temperature"
    created_ids.append(m_urn)


def test_ingest_batch_two_yields_two_entries(api, anon, created_ids):
    eid = _make_http_device(api, created_ids)
    key = _issue_key(api, eid)

    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={
            "measurements": [
                {"controlledProperty": "humidity", "value": 60.0},
                {"controlledProperty": "humidity", "value": 61.0},
            ]
        },
        headers={"X-Device-Key": key},
    )
    assert r.status_code == 202, r.text
    assert r.json() == {"accepted": 2}

    device_uuid = eid.rsplit(":", 1)[-1]
    created_ids.append(f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:Humidity")

    # The second value overwrites the first in Orion; QL records both
    # snapshots over time. Sleep briefly between the two so QL has a
    # distinct time_index. Our two-shot was a single request, so we
    # follow up with a third publish with a delay.
    time.sleep(1.2)
    r2 = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={"controlledProperty": "humidity", "value": 62.0},
        headers={"X-Device-Key": key},
    )
    assert r2.status_code == 202

    entries = _wait_until(
        lambda: (
            api.get(
                f"/api/v1/devices/{eid}/telemetry",
                params={"controlledProperty": "humidity", "limit": 10},
            ).json().get("entries", [])
            if len(api.get(
                f"/api/v1/devices/{eid}/telemetry",
                params={"controlledProperty": "humidity", "limit": 10},
            ).json().get("entries", [])) >= 2
            else None
        ),
        timeout_s=10.0,
    )
    assert entries, "telemetry did not return >= 2 entries after batch + follow-up"


def test_ingest_with_explicit_ts_used_as_dateObserved(api, anon, orion, created_ids):
    eid = _make_http_device(api, created_ids)
    key = _issue_key(api, eid)
    ts = "2026-04-01T12:34:56Z"
    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={"controlledProperty": "pressure", "value": 1013.25, "ts": ts},
        headers={"X-Device-Key": key},
    )
    assert r.status_code == 202, r.text

    device_uuid = eid.rsplit(":", 1)[-1]
    m_urn = f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:Pressure"
    created_ids.append(m_urn)

    body = _wait_until(
        lambda: (
            orion.get(f"/v2/entities/{m_urn}").json()
            if orion.get(f"/v2/entities/{m_urn}").status_code == 200
            else None
        ),
        timeout_s=5.0,
    )
    assert body is not None
    assert body["dateObserved"]["value"].startswith("2026-04-01T12:34:56")


def test_ingest_no_unit_code_when_omitted(api, anon, orion, created_ids):
    eid = _make_http_device(api, created_ids)
    key = _issue_key(api, eid)
    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={"controlledProperty": "battery", "value": 87.0},
        headers={"X-Device-Key": key},
    )
    assert r.status_code == 202

    device_uuid = eid.rsplit(":", 1)[-1]
    m_urn = f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:Battery"
    created_ids.append(m_urn)
    body = _wait_until(
        lambda: (
            orion.get(f"/v2/entities/{m_urn}").json()
            if orion.get(f"/v2/entities/{m_urn}").status_code == 200
            else None
        ),
        timeout_s=5.0,
    )
    assert body is not None
    assert "unitCode" not in body


# ─── ingest auth & validation failures ──────────────────────────────


def test_ingest_dataTypes_mismatch_422(api, anon, created_ids):
    eid = _make_http_device(api, created_ids, data_types={"temperature": "Number"})
    key = _issue_key(api, eid)
    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={"controlledProperty": "temperature", "value": "hot"},
        headers={"X-Device-Key": key},
    )
    assert r.status_code == 422, r.text


def test_ingest_missing_key_401(api, anon, created_ids):
    eid = _make_http_device(api, created_ids)
    _issue_key(api, eid)
    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={"controlledProperty": "temperature", "value": 1.0},
    )
    assert r.status_code == 401


def test_ingest_wrong_device_key_401(api, anon, created_ids):
    eid_a = _make_http_device(api, created_ids)
    eid_b = _make_http_device(api, created_ids)
    key_a = _issue_key(api, eid_a)
    _issue_key(api, eid_b)  # so the row exists
    r = anon.post(
        f"/api/v1/devices/{eid_b}/telemetry",
        json={"controlledProperty": "temperature", "value": 1.0},
        headers={"X-Device-Key": key_a},
    )
    assert r.status_code == 401


def test_ingest_unknown_device_404(anon):
    fake = f"urn:ngsi-ld:Device:{uuid.uuid4()}"
    r = anon.post(
        f"/api/v1/devices/{fake}/telemetry",
        json={"controlledProperty": "temperature", "value": 1.0},
        headers={"X-Device-Key": "dik_xxxx_yyyy"},
    )
    assert r.status_code == 404


def test_ingest_body_must_have_one_shape(api, anon, created_ids):
    eid = _make_http_device(api, created_ids)
    key = _issue_key(api, eid)
    # both shapes set
    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={
            "controlledProperty": "temperature",
            "value": 1.0,
            "measurements": [{"controlledProperty": "humidity", "value": 50.0}],
        },
        headers={"X-Device-Key": key},
    )
    assert r.status_code == 422
    # neither shape
    r = anon.post(
        f"/api/v1/devices/{eid}/telemetry",
        json={},
        headers={"X-Device-Key": key},
    )
    assert r.status_code == 422
