"""Tests for device manuals (ticket 0016)."""

from __future__ import annotations

import io
import os
from uuid import uuid4

import httpx
import pytest


API_BASE = os.environ.get("API_INTERNAL_URL", "http://iot-api:8000")
PREFIX = "/api/v1"


def _client(token: str | None = None) -> httpx.Client:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(base_url=API_BASE, timeout=30.0, headers=headers)


def _seed_device(api: httpx.Client, created_ids: list[str]) -> str:
    uid = str(uuid4())
    r = api.post(
        f"{PREFIX}/devices",
        json={
            "id": uid,
            "category": "sensor",
            "supportedProtocol": "http",
            "name": f"manuals-{uid[:8]}",
        },
    )
    assert r.status_code == 201, r.text
    created_ids.append(f"urn:ngsi-ld:Device:{uid}")
    return uid


def _pdf_bytes(extra: int = 64) -> bytes:
    """Minimal-but-valid-looking PDF: just needs the magic header for our checks."""
    return b"%PDF-1.4\n" + b"x" * extra + b"\n%%EOF\n"


# ---------- happy path ----------


def test_upload_then_list_then_get_then_delete(api, tokens, created_ids):
    uid = _seed_device(api, created_ids)
    body = _pdf_bytes(2048)

    # operator can upload
    with _client(tokens["operator"]) as c:
        r = c.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("vendor.pdf", body, "application/pdf")},
        )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["filename"] == "vendor.pdf"
    assert created["content_type"] == "application/pdf"
    assert created["size_bytes"] == len(body)
    assert created["uploaded_by"] == "operator"
    manual_id = created["id"]

    # viewer can list and see it
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/devices/{uid}/manuals")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1 and items[0]["id"] == manual_id

    # viewer can download
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/manuals/{manual_id}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content == body

    # admin can delete (operator cannot)
    with _client(tokens["operator"]) as c:
        assert c.delete(f"{PREFIX}/manuals/{manual_id}").status_code == 403
    with _client(tokens["admin"]) as c:
        assert c.delete(f"{PREFIX}/manuals/{manual_id}").status_code == 204

    # gone
    with _client(tokens["admin"]) as c:
        assert c.get(f"{PREFIX}/manuals/{manual_id}").status_code == 404


def test_list_empty_for_known_device(api, tokens, created_ids):
    uid = _seed_device(api, created_ids)
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/devices/{uid}/manuals")
    assert r.status_code == 200
    assert r.json() == []


# ---------- bad inputs ----------


def test_upload_non_pdf_415(api, tokens, created_ids):
    uid = _seed_device(api, created_ids)
    with _client(tokens["operator"]) as c:
        r = c.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("note.txt", b"hello world", "text/plain")},
        )
    assert r.status_code == 415


def test_upload_pdf_content_type_but_wrong_magic_415(api, tokens, created_ids):
    """Content-type lies; magic-byte check must reject."""
    uid = _seed_device(api, created_ids)
    with _client(tokens["operator"]) as c:
        r = c.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("fake.pdf", b"NOTPDF" + b"\x00" * 32, "application/pdf")},
        )
    assert r.status_code == 415


def test_upload_too_big_413(api, tokens, created_ids):
    uid = _seed_device(api, created_ids)
    big = b"%PDF-1.4\n" + b"x" * (10 * 1024 * 1024)  # > 10 MiB
    with _client(tokens["operator"]) as c:
        r = c.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("big.pdf", big, "application/pdf")},
        )
    assert r.status_code == 413


def test_upload_unknown_device_404(tokens):
    uid = str(uuid4())
    with _client(tokens["operator"]) as c:
        r = c.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("x.pdf", _pdf_bytes(), "application/pdf")},
        )
    assert r.status_code == 404


def test_upload_bad_device_id_404(tokens):
    with _client(tokens["operator"]) as c:
        r = c.post(
            f"{PREFIX}/devices/not-a-uuid/manuals",
            files={"file": ("x.pdf", _pdf_bytes(), "application/pdf")},
        )
    assert r.status_code == 404


def test_get_unknown_404(tokens):
    with _client(tokens["viewer"]) as c:
        r = c.get(f"{PREFIX}/manuals/{uuid4()}")
    assert r.status_code == 404


def test_delete_unknown_404(tokens):
    with _client(tokens["admin"]) as c:
        r = c.delete(f"{PREFIX}/manuals/{uuid4()}")
    assert r.status_code == 404


# ---------- RBAC ----------


@pytest.mark.parametrize("role", ["viewer", "operator", "manager", "admin"])
def test_list_allowed_for_all_roles(api, tokens, created_ids, role):
    uid = _seed_device(api, created_ids)
    with _client(tokens[role]) as c:
        r = c.get(f"{PREFIX}/devices/{uid}/manuals")
    assert r.status_code == 200


def test_upload_forbidden_for_viewer(api, tokens, created_ids):
    uid = _seed_device(api, created_ids)
    with _client(tokens["viewer"]) as c:
        r = c.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("x.pdf", _pdf_bytes(), "application/pdf")},
        )
    assert r.status_code == 403


@pytest.mark.parametrize("role", ["operator", "manager", "admin"])
def test_upload_allowed_for_operator_manager_admin(api, tokens, created_ids, role):
    uid = _seed_device(api, created_ids)
    with _client(tokens[role]) as c:
        r = c.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("x.pdf", _pdf_bytes(), "application/pdf")},
        )
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("role", ["viewer", "operator", "manager"])
def test_delete_forbidden_for_non_admins(api, tokens, created_ids, role):
    uid = _seed_device(api, created_ids)
    with _client(tokens["admin"]) as admin:
        r = admin.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("x.pdf", _pdf_bytes(), "application/pdf")},
        )
        assert r.status_code == 201
        manual_id = r.json()["id"]
    with _client(tokens[role]) as c:
        assert c.delete(f"{PREFIX}/manuals/{manual_id}").status_code == 403


# ---------- 401 ----------


def test_unauth_list_401(api, created_ids):
    uid = _seed_device(api, created_ids)
    with _client() as c:
        assert c.get(f"{PREFIX}/devices/{uid}/manuals").status_code == 401


def test_unauth_upload_401(api, created_ids):
    uid = _seed_device(api, created_ids)
    with _client() as c:
        r = c.post(
            f"{PREFIX}/devices/{uid}/manuals",
            files={"file": ("x.pdf", _pdf_bytes(), "application/pdf")},
        )
    assert r.status_code == 401


def test_unauth_get_401():
    with _client() as c:
        assert c.get(f"{PREFIX}/manuals/{uuid4()}").status_code == 401


def test_unauth_delete_401():
    with _client() as c:
        assert c.delete(f"{PREFIX}/manuals/{uuid4()}").status_code == 401
