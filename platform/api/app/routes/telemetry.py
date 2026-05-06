from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import require_roles
from app.deps import OrionDep, QuantumLeapDep
from app.schemas import DeviceIn, to_urn
from app.schemas_telemetry import (
    AggrMethod,
    AggrPeriod,
    StateResponse,
    TelemetryEntry,
    TelemetryResponse,
)

router = APIRouter(prefix="/devices", tags=["telemetry"])


_STATE_ATTRS = ("deviceState", "dateLastValueReported", "batteryLevel")
# Attribute names that belong to the Device metadata schema (not telemetry).
# Anything outside this set comes from MQTT publishes and goes into
# `StateResponse.attributes` (ticket 0018).
_DEVICE_META_FIELDS = set(DeviceIn.model_fields.keys()) | {"id", "type", "TimeInstant"}


def _normalise_id_or_404(raw: str) -> str:
    try:
        return to_urn(raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )


def _measurement_urn(device_urn: str, controlled_property: str) -> str:
    # device_urn is "urn:ngsi-ld:Device:<uuid>"
    uuid = device_urn.rsplit(":", 1)[-1]
    suffix = controlled_property[:1].upper() + controlled_property[1:]
    return f"urn:ngsi-ld:DeviceMeasurement:{uuid}:{suffix}"


def _to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    # QL accepts ISO-8601; ensure timezone-aware → UTC string.
    return dt.isoformat()


@router.get(
    "/{device_id}/telemetry",
    response_model=TelemetryResponse,
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def get_telemetry(
    device_id: str,
    orion: OrionDep,
    ql: QuantumLeapDep,
    controlledProperty: Annotated[str, Query(min_length=1, pattern=r"^[A-Za-z0-9_]+$")],
    fromDate: datetime | None = None,
    toDate: datetime | None = None,
    lastN: Annotated[int | None, Query(ge=1, le=1000)] = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    aggrMethod: AggrMethod = "none",
    aggrPeriod: AggrPeriod | None = None,
) -> TelemetryResponse:
    if fromDate and toDate and fromDate > toDate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fromDate must be <= toDate",
        )
    if aggrMethod != "none" and aggrPeriod is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="aggrPeriod is required when aggrMethod is set",
        )

    device_urn = _normalise_id_or_404(device_id)
    if await orion.get_entity(device_urn) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    measurement_urn = _measurement_urn(device_urn, controlledProperty)
    from_iso = _to_iso(fromDate)
    to_iso = _to_iso(toDate)

    if aggrMethod != "none":
        # Bucketed mode: single QL call with the chosen avg period.
        # `lastN`/`limit`/`offset` are ignored.
        payload = await ql.query_entity(
            measurement_urn,
            type_="DeviceMeasurement",
            attrs="numValue",
            from_date=from_iso,
            to_date=to_iso,
            aggr_method=aggrMethod,
            aggr_period=aggrPeriod,
        )
        entries: list[TelemetryEntry] = []
        if payload is not None:
            index = payload.get("index", []) or []
            vals = _values(payload, "numValue")
            for i, ts in enumerate(index):
                v = vals[i] if i < len(vals) else None
                if v is None:
                    continue
                entries.append(
                    TelemetryEntry(dateObserved=ts, numValue=float(v))
                )
        return TelemetryResponse(
            deviceId=device_urn,
            controlledProperty=controlledProperty,
            aggrMethod=aggrMethod,
            aggrPeriod=aggrPeriod,
            entries=entries,
        )

    # Raw mode: existing behaviour, plus best-effort total via
    # QuantumLeap's options=count.
    payload = await ql.query_entity(
        measurement_urn,
        type_="DeviceMeasurement",
        attrs="numValue,unitCode",
        from_date=from_iso,
        to_date=to_iso,
        last_n=lastN,
        limit=None if lastN is not None else limit,
        offset=offset,
    )

    entries = []
    if payload is not None:
        index: list[str] = payload.get("index", []) or []
        num_values = _values(payload, "numValue")
        unit_codes = _values(payload, "unitCode")
        for i, ts in enumerate(index):
            num = num_values[i] if i < len(num_values) else None
            if num is None:
                continue
            unit = unit_codes[i] if i < len(unit_codes) else None
            entries.append(
                TelemetryEntry(
                    dateObserved=ts,
                    numValue=float(num),
                    unitCode=unit if unit not in (None, "") else None,
                )
            )

    total: int | None = None
    try:
        total = await ql.count_entity(
            measurement_urn,
            type_="DeviceMeasurement",
            attrs="numValue",
            from_date=from_iso,
            to_date=to_iso,
        )
    except Exception:
        total = None

    return TelemetryResponse(
        deviceId=device_urn,
        controlledProperty=controlledProperty,
        aggrMethod="none",
        aggrPeriod=None,
        total=total,
        entries=entries,
    )


def _values(payload: dict, attr: str) -> list:
    for a in payload.get("attributes", []) or []:
        if a.get("attrName") == attr:
            return a.get("values", []) or []
    return []


@router.get(
    "/{device_id}/state",
    response_model=StateResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def get_state(device_id: str, orion: OrionDep) -> StateResponse:
    device_urn = _normalise_id_or_404(device_id)
    entity = await orion.get_entity(device_urn)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    projected: dict[str, object] = {}
    for attr in _STATE_ATTRS:
        if attr in entity and isinstance(entity[attr], dict) and "value" in entity[attr]:
            value = entity[attr]["value"]
            if value not in (None, ""):
                projected[attr] = value
    extras: dict[str, dict] = {}
    for name, raw in entity.items():
        if name in _DEVICE_META_FIELDS or name in _STATE_ATTRS:
            continue
        if not isinstance(raw, dict) or "value" not in raw:
            continue
        extras[name] = {"type": raw.get("type", "Text"), "value": raw["value"]}
    if extras:
        projected["attributes"] = extras
    return StateResponse(**projected)
