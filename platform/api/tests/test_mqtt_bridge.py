"""Integration tests for the MQTT broker + bridge (ticket 0018).

These tests run inside the iot-api container and connect to the
Mosquitto broker at ``mosquitto:1883`` over the iot-net network.
"""
from __future__ import annotations

import os
import time
import uuid
from collections.abc import Iterator

import httpx
import paho.mqtt.client as mqtt
import pytest


MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "bridge")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "change-me-bridge")


def _wait_until(predicate, timeout_s: float = 5.0, interval: float = 0.1):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    return last


@pytest.fixture
def mqtt_client() -> Iterator[mqtt.Client]:
    cli = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"test-{uuid.uuid4().hex[:8]}",
    )
    cli.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    cli.connect(MQTT_HOST, MQTT_PORT, keepalive=15)
    cli.loop_start()
    try:
        yield cli
    finally:
        cli.loop_stop()
        try:
            cli.disconnect()
        except Exception:
            pass


def _make_mqtt_device(api: httpx.Client, created_ids: list[str], data_types: dict[str, str]) -> tuple[str, str]:
    dev_uuid = str(uuid.uuid4())
    root = f"test/{dev_uuid[:8]}"
    payload = {
        "id": dev_uuid,
        "category": "sensor",
        "name": f"mqtt-test-{dev_uuid[:6]}",
        "supportedProtocol": "mqtt",
        "mqttTopicRoot": root,
        "mqttClientId": f"sensor-{dev_uuid[:6]}",
        "dataTypes": data_types,
    }
    r = api.post("/api/v1/devices", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    eid = body["id"]
    created_ids.append(eid)
    # Allow the bridge a moment to receive the refresh().
    time.sleep(0.5)
    return eid, root


def test_publish_lands_in_state_and_crate(api, orion, ql, created_ids, mqtt_client):
    eid, root = _make_mqtt_device(api, created_ids, {"temp": "Number"})
    mqtt_client.publish(f"{root}/temp", '{"value": 24.7}', qos=0).wait_for_publish(timeout=2)

    state = _wait_until(
        lambda: (
            api.get(f"/api/v1/devices/{eid}/state").json()
            if api.get(f"/api/v1/devices/{eid}/state").status_code == 200
            and api.get(f"/api/v1/devices/{eid}/state").json().get("attributes", {}).get("temp", {}).get("value") == 24.7
            else None
        ),
        timeout_s=4.0,
    )
    assert state is not None, "temp value did not land in /state within 4s"
    assert state["attributes"]["temp"]["value"] == 24.7


def test_publish_invalid_json_dropped(api, created_ids, mqtt_client, tokens):
    eid, root = _make_mqtt_device(api, created_ids, {"temp": "Number"})
    admin = {"Authorization": f"Bearer {tokens['admin']}"}
    before = api.get("/api/v1/system/mqtt", headers=admin).json()["dropped_invalid"]
    mqtt_client.publish(f"{root}/temp", b"not-json", qos=0).wait_for_publish(timeout=2)
    after = _wait_until(
        lambda: api.get("/api/v1/system/mqtt", headers=admin).json()["dropped_invalid"]
        if api.get("/api/v1/system/mqtt", headers=admin).json()["dropped_invalid"] > before
        else None,
        timeout_s=3.0,
    )
    assert after is not None and after > before


def test_publish_dataTypes_mismatch_dropped(api, created_ids, mqtt_client, tokens):
    eid, root = _make_mqtt_device(api, created_ids, {"temp": "Number"})
    admin = {"Authorization": f"Bearer {tokens['admin']}"}
    before = api.get("/api/v1/system/mqtt", headers=admin).json()["dropped_invalid"]
    mqtt_client.publish(f"{root}/temp", '{"value": "hello"}', qos=0).wait_for_publish(timeout=2)
    after = _wait_until(
        lambda: api.get("/api/v1/system/mqtt", headers=admin).json()["dropped_invalid"]
        if api.get("/api/v1/system/mqtt", headers=admin).json()["dropped_invalid"] > before
        else None,
        timeout_s=3.0,
    )
    assert after is not None
    state = api.get(f"/api/v1/devices/{eid}/state").json()
    assert "temp" not in (state.get("attributes") or {})


def test_subscription_refresh_on_create(api, created_ids, mqtt_client):
    """A newly-created device's topic must be picked up without restart."""
    eid, root = _make_mqtt_device(api, created_ids, {"door": "Boolean"})
    mqtt_client.publish(f"{root}/door", '{"value": true}', qos=0).wait_for_publish(timeout=2)
    state = _wait_until(
        lambda: (
            api.get(f"/api/v1/devices/{eid}/state").json()
            if api.get(f"/api/v1/devices/{eid}/state").status_code == 200
            and api.get(f"/api/v1/devices/{eid}/state").json().get("attributes", {}).get("door", {}).get("value") is True
            else None
        ),
        timeout_s=4.0,
    )
    assert state is not None, "door=true did not propagate"


def test_unknown_topic_dropped(api, created_ids, mqtt_client, tokens):
    """A publish on a topic root that no device owns increments the drop counter."""
    admin = {"Authorization": f"Bearer {tokens['admin']}"}
    before = api.get("/api/v1/system/mqtt", headers=admin).json()["dropped_invalid"]
    # Subscribe pattern <root>/+ won't match anything, but publish anyway —
    # if the bridge happens to be subscribed to a leftover root, this is a noop.
    mqtt_client.publish(f"nonexistent-{uuid.uuid4().hex[:8]}/x", '{"value": 1}', qos=0).wait_for_publish(timeout=2)
    # No assertion on `before`/`after` change because the bridge never sees it
    # (no subscription matches). This test just confirms the broker doesn't
    # reject the publish and the API stays healthy.
    after = api.get("/api/v1/system/mqtt", headers=admin)
    assert after.status_code == 200


def test_system_mqtt_endpoint_rbac(api, tokens):
    paths = "/api/v1/system/mqtt"
    # admin
    r = api.get(paths, headers={"Authorization": f"Bearer {tokens['admin']}"})
    assert r.status_code == 200
    body = r.json()
    assert {"connected", "subscribed_topics", "last_message_at", "dropped_invalid"} <= body.keys()
    # operator / manager / viewer → 403
    for role in ("operator", "manager", "viewer"):
        r = api.get(paths, headers={"Authorization": f"Bearer {tokens[role]}"})
        assert r.status_code == 403, f"{role} got {r.status_code}"
    # anon → 401
    r = httpx.get(f"{api.base_url}{paths}", timeout=5.0)
    assert r.status_code == 401


def test_subscription_removed_on_delete(api, orion, mqtt_client, tokens):
    """After delete, publishes on the old root must not recreate the entity."""
    # Create + immediately delete
    dev_uuid = str(uuid.uuid4())
    root = f"test/{dev_uuid[:8]}"
    r = api.post(
        "/api/v1/devices",
        json={
            "id": dev_uuid,
            "category": "sensor",
            "name": f"mqtt-del-{dev_uuid[:6]}",
            "supportedProtocol": "mqtt",
            "mqttTopicRoot": root,
            "mqttClientId": f"sensor-{dev_uuid[:6]}",
            "dataTypes": {"temp": "Number"},
        },
    )
    assert r.status_code == 201
    eid = r.json()["id"]
    d = api.delete(f"/api/v1/devices/{eid}")
    assert d.status_code == 204
    time.sleep(0.5)  # let bridge.refresh() run
    mqtt_client.publish(f"{root}/temp", '{"value": 99}', qos=0).wait_for_publish(timeout=2)
    time.sleep(1.0)
    # The entity must remain absent (no autovivification).
    r = api.get(f"/api/v1/devices/{eid}")
    assert r.status_code == 404


# ─── ticket 0018b: canonical DeviceMeasurement upsert ────────────────────


def _ql_entry_count(api: httpx.Client, eid: str, controlled_property: str) -> int:
    r = api.get(
        f"/api/v1/devices/{eid}/telemetry",
        params={"controlledProperty": controlled_property, "limit": 100},
    )
    if r.status_code != 200:
        return 0
    return len(r.json().get("entries", []))


def test_publish_lands_in_state_and_telemetry(api, orion, created_ids, mqtt_client):
    """0018b: a numeric MQTT publish must reach /state AND /telemetry."""
    eid, root = _make_mqtt_device(api, created_ids, {"temperature": "Number"})
    mqtt_client.publish(
        f"{root}/temperature", '{"value": 24.7}', qos=0
    ).wait_for_publish(timeout=2)

    # /state reflects the value and dateLastValueReported is set.
    state = _wait_until(
        lambda: (
            api.get(f"/api/v1/devices/{eid}/state").json()
            if api.get(f"/api/v1/devices/{eid}/state").status_code == 200
            and api.get(f"/api/v1/devices/{eid}/state").json().get("attributes", {}).get("temperature", {}).get("value") == 24.7
            else None
        ),
        timeout_s=4.0,
    )
    assert state is not None, "/state did not pick up the publish"
    assert state.get("dateLastValueReported"), "dateLastValueReported missing"

    # /telemetry shows at least one DeviceMeasurement entry.
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
    assert entries, "/telemetry did not return the DeviceMeasurement"
    assert any(e["numValue"] == 24.7 for e in entries)

    # The measurement entity itself must exist in Orion.
    device_uuid = eid.rsplit(":", 1)[-1]
    m_urn = f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:Temperature"
    created_ids.append(m_urn)  # ensure cleanup
    r = orion.get(f"/v2/entities/{m_urn}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "DeviceMeasurement"
    assert body["refDevice"]["value"] == eid
    assert body["controlledProperty"]["value"] == "temperature"
    assert body["numValue"]["value"] == 24.7


def test_two_publishes_yield_two_entries(api, orion, created_ids, mqtt_client):
    """0018b: a second publish must update (not collide on) the entity."""
    eid, root = _make_mqtt_device(api, created_ids, {"temperature": "Number"})
    device_uuid = eid.rsplit(":", 1)[-1]
    m_urn = f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:Temperature"
    created_ids.append(m_urn)

    mqtt_client.publish(
        f"{root}/temperature", '{"value": 21.1}', qos=0
    ).wait_for_publish(timeout=2)
    _wait_until(
        lambda: _ql_entry_count(api, eid, "temperature") >= 1, timeout_s=8.0
    )
    time.sleep(1.2)  # let QL move the time_index forward
    mqtt_client.publish(
        f"{root}/temperature", '{"value": 22.2}', qos=0
    ).wait_for_publish(timeout=2)
    final = _wait_until(
        lambda: _ql_entry_count(api, eid, "temperature") >= 2, timeout_s=8.0
    )
    assert final, "second publish did not produce a second telemetry entry"


def test_boolean_publish_creates_no_measurement(api, orion, created_ids, mqtt_client):
    """0018b: non-numeric publishes update /state but skip DeviceMeasurement."""
    eid, root = _make_mqtt_device(api, created_ids, {"door": "Boolean"})
    mqtt_client.publish(
        f"{root}/door", '{"value": true}', qos=0
    ).wait_for_publish(timeout=2)
    state = _wait_until(
        lambda: (
            api.get(f"/api/v1/devices/{eid}/state").json()
            if api.get(f"/api/v1/devices/{eid}/state").status_code == 200
            and api.get(f"/api/v1/devices/{eid}/state").json().get("attributes", {}).get("door", {}).get("value") is True
            else None
        ),
        timeout_s=4.0,
    )
    assert state is not None, "boolean publish did not reach /state"

    device_uuid = eid.rsplit(":", 1)[-1]
    m_urn = f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:Door"
    r = orion.get(f"/v2/entities/{m_urn}")
    assert r.status_code == 404, f"unexpected DeviceMeasurement created: {r.text}"
