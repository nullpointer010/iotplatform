from __future__ import annotations

import httpx
import pytest


DEVICES = "/api/v1/devices"


def _http_payload(name: str = "http-dev") -> dict:
    return {"name": name, "category": "sensor", "supportedProtocol": "http"}


def _mqtt_payload(name: str = "mqtt-dev") -> dict:
    return {
        "name": name,
        "category": "sensor",
        "supportedProtocol": "mqtt",
        "mqttTopicRoot": "site/area/sensor1",
        "mqttClientId": "sensor1",
    }


def _plc_payload(name: str = "plc-dev") -> dict:
    return {
        "name": name,
        "category": "plc",
        "supportedProtocol": "plc",
        "plcIpAddress": "192.168.1.100",
        "plcPort": 502,
        "plcConnectionMethod": "Modbus TCP",
        "plcTagsMapping": {"DB1.DW10": "Temperatura"},
    }


def _lora_payload(name: str = "lora-dev") -> dict:
    return {
        "name": name,
        "category": "sensor",
        "supportedProtocol": "lorawan",
        "loraAppEui": "70B3D57ED00001A6",
        "loraDevEui": "0004A30B001C0530",
        "loraAppKey": "0123456789ABCDEF0123456789ABCDEF",
        "loraNetworkServer": "lora.example.com",
        "loraPayloadDecoder": "decoder_v1",
    }


# ---------- POST: cross-protocol leak ----------

def test_post_http_with_mqtt_field_rejected(api: httpx.Client):
    payload = _http_payload() | {"mqttTopicRoot": "a/b"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422, r.text


def test_post_mqtt_with_plc_field_rejected(api: httpx.Client):
    payload = _mqtt_payload() | {"plcIpAddress": "10.0.0.1"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422, r.text


def test_post_plc_with_lora_field_rejected(api: httpx.Client):
    payload = _plc_payload() | {"loraAppEui": "70B3D57ED00001A6"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422, r.text


# ---------- POST: required-fields regression ----------

def test_post_mqtt_missing_required_rejected(api: httpx.Client):
    payload = _mqtt_payload()
    payload.pop("mqttClientId")
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422, r.text


# ---------- POST: field-format ----------

@pytest.mark.parametrize("topic", ["/leading", "trailing/", "with space", "wild+card", "wild#card"])
def test_post_mqtt_topic_invalid(api: httpx.Client, topic: str):
    payload = _mqtt_payload() | {"mqttTopicRoot": topic}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422, (topic, r.text)


def test_post_plc_bad_ip_rejected(api: httpx.Client):
    payload = _plc_payload() | {"plcIpAddress": "999.1.1.1"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422, r.text


def test_post_lora_bad_eui_rejected(api: httpx.Client):
    payload = _lora_payload() | {"loraAppEui": "70B3D57ED00001"}  # 14 hex
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422, r.text


def test_post_lora_bad_appkey_rejected(api: httpx.Client):
    payload = _lora_payload() | {"loraAppKey": "ZZZZ"}
    r = api.post(DEVICES, json=payload)
    assert r.status_code == 422, r.text


# ---------- POST: happy paths ----------

def test_post_full_lora_succeeds(api: httpx.Client, created_ids: list[str]):
    r = api.post(DEVICES, json=_lora_payload())
    assert r.status_code == 201, r.text
    created_ids.append(r.json()["id"])


def test_post_full_plc_succeeds(api: httpx.Client, created_ids: list[str]):
    r = api.post(DEVICES, json=_plc_payload())
    assert r.status_code == 201, r.text
    created_ids.append(r.json()["id"])


# ---------- PATCH: cross-validation ----------

def test_patch_switch_protocol_without_required_rejected(
    api: httpx.Client, created_ids: list[str]
):
    r = api.post(DEVICES, json=_http_payload())
    assert r.status_code == 201
    eid = r.json()["id"]
    created_ids.append(eid)

    r = api.patch(f"{DEVICES}/{eid}", json={"supportedProtocol": "mqtt"})
    assert r.status_code == 422, r.text


def test_patch_switch_protocol_with_required_succeeds(
    api: httpx.Client, created_ids: list[str]
):
    r = api.post(DEVICES, json=_http_payload())
    eid = r.json()["id"]
    created_ids.append(eid)

    r = api.patch(
        f"{DEVICES}/{eid}",
        json={
            "supportedProtocol": "mqtt",
            "mqttTopicRoot": "a/b",
            "mqttClientId": "cid",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["supportedProtocol"] == "mqtt"


def test_patch_introduces_foreign_protocol_field_rejected(
    api: httpx.Client, created_ids: list[str]
):
    r = api.post(DEVICES, json=_mqtt_payload())
    eid = r.json()["id"]
    created_ids.append(eid)

    r = api.patch(f"{DEVICES}/{eid}", json={"plcIpAddress": "10.0.0.1"})
    assert r.status_code == 422, r.text


def test_patch_bad_format_rejected(api: httpx.Client, created_ids: list[str]):
    r = api.post(DEVICES, json=_plc_payload())
    eid = r.json()["id"]
    created_ids.append(eid)

    r = api.patch(f"{DEVICES}/{eid}", json={"plcIpAddress": "not-an-ip"})
    assert r.status_code == 422, r.text


def test_patch_in_protocol_field_succeeds(
    api: httpx.Client, created_ids: list[str]
):
    r = api.post(DEVICES, json=_mqtt_payload())
    eid = r.json()["id"]
    created_ids.append(eid)

    r = api.patch(f"{DEVICES}/{eid}", json={"mqttQos": 2})
    assert r.status_code == 200, r.text
    assert r.json()["mqttQos"] == 2


def test_patch_no_op_name_change_succeeds(
    api: httpx.Client, created_ids: list[str]
):
    r = api.post(DEVICES, json=_mqtt_payload())
    eid = r.json()["id"]
    created_ids.append(eid)

    r = api.patch(f"{DEVICES}/{eid}", json={"name": "renamed"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "renamed"
