"""Bidirectional translation between API JSON and NGSI v2 normalised entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any


# Attribute name -> NGSI type. Values not in this map default to Text on render
# and are returned as-is on parse.
_NGSI_TYPE: dict[str, str] = {
    # base
    "location": "geo:point",
    "controlledProperty": "StructuredValue",
    "owner": "StructuredValue",
    "ipAddress": "StructuredValue",
    "address": "StructuredValue",
    "dateInstalled": "DateTime",
    # mqtt
    "mqttQos": "Number",
    "dataTypes": "StructuredValue",
    "mqttSecurity": "StructuredValue",
    # plc
    "plcPort": "Number",
    "plcReadFrequency": "Number",
    "plcCredentials": "StructuredValue",
    "plcTagsMapping": "StructuredValue",
}


def _render_value(name: str, value: Any) -> Any:
    if name == "location" and isinstance(value, dict):
        return f"{value['latitude']},{value['longitude']}"
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return value


def _parse_value(name: str, attr: dict[str, Any]) -> Any:
    value = attr.get("value")
    if name == "location" and isinstance(value, str) and "," in value:
        lat, lon = value.split(",", 1)
        return {"latitude": float(lat), "longitude": float(lon)}
    return value


def to_ngsi(payload: dict[str, Any]) -> dict[str, Any]:
    """Render a Pydantic-dumped device dict into an NGSI v2 normalised entity.

    `payload` MUST already include `id` (URN). Optional attributes that are
    `None` are omitted (per data-model.md §Optional attributes).
    """
    entity: dict[str, Any] = {"id": payload["id"], "type": "Device"}
    for name, value in payload.items():
        if name in ("id", "type") or value is None:
            continue
        ngsi_type = _NGSI_TYPE.get(name, "Text")
        entity[name] = {"type": ngsi_type, "value": _render_value(name, value)}
    return entity


def to_ngsi_attrs(payload: dict[str, Any]) -> dict[str, Any]:
    """Like `to_ngsi` but for PATCH: no id/type, just attributes."""
    attrs: dict[str, Any] = {}
    for name, value in payload.items():
        if value is None:
            continue
        ngsi_type = _NGSI_TYPE.get(name, "Text")
        attrs[name] = {"type": ngsi_type, "value": _render_value(name, value)}
    return attrs


def from_ngsi(entity: dict[str, Any]) -> dict[str, Any]:
    """Parse an Orion entity back into the API JSON shape."""
    out: dict[str, Any] = {"id": entity["id"], "type": entity.get("type", "Device")}
    for name, attr in entity.items():
        if name in ("id", "type"):
            continue
        if not isinstance(attr, dict) or "value" not in attr:
            continue
        out[name] = _parse_value(name, attr)
    return out
