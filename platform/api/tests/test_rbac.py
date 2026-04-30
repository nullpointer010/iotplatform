"""RBAC matrix tests for ticket 0014.

Each block exercises a representative endpoint per resource with three
shapes: no token (401), insufficient role (403), sufficient role (200).
The token fixture comes from `conftest.py`.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest


API_BASE = os.environ.get("API_INTERNAL_URL", "http://iot-api:8000")
PREFIX = "/api/v1"


def _client(token: str | None = None) -> httpx.Client:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(base_url=API_BASE, timeout=10.0, headers=headers)


# ---------- helpers used to provoke 200s ----------


def _seed_device(api: httpx.Client) -> str:
    """Create a device with the admin-token fixture; return its short uuid."""
    uid = str(uuid4())
    r = api.post(
        f"{PREFIX}/devices",
        json={
            "id": uid,
            "category": "sensor",
            "supportedProtocol": "http",
            "name": f"rbac-{uid[:8]}",
        },
    )
    assert r.status_code == 201, r.text
    return uid


# ---------- /devices ----------


def test_devices_list_requires_auth():
    with _client() as c:
        assert c.get(f"{PREFIX}/devices").status_code == 401


def test_devices_create_forbidden_for_viewer(tokens):
    with _client(tokens["viewer"]) as c:
        r = c.post(
            f"{PREFIX}/devices",
            json={"id": str(uuid4()), "category": "sensor", "supportedProtocol": "http"},
        )
    assert r.status_code == 403


def test_devices_list_ok_for_viewer(tokens):
    with _client(tokens["viewer"]) as c:
        assert c.get(f"{PREFIX}/devices").status_code == 200


def test_devices_create_ok_for_operator(tokens, created_ids):
    uid = str(uuid4())
    payload = {
        "id": uid,
        "category": "sensor",
        "supportedProtocol": "http",
        "name": f"rbac-op-{uid[:8]}",
    }
    with _client(tokens["operator"]) as c:
        r = c.post(f"{PREFIX}/devices", json=payload)
    assert r.status_code == 201, r.text
    created_ids.append(f"urn:ngsi-ld:Device:{uid}")


def test_devices_delete_forbidden_for_operator(tokens, api, created_ids):
    uid = _seed_device(api)
    created_ids.append(f"urn:ngsi-ld:Device:{uid}")
    with _client(tokens["operator"]) as c:
        r = c.delete(f"{PREFIX}/devices/{uid}")
    assert r.status_code == 403


def test_devices_delete_ok_for_admin(tokens, api):
    uid = _seed_device(api)
    with _client(tokens["admin"]) as c:
        r = c.delete(f"{PREFIX}/devices/{uid}")
    assert r.status_code == 204


# ---------- telemetry / state ----------


def test_state_requires_auth():
    with _client() as c:
        assert c.get(f"{PREFIX}/devices/{uuid4()}/state").status_code == 401


def test_state_ok_for_viewer(tokens, api, created_ids):
    uid = _seed_device(api)
    created_ids.append(f"urn:ngsi-ld:Device:{uid}")
    with _client(tokens["viewer"]) as c:
        # 200 with empty state body, or 404 if the entity never had state attrs;
        # auth itself must succeed.
        r = c.get(f"{PREFIX}/devices/{uid}/state")
    assert r.status_code in (200, 404)


# ---------- maintenance/operation-types ----------


def test_op_types_create_forbidden_for_operator(tokens):
    with _client(tokens["operator"]) as c:
        r = c.post(
            f"{PREFIX}/maintenance/operation-types",
            json={"name": f"rbac-{uuid4().hex[:6]}", "requires_component": False},
        )
    assert r.status_code == 403


def test_op_types_create_ok_for_manager(tokens):
    with _client(tokens["manager"]) as c:
        r = c.post(
            f"{PREFIX}/maintenance/operation-types",
            json={"name": f"rbac-{uuid4().hex[:6]}", "requires_component": False},
        )
    assert r.status_code == 201, r.text


def test_op_types_list_ok_for_viewer(tokens):
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/maintenance/operation-types")
    assert r.status_code == 200


# ---------- maintenance/log ----------


def test_log_list_requires_auth():
    with _client() as c:
        assert c.get(f"{PREFIX}/devices/{uuid4()}/maintenance/log").status_code == 401


def test_log_delete_forbidden_for_operator(tokens):
    # The log id doesn't matter — RBAC fires before the lookup.
    fake = uuid4()
    with _client(tokens["operator"]) as c:
        r = c.delete(f"{PREFIX}/maintenance/log/{fake}")
    assert r.status_code == 403


def test_log_delete_returns_404_for_manager(tokens):
    """Manager passes RBAC; the (random) id then 404s."""
    fake = uuid4()
    with _client(tokens["manager"]) as c:
        r = c.delete(f"{PREFIX}/maintenance/log/{fake}")
    assert r.status_code == 404


# ---------- health stays public ----------


def test_health_is_public():
    with _client() as c:
        assert c.get("/healthz").status_code == 200


# ---------- /me echoes identity for any authenticated user ----------


@pytest.mark.parametrize(
    "user,expected_role",
    [
        ("viewer", "viewer"),
        ("operator", "operator"),
        ("manager", "maintenance_manager"),
        ("admin", "admin"),
    ],
)
def test_me_returns_username_and_roles(tokens, user, expected_role):
    with _client(tokens[user]) as c:
        r = c.get(f"{PREFIX}/me")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == user
    assert expected_role in body["roles"]


def test_me_requires_auth():
    with _client() as c:
        assert c.get(f"{PREFIX}/me").status_code == 401
