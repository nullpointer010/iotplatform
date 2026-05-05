"""Canonical telemetry writer (ticket 0019).

Both the in-process MQTT bridge (0018) and the HTTP ingest endpoint
(0019) call the helpers here so the data lands in the exact same
shape: every successful publish patches ``Device:<id>`` with the
attribute and ``dateLastValueReported``, and (only when the value is
numeric) upserts ``DeviceMeasurement:<deviceUuid>:<Attr>``.

Errors during the measurement upsert are logged at WARNING and never
roll back the Device patch — ``/state`` freshness is treated as more
critical than telemetry consistency in v1.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.orion import DuplicateEntity, OrionClient, OrionError

log = logging.getLogger("app.ingest")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def to_iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def measurement_urn(device_urn: str, attr: str) -> str:
    """Mirror ``app.routes.telemetry._measurement_urn``."""
    device_uuid = device_urn.rsplit(":", 1)[-1]
    suffix = attr[:1].upper() + attr[1:]
    return f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:{suffix}"


async def upsert_measurement(
    orion: OrionClient,
    device_urn: str,
    attr: str,
    value: float,
    ts_iso: str,
    unit_code: str | None = None,
) -> None:
    """Create or update the canonical ``DeviceMeasurement`` entity.

    Tries ``POST /v2/entities`` first, falls back to
    ``POST /v2/entities/<id>/attrs`` on duplicate. Errors are logged
    at WARNING; never raised.
    """
    m_urn = measurement_urn(device_urn, attr)
    body: dict[str, Any] = {
        "id": m_urn,
        "type": "DeviceMeasurement",
        "refDevice": {"type": "Text", "value": device_urn},
        "controlledProperty": {"type": "Text", "value": attr},
        "numValue": {"type": "Number", "value": value},
        "dateObserved": {"type": "DateTime", "value": ts_iso},
    }
    if unit_code:
        body["unitCode"] = {"type": "Text", "value": unit_code}
    try:
        await orion.create_entity(body)
        return
    except DuplicateEntity:
        pass
    except OrionError as exc:
        log.warning("measurement create failed entity=%s: %s", m_urn, exc)
        return
    patch: dict[str, Any] = {
        "numValue": {"type": "Number", "value": value},
        "dateObserved": {"type": "DateTime", "value": ts_iso},
    }
    if unit_code:
        patch["unitCode"] = {"type": "Text", "value": unit_code}
    try:
        await orion.patch_entity(m_urn, patch)
    except OrionError as exc:
        log.warning("measurement patch failed entity=%s: %s", m_urn, exc)


async def apply_measurement(
    orion: OrionClient,
    device_urn: str,
    attr: str,
    ngsi_type: str,
    value: Any,
    ts_iso: str | None = None,
    unit_code: str | None = None,
) -> None:
    """Dual write: patch ``Device`` and (for numeric values) upsert
    ``DeviceMeasurement``. ``ts_iso`` defaults to UTC now.
    """
    if ts_iso is None:
        ts_iso = now_utc_iso()
    attrs = {
        attr: {"type": ngsi_type, "value": value},
        "dateLastValueReported": {"type": "DateTime", "value": ts_iso},
    }
    try:
        await orion.patch_entity(device_urn, attrs)
    except OrionError as exc:
        log.warning("device patch failed device=%s: %s", device_urn, exc)
        return
    if ngsi_type == "Number":
        await upsert_measurement(orion, device_urn, attr, value, ts_iso, unit_code)
