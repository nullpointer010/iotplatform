"""HTTP/LoRaWAN telemetry ingest + per-device API key (ticket 0019).

Endpoints:
- ``POST   /devices/{id}/ingest-key`` — issue or rotate the per-device key (operator).
- ``DELETE /devices/{id}/ingest-key`` — revoke the key (admin).
- ``POST   /devices/{id}/telemetry`` — push one or many measurements
  (auth = ``X-Device-Key`` header).

The ingest endpoint authenticates *off* the user-RBAC ladder (no
Keycloak account per sensor): a 40-char random secret stored hashed
in Postgres. Measurements land via the canonical writer in
``app.ingest`` so MQTT and HTTP produce identical entities.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import delete, select, update

from app.auth import Principal, get_principal, require_roles
from app.deps import OrionDep, SessionDep
from app.ingest import apply_measurement, to_iso
from app.models_ingest_keys import DeviceIngestKey
from app.mqtt_payload import infer_ngsi_type, validate_against_dataTypes
from app.ngsi import from_ngsi
from app.schemas import to_urn
from app.schemas_ingest import (
    IngestKeyOut,
    TelemetryIngestIn,
    TelemetryIngestOut,
)

router = APIRouter(prefix="/devices", tags=["ingest"])
log = logging.getLogger("app.ingest")


def _normalise_id_or_404(raw: str) -> str:
    try:
        return to_urn(raw)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")


def _device_uuid(device_urn: str) -> UUID:
    return UUID(device_urn.rsplit(":", 1)[-1])


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _generate_key() -> tuple[str, str]:
    """Return (cleartext, prefix). Prefix is the leading ``dik_<8hex>``."""
    prefix_secret = secrets.token_hex(4)  # 8 chars
    body = secrets.token_hex(16)  # 32 chars
    cleartext = f"dik_{prefix_secret}_{body}"
    prefix = f"dik_{prefix_secret}"
    return cleartext, prefix


# ─── key management ─────────────────────────────────────────────────


@router.post(
    "/{device_id}/ingest-key",
    response_model=IngestKeyOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("operator"))],
)
async def issue_ingest_key(
    device_id: str,
    orion: OrionDep,
    session: SessionDep,
    principal: Principal = Depends(get_principal),
) -> IngestKeyOut:
    eid = _normalise_id_or_404(device_id)
    if await orion.get_entity(eid) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    duuid = _device_uuid(eid)
    cleartext, prefix = _generate_key()
    key_hash = _hash_key(cleartext)
    now = datetime.now(timezone.utc)

    existing = await session.get(DeviceIngestKey, duuid)
    if existing is None:
        session.add(
            DeviceIngestKey(
                device_id=duuid,
                key_hash=key_hash,
                prefix=prefix,
                created_at=now,
                created_by=principal.username or None,
            )
        )
    else:
        existing.key_hash = key_hash
        existing.prefix = prefix
        existing.created_at = now
        existing.created_by = principal.username or None
        existing.last_used_at = None
    await session.commit()
    return IngestKeyOut(key=cleartext, prefix=prefix, createdAt=now)


@router.delete(
    "/{device_id}/ingest-key",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles())],  # admin-only
)
async def revoke_ingest_key(
    device_id: str, orion: OrionDep, session: SessionDep
) -> Response:
    eid = _normalise_id_or_404(device_id)
    if await orion.get_entity(eid) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    duuid = _device_uuid(eid)
    await session.execute(delete(DeviceIngestKey).where(DeviceIngestKey.device_id == duuid))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── ingest ─────────────────────────────────────────────────────────


@router.post(
    "/{device_id}/telemetry",
    response_model=TelemetryIngestOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_telemetry(
    device_id: str,
    body: TelemetryIngestIn,
    orion: OrionDep,
    session: SessionDep,
    request: Request,
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
) -> TelemetryIngestOut:
    eid = _normalise_id_or_404(device_id)
    entity = await orion.get_entity(eid)
    if entity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")

    # Auth: per-device API key. Off the Keycloak/RBAC ladder by design.
    if not x_device_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing X-Device-Key")
    duuid = _device_uuid(eid)
    row = await session.get(DeviceIngestKey, duuid)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no ingest key for device")
    if not hmac.compare_digest(row.key_hash, _hash_key(x_device_key)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid X-Device-Key")

    # Read declared dataTypes once (one Orion GET per request).
    parsed = from_ngsi(entity)
    data_types = parsed.get("dataTypes") or {}
    if not isinstance(data_types, dict):
        data_types = {}

    items = body.as_list()

    # Validate the whole batch first; no partial writes.
    prepared: list[tuple[str, str, object, str | None, str | None]] = []
    for m in items:
        ngsi_type, value = infer_ngsi_type(m.value)
        if not validate_against_dataTypes(m.controlledProperty, ngsi_type, value, data_types):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"value type {ngsi_type} does not match dataTypes[{m.controlledProperty}]"
                f"={data_types.get(m.controlledProperty)}",
            )
        ts_iso = to_iso(m.ts) if m.ts is not None else None
        prepared.append((m.controlledProperty, ngsi_type, value, ts_iso, m.unitCode))

    for attr, ngsi_type, value, ts_iso, unit_code in prepared:
        await apply_measurement(orion, eid, attr, ngsi_type, value, ts_iso, unit_code)

    # last_used_at bookkeeping (best-effort).
    await session.execute(
        update(DeviceIngestKey)
        .where(DeviceIngestKey.device_id == duuid)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await session.commit()

    return TelemetryIngestOut(accepted=len(prepared))
