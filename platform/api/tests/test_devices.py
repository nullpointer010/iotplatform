from __future__ import annotations

from uuid import uuid4

import httpx
import pytest


URN = "urn:ngsi-ld:Device:"
DEVICES = "/api/v1/devices"


def _minimal_payload(name: str = "sensor") -> dict:
    return {
        "name": name,
        "category": "sensor",
        "supportedProtocol": "http",
    }


def _full_mqtt_payload(name: str = "mqtt-sensor") -> dict:
    return {
        "name": name,
        "category": "sensor",
        "supportedProtocol": "mqtt",
        "controlledProperty": ["temperature", "humidity"],
        "serialNumber": "00:1B:44:11:3A:B7",
        "serialNumberType": "MAC",
        "location": {"latitude": 40.4168, "longitude": -3.7038},
        "manufacturerName": "Acme",
        "modelName": "T-1000",
        "firmwareVersion": "1.2.3",
        "deviceState": "active",
        "mqttTopicRoot": "instalacion/salaA/temp/sensor1",
        "mqttClientId": "sensor1",
        "mqttQos": 1,
    }


# ---------- create ----------

def test_create_minimal_returns_201_with_urn_id(api, created_ids):
    r = api.post(DEVICES, json=_minimal_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"].startswith(URN)
    assert body["type"] == "Device"
    assert body["name"] == "sensor"
    assert body["category"] == "sensor"
    created_ids.append(body["id"])


def test_create_with_explicit_uuid_returns_urn(api, created_ids):
    uid = str(uuid4())
    payload = _minimal_payload() | {"id": uid}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["id"] == URN + uid
    created_ids.append(URN + uid)


def test_create_full_mqtt_device_round_trips(api, created_ids):
    r = api.post(DEVICES, json=_full_mqtt_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    created_ids.append(body["id"])
    # round-trip: re-fetch and check key fields survived
    g = api.get(f"{DEVICES}/{body['id']}")
    assert g.status_code == 200
    got = g.json()
    assert got["mqttTopicRoot"] == "instalacion/salaA/temp/sensor1"
    assert got["mqttQos"] == 1
    assert got["controlledProperty"] == ["temperature", "humidity"]
    assert got["location"] == {"latitude": 40.4168, "longitude": -3.7038}


def test_create_missing_name_returns_422(api):
    r = api.post(DEVICES, json={"category": "sensor", "supportedProtocol": "http"})
    assert r.status_code == 422


def test_create_unknown_category_returns_422(api):
    payload = _minimal_payload() | {"category": "spaceship"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422


def test_create_mqtt_without_topic_root_returns_422(api):
    payload = {
        "name": "x",
        "category": "sensor",
        "supportedProtocol": "mqtt",
        "mqttClientId": "c1",
    }
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422


def test_create_plc_without_required_fields_returns_422(api):
    payload = {"name": "x", "category": "plc", "supportedProtocol": "plc"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422


def test_create_lorawan_without_required_fields_returns_422(api):
    payload = {"name": "x", "category": "sensor", "supportedProtocol": "lorawan"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422


def test_create_extra_field_returns_422(api):
    payload = _minimal_payload() | {"bogus": "no"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422


def test_create_duplicate_returns_409(api, created_ids):
    uid = str(uuid4())
    p = _minimal_payload() | {"id": uid}
    r1 = api.post(DEVICES, json=p)
    assert r1.status_code == 201
    created_ids.append(URN + uid)
    r2 = api.post(DEVICES, json=p)
    assert r2.status_code == 409


# ---------- get ----------

def test_get_by_uuid_and_by_urn_match(api, created_ids):
    uid = str(uuid4())
    api.post(DEVICES, json=_minimal_payload() | {"id": uid})
    created_ids.append(URN + uid)
    g_uuid = api.get(f"{DEVICES}/{uid}")
    g_urn = api.get(f"{DEVICES}/{URN}{uid}")
    assert g_uuid.status_code == 200
    assert g_urn.status_code == 200
    assert g_uuid.json() == g_urn.json()


def test_get_unknown_returns_404(api):
    r = api.get(f"{DEVICES}/{uuid4()}")
    assert r.status_code == 404


def test_get_malformed_id_returns_404(api):
    r = api.get(f"{DEVICES}/not-a-uuid")
    assert r.status_code == 404


# ---------- list ----------

def test_list_after_creates_includes_them(api, created_ids):
    uid = str(uuid4())
    api.post(DEVICES, json=_minimal_payload(f"name-{uid}") | {"id": uid})
    created_ids.append(URN + uid)
    r = api.get(DEVICES, params={"limit": 1000})
    assert r.status_code == 200
    ids = [e["id"] for e in r.json()]
    assert URN + uid in ids


def test_list_pagination_bad_limit_returns_400(api):
    r = api.get(DEVICES, params={"limit": 0})
    assert r.status_code == 422  # FastAPI Query validation


def test_list_pagination_negative_offset_returns_422(api):
    r = api.get(DEVICES, params={"offset": -1})
    assert r.status_code == 422


# ---------- patch ----------

def test_patch_partial_updates_only_given_fields(api, created_ids):
    uid = str(uuid4())
    api.post(DEVICES, json=_minimal_payload("before") | {"id": uid})
    created_ids.append(URN + uid)
    r = api.patch(f"{DEVICES}/{uid}", json={"name": "after", "deviceState": "maintenance"})
    assert r.status_code == 200, r.text
    g = api.get(f"{DEVICES}/{uid}").json()
    assert g["name"] == "after"
    assert g["deviceState"] == "maintenance"
    assert g["category"] == "sensor"  # unchanged


def test_patch_unknown_returns_404(api):
    r = api.patch(f"{DEVICES}/{uuid4()}", json={"name": "x"})
    assert r.status_code == 404


def test_patch_extra_field_returns_422(api, created_ids):
    uid = str(uuid4())
    api.post(DEVICES, json=_minimal_payload() | {"id": uid})
    created_ids.append(URN + uid)
    r = api.patch(f"{DEVICES}/{uid}", json={"bogus": "no"})
    assert r.status_code == 422
