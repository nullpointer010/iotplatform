from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


URN = "urn:ngsi-ld:Device:"
OPS = "/api/v1/maintenance/operation-types"


def _create_device(api, created_ids) -> str:
    uid = str(uuid4())
    r = api.post(
        "/api/v1/devices",
        json={
            "name": f"sensor-{uid[:8]}",
            "category": "sensor",
            "supportedProtocol": "http",
            "id": uid,
        },
    )
    assert r.status_code == 201, r.text
    created_ids.append(URN + uid)
    return uid


def _create_op_type(api, name="Calibration", *, requires_component=False) -> str:
    r = api.post(
        OPS,
        json={"name": name, "requires_component": requires_component},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------- operation types ----------


def test_list_empty(api):
    r = api.get(OPS)
    assert r.status_code == 200
    assert r.json() == []


def test_create_then_list(api):
    op_id = _create_op_type(api, name="Calibration")
    r = api.get(OPS)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["id"] == op_id
    assert body[0]["name"] == "Calibration"
    assert body[0]["requires_component"] is False


def test_create_duplicate_name_409(api):
    _create_op_type(api, name="Battery replacement")
    r = api.post(OPS, json={"name": "Battery replacement"})
    assert r.status_code == 409


def test_create_missing_name_422(api):
    r = api.post(OPS, json={"description": "no name"})
    assert r.status_code == 422


def test_patch_updates_fields(api):
    op_id = _create_op_type(api, name="Inspection")
    r = api.patch(
        f"{OPS}/{op_id}",
        json={"description": "Visual inspection", "requires_component": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["description"] == "Visual inspection"
    assert body["requires_component"] is True


def test_patch_unknown_404(api):
    r = api.patch(f"{OPS}/{uuid4()}", json={"description": "x"})
    assert r.status_code == 404


def test_patch_empty_body_422(api):
    op_id = _create_op_type(api, name="Patch-empty")
    r = api.patch(f"{OPS}/{op_id}", json={})
    assert r.status_code == 422


def test_delete_unknown_404(api):
    r = api.delete(f"{OPS}/{uuid4()}")
    assert r.status_code == 404


def test_delete_unreferenced_204(api):
    op_id = _create_op_type(api, name="Disposable")
    r = api.delete(f"{OPS}/{op_id}")
    assert r.status_code == 204
    r2 = api.get(OPS)
    assert r2.json() == []


def test_delete_referenced_409(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Referenced")
    create = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={
            "operation_type_id": op_id,
            "start_time": "2026-04-30T10:00:00Z",
        },
    )
    assert create.status_code == 201, create.text
    r = api.delete(f"{OPS}/{op_id}")
    assert r.status_code == 409


# ---------- maintenance log ----------


def test_create_log_201_returns_row(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Log create")
    r = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={
            "operation_type_id": op_id,
            "performed_by_id": str(uuid4()),
            "start_time": "2026-04-30T10:00:00Z",
            "end_time": "2026-04-30T10:30:00Z",
            "details_notes": "All good",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["device_id"] == uid
    assert body["operation_type_id"] == op_id
    assert body["details_notes"] == "All good"


def test_create_log_unknown_device_404(api):
    op_id = _create_op_type(api, name="Log unknown device")
    r = api.post(
        f"/api/v1/devices/{uuid4()}/maintenance/log",
        json={"operation_type_id": op_id, "start_time": "2026-04-30T10:00:00Z"},
    )
    assert r.status_code == 404


def test_create_log_unknown_operation_type_422(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={"operation_type_id": str(uuid4()), "start_time": "2026-04-30T10:00:00Z"},
    )
    assert r.status_code == 422


def test_create_log_requires_component_missing_422(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Need component", requires_component=True)
    r = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={"operation_type_id": op_id, "start_time": "2026-04-30T10:00:00Z"},
    )
    assert r.status_code == 422


def test_create_log_requires_component_present_201(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Need component ok", requires_component=True)
    r = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={
            "operation_type_id": op_id,
            "start_time": "2026-04-30T10:00:00Z",
            "component_path": "sensor_temperatura_1",
        },
    )
    assert r.status_code == 201, r.text


def test_create_log_end_before_start_400(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Bad times")
    r = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={
            "operation_type_id": op_id,
            "start_time": "2026-04-30T11:00:00Z",
            "end_time": "2026-04-30T10:00:00Z",
        },
    )
    assert r.status_code == 400


def test_list_filters_by_date_range(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Range")
    base = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    for i in range(5):
        api.post(
            f"/api/v1/devices/{uid}/maintenance/log",
            json={
                "operation_type_id": op_id,
                "start_time": (base + timedelta(days=i)).isoformat(),
            },
        )
    r = api.get(
        f"/api/v1/devices/{uid}/maintenance/log",
        params={
            "from_date": (base + timedelta(days=1)).isoformat(),
            "to_date": (base + timedelta(days=3)).isoformat(),
        },
    )
    assert r.status_code == 200, r.text
    assert len(r.json()) == 3


def test_list_pagination(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Pag")
    base = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    for i in range(7):
        api.post(
            f"/api/v1/devices/{uid}/maintenance/log",
            json={
                "operation_type_id": op_id,
                "start_time": (base + timedelta(seconds=i)).isoformat(),
            },
        )
    r1 = api.get(
        f"/api/v1/devices/{uid}/maintenance/log",
        params={"page": 1, "page_size": 3},
    )
    r2 = api.get(
        f"/api/v1/devices/{uid}/maintenance/log",
        params={"page": 2, "page_size": 3},
    )
    assert len(r1.json()) == 3
    assert len(r2.json()) == 3
    ids1 = {row["id"] for row in r1.json()}
    ids2 = {row["id"] for row in r2.json()}
    assert ids1.isdisjoint(ids2)


def test_list_bad_date_range_400(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(
        f"/api/v1/devices/{uid}/maintenance/log",
        params={"from_date": "2026-04-30T11:00:00Z", "to_date": "2026-04-30T10:00:00Z"},
    )
    assert r.status_code == 400


def test_list_bad_pagination_422(api, created_ids):
    uid = _create_device(api, created_ids)
    r = api.get(
        f"/api/v1/devices/{uid}/maintenance/log",
        params={"page": 0},
    )
    assert r.status_code == 422


def test_patch_log_partial_updates(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Partial")
    create = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={"operation_type_id": op_id, "start_time": "2026-04-30T10:00:00Z"},
    )
    log_id = create.json()["id"]
    r = api.patch(
        f"/api/v1/maintenance/log/{log_id}",
        json={"end_time": "2026-04-30T11:00:00Z", "details_notes": "Done"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["details_notes"] == "Done"
    assert body["end_time"].startswith("2026-04-30T11:00:00")


def test_patch_log_unknown_404(api):
    r = api.patch(f"/api/v1/maintenance/log/{uuid4()}", json={"details_notes": "x"})
    assert r.status_code == 404


def test_patch_log_empty_body_422(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="PEmpty")
    create = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={"operation_type_id": op_id, "start_time": "2026-04-30T10:00:00Z"},
    )
    r = api.patch(f"/api/v1/maintenance/log/{create.json()['id']}", json={})
    assert r.status_code == 422


def test_delete_log_204(api, created_ids):
    uid = _create_device(api, created_ids)
    op_id = _create_op_type(api, name="Del")
    create = api.post(
        f"/api/v1/devices/{uid}/maintenance/log",
        json={"operation_type_id": op_id, "start_time": "2026-04-30T10:00:00Z"},
    )
    log_id = create.json()["id"]
    r = api.delete(f"/api/v1/maintenance/log/{log_id}")
    assert r.status_code == 204
    r2 = api.get(f"/api/v1/devices/{uid}/maintenance/log")
    assert r2.json() == []


def test_delete_log_unknown_404(api):
    r = api.delete(f"/api/v1/maintenance/log/{uuid4()}")
    assert r.status_code == 404
