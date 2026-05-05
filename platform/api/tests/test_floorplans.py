"""Tests for site floor plans + device placements (ticket 0017)."""

from __future__ import annotations

import os
import struct
import zlib
from uuid import uuid4

import httpx
import pytest


API_BASE = os.environ.get("API_INTERNAL_URL", "http://iot-api:8000")
PREFIX = "/api/v1"


def _client(token: str | None = None) -> httpx.Client:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(base_url=API_BASE, timeout=30.0, headers=headers)


def _seed_device(api: httpx.Client, created_ids: list[str], site_area: str | None) -> str:
    uid = str(uuid4())
    body: dict = {
        "id": uid,
        "category": "sensor",
        "supportedProtocol": "http",
        "name": f"plan-{uid[:8]}",
    }
    if site_area is not None:
        body["location"] = {"latitude": 36.83, "longitude": -2.40, "site_area": site_area}
    r = api.post(f"{PREFIX}/devices", json=body)
    assert r.status_code == 201, r.text
    created_ids.append(f"urn:ngsi-ld:Device:{uid}")
    return uid


def _png(n_extra: int = 0) -> bytes:
    """Tiny valid 1x1 PNG, optionally padded."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_chunk = (
        struct.pack(">I", len(ihdr))
        + b"IHDR"
        + ihdr
        + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    )
    raw = b"\x00\xff\xff\xff"
    comp = zlib.compress(raw)
    idat_chunk = (
        struct.pack(">I", len(comp))
        + b"IDAT"
        + comp
        + struct.pack(">I", zlib.crc32(b"IDAT" + comp))
    )
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))
    base = sig + ihdr_chunk + idat_chunk + iend
    if n_extra > 0:
        # Append after IEND; keeps valid magic prefix and our size-cap test happy.
        base = base + b"\x00" * n_extra
    return base


# ---------- /sites index ----------


def test_sites_index_counts_and_flag(api, tokens, created_ids):
    site = f"plan-{uuid4().hex[:8]}"
    _seed_device(api, created_ids, site)
    _seed_device(api, created_ids, site)
    _seed_device(api, created_ids, None)  # no site_area → not counted

    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/sites")
    assert r.status_code == 200
    body = r.json()
    row = next((x for x in body if x["site_area"] == site), None)
    assert row is not None
    assert row["device_count"] >= 2
    assert row["has_floorplan"] is False

    # upload a plan and re-check
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("plan.png", _png(), "image/png")},
        )
    assert r.status_code == 201, r.text

    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/sites")
    row = next((x for x in r.json() if x["site_area"] == site), None)
    assert row and row["has_floorplan"] is True


# ---------- floorplan upload / get / delete ----------


def test_upload_get_delete_floorplan(api, tokens, created_ids):
    site = f"plan-{uuid4().hex[:8]}"
    _seed_device(api, created_ids, site)
    body = _png()

    # operator uploads (201)
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("plan.png", body, "image/png")},
        )
    assert r.status_code == 201
    js = r.json()
    assert js["site_area"] == site
    assert js["content_type"] == "image/png"
    assert js["size_bytes"] == len(body)
    assert js["uploaded_by"] == "operator"

    # second upload returns 200 (replace)
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("plan2.png", _png(extra := 32), "image/png")},
        )
    assert r.status_code == 200, r.text

    # viewer can download
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/sites/{site}/floorplan")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"

    # operator cannot delete; admin can
    with _client(tokens["operator"]) as c:
        assert c.delete(f"{PREFIX}/sites/{site}/floorplan").status_code == 403
    with _client(tokens["admin"]) as c:
        assert c.delete(f"{PREFIX}/sites/{site}/floorplan").status_code == 204
    with _client(tokens["viewer"]) as c:
        assert c.get(f"{PREFIX}/sites/{site}/floorplan").status_code == 404


def test_upload_non_image_415(api, tokens, created_ids):
    site = f"plan-{uuid4().hex[:8]}"
    _seed_device(api, created_ids, site)
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("note.txt", b"hello world", "text/plain")},
        )
    assert r.status_code == 415


def test_upload_too_big_413(api, tokens, created_ids):
    site = f"plan-{uuid4().hex[:8]}"
    _seed_device(api, created_ids, site)
    big = _png(n_extra=10 * 1024 * 1024 + 1)
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("big.png", big, "image/png")},
        )
    assert r.status_code == 413


def test_get_floorplan_unknown_404(tokens):
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/sites/no-such-site-{uuid4().hex[:6]}/floorplan")
    assert r.status_code == 404


# ---------- placements ----------


def test_placements_list_and_upsert(api, tokens, created_ids):
    site = f"plan-{uuid4().hex[:8]}"
    uid_a = _seed_device(api, created_ids, site)
    uid_b = _seed_device(api, created_ids, site)

    # initial list: both unplaced
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/sites/{site}/placements")
    assert r.status_code == 200
    items = {row["device_id"].rsplit("-", 1)[-1]: row for row in r.json()}
    # all entries have x_pct==y_pct==None
    for row in r.json():
        assert row["x_pct"] is None and row["y_pct"] is None

    # operator places A
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/devices/{uid_a}/placement",
            json={"x_pct": 25.5, "y_pct": 75.0},
        )
    assert r.status_code == 200, r.text
    js = r.json()
    assert js["x_pct"] == 25.5 and js["y_pct"] == 75.0

    # update the same placement
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/devices/{uid_a}/placement",
            json={"x_pct": 10.0, "y_pct": 20.0},
        )
    assert r.status_code == 200
    assert r.json()["x_pct"] == 10.0

    # list now shows A placed, B not
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/sites/{site}/placements")
    body = r.json()
    placed = {row["device_id"]: row for row in body}
    a_full = next(k for k in placed if k.endswith(uid_a))
    b_full = next(k for k in placed if k.endswith(uid_b))
    assert placed[a_full]["x_pct"] == 10.0
    assert placed[b_full]["x_pct"] is None

    # admin deletes A's placement
    with _client(tokens["admin"]) as c:
        assert c.delete(f"{PREFIX}/devices/{uid_a}/placement").status_code == 204


def test_placement_out_of_range_422(api, tokens, created_ids):
    site = f"plan-{uuid4().hex[:8]}"
    uid = _seed_device(api, created_ids, site)
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/devices/{uid}/placement",
            json={"x_pct": 101, "y_pct": 50},
        )
    assert r.status_code == 422


def test_placement_unknown_device_404(tokens):
    uid = str(uuid4())
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/devices/{uid}/placement",
            json={"x_pct": 10, "y_pct": 20},
        )
    assert r.status_code == 404


def test_placement_bad_device_id_404(tokens):
    with _client(tokens["operator"]) as c:
        r = c.put(
            f"{PREFIX}/devices/not-a-uuid/placement",
            json={"x_pct": 10, "y_pct": 20},
        )
    assert r.status_code == 404


def test_placements_include_state_and_primary_property(api, tokens, created_ids):
    """Ticket 0021: list_placements exposes deviceState + primary controlledProperty."""
    site = f"plan-{uuid4().hex[:8]}"

    # Device A: explicit deviceState + controlledProperty
    uid_a = str(uuid4())
    r = api.post(
        f"{PREFIX}/devices",
        json={
            "id": uid_a,
            "category": "sensor",
            "supportedProtocol": "http",
            "name": f"plan-{uid_a[:8]}",
            "location": {"latitude": 36.83, "longitude": -2.40, "site_area": site},
            "controlledProperty": ["temperature", "humidity"],
            "deviceState": "active",
        },
    )
    assert r.status_code == 201, r.text
    created_ids.append(f"urn:ngsi-ld:Device:{uid_a}")

    # Device B: neither field set
    uid_b = _seed_device(api, created_ids, site)

    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/sites/{site}/placements")
    assert r.status_code == 200
    by_id = {row["device_id"]: row for row in r.json()}
    a_full = next(k for k in by_id if k.endswith(uid_a))
    b_full = next(k for k in by_id if k.endswith(uid_b))

    assert by_id[a_full]["device_state"] == "active"
    assert by_id[a_full]["primary_property"] == "temperature"
    assert by_id[b_full]["device_state"] is None
    assert by_id[b_full]["primary_property"] is None


# ---------- RBAC matrix ----------


@pytest.mark.parametrize("role", ["viewer", "operator", "manager", "admin"])
def test_list_sites_allowed_for_all_roles(tokens, role):
    with _client(tokens[role]) as c:
        assert c.get(f"{PREFIX}/sites").status_code == 200


def test_upload_floorplan_forbidden_for_viewer(api, tokens, created_ids):
    site = f"plan-{uuid4().hex[:8]}"
    _seed_device(api, created_ids, site)
    with _client(tokens["viewer"]) as c:
        r = c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("p.png", _png(), "image/png")},
        )
    assert r.status_code == 403


@pytest.mark.parametrize("role", ["operator", "manager", "admin"])
def test_upload_floorplan_allowed(api, tokens, created_ids, role):
    site = f"plan-{uuid4().hex[:8]}"
    _seed_device(api, created_ids, site)
    with _client(tokens[role]) as c:
        r = c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("p.png", _png(), "image/png")},
        )
    assert r.status_code in (200, 201), r.text


@pytest.mark.parametrize("role", ["viewer", "operator", "manager"])
def test_delete_floorplan_forbidden_for_non_admins(api, tokens, created_ids, role):
    site = f"plan-{uuid4().hex[:8]}"
    _seed_device(api, created_ids, site)
    with _client(tokens["admin"]) as c:
        c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("p.png", _png(), "image/png")},
        )
    with _client(tokens[role]) as c:
        assert c.delete(f"{PREFIX}/sites/{site}/floorplan").status_code == 403


# ---------- 401 ----------


def test_unauth_endpoints_return_401():
    site = "any"
    with _client() as c:
        assert c.get(f"{PREFIX}/sites").status_code == 401
        assert c.get(f"{PREFIX}/sites/{site}/floorplan").status_code == 401
        assert c.get(f"{PREFIX}/sites/{site}/placements").status_code == 401
        r = c.put(
            f"{PREFIX}/sites/{site}/floorplan",
            files={"file": ("p.png", _png(), "image/png")},
        )
        assert r.status_code == 401
        assert (
            c.put(
                f"{PREFIX}/devices/{uuid4()}/placement",
                json={"x_pct": 1, "y_pct": 1},
            ).status_code
            == 401
        )
