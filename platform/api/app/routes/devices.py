from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import delete

from app.deps import OrionDep, SessionDep
from app.auth import require_roles
from app.models_maintenance import MaintenanceLog
from app.ngsi import from_ngsi, to_ngsi, to_ngsi_attrs
from app.orion import DuplicateEntity
from app.schemas import (
    DeviceIn,
    DeviceUpdate,
    Protocol,
    to_urn,
    validate_protocol_invariants,
)

router = APIRouter(prefix="/devices", tags=["devices"])


import logging

_log = logging.getLogger("app.mqtt")


def _maybe_refresh_bridge(request: Request) -> None:
    """Fire-and-forget hook so MQTT subscriptions track device CRUD."""
    bridge = getattr(request.app.state, "mqtt_bridge", None)
    if bridge is None:
        return
    import asyncio

    try:
        asyncio.create_task(bridge.refresh())
    except Exception as exc:  # pragma: no cover
        _log.warning("bridge refresh schedule failed: %s", exc)


def _normalise_id_or_400(raw: str) -> str:
    try:
        return to_urn(raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("operator"))],
)
async def create_device(payload: DeviceIn, orion: OrionDep, request: Request) -> dict:
    entity = to_ngsi(payload.model_dump(exclude_none=True))
    try:
        await orion.create_entity(entity)
    except DuplicateEntity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device {entity['id']} already exists",
        )
    fresh = await orion.get_entity(entity["id"])
    _maybe_refresh_bridge(request)
    return from_ngsi(fresh or entity)


@router.get(
    "",
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def list_devices(
    orion: OrionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    entities = await orion.list_entities(limit=limit, offset=offset)
    return [from_ngsi(e) for e in entities]


@router.get(
    "/{device_id}",
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def get_device(device_id: str, orion: OrionDep) -> dict:
    eid = _normalise_id_or_400(device_id)
    entity = await orion.get_entity(eid)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return from_ngsi(entity)


@router.patch(
    "/{device_id}",
    dependencies=[Depends(require_roles("operator"))],
)
async def patch_device(
    device_id: str, payload: DeviceUpdate, orion: OrionDep, request: Request
) -> dict:
    eid = _normalise_id_or_400(device_id)
    existing = await orion.get_entity(eid)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    patch = payload.model_dump(exclude_none=True)
    merged = {**from_ngsi(existing), **patch}
    proto_raw = merged.get("supportedProtocol")
    if proto_raw is not None:
        try:
            protocol = Protocol(proto_raw) if not isinstance(proto_raw, Protocol) else proto_raw
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"unknown supportedProtocol '{proto_raw}'",
            )
        try:
            validate_protocol_invariants(merged, protocol)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )
    attrs = to_ngsi_attrs(patch)
    ok = await orion.patch_entity(eid, attrs)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    fresh = await orion.get_entity(eid)
    _maybe_refresh_bridge(request)
    return from_ngsi(fresh or {"id": eid, "type": "Device"})


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles())],  # admin-only
)
async def delete_device(
    device_id: str, orion: OrionDep, session: SessionDep, request: Request
) -> Response:
    eid = _normalise_id_or_400(device_id)
    ok = await orion.delete_entity(eid)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    device_uuid = UUID(eid.rsplit(":", 1)[-1])
    await session.execute(
        delete(MaintenanceLog).where(MaintenanceLog.device_id == device_uuid)
    )
    await session.commit()
    _maybe_refresh_bridge(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
