"""Pure helpers for MQTT bridge payload handling (ticket 0018).

Kept separate from `mqtt_bridge` so they are testable without a broker.
"""
from __future__ import annotations

import json
from typing import Any


class PayloadError(ValueError):
    """Raised when a payload cannot be turned into an NGSI-v2 value."""


def parse_payload(raw: bytes, max_bytes: int) -> Any:
    """Decode a raw MQTT payload into a Python value.

    - Rejects payloads larger than `max_bytes`.
    - Strips the ``{"value": <x>}`` wrapper if present.
    - Accepts a bare JSON scalar / object / array.
    """
    if len(raw) > max_bytes:
        raise PayloadError(f"payload too large ({len(raw)} > {max_bytes} bytes)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PayloadError(f"payload is not valid UTF-8: {exc}") from exc
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PayloadError(f"payload is not valid JSON: {exc.msg}") from exc
    if isinstance(decoded, dict) and set(decoded.keys()) == {"value"}:
        return decoded["value"]
    return decoded


def infer_ngsi_type(value: Any) -> tuple[str, Any]:
    """Map a Python value to an NGSI-v2 ``(type, value)`` pair.

    `bool` is *not* a Number (despite being a Python ``int`` subclass).
    Integers are upcast to ``float`` so they round-trip through Orion as
    ``Number`` regardless of the wire shape.
    """
    if isinstance(value, bool):
        return ("Boolean", value)
    if isinstance(value, int):
        return ("Number", float(value))
    if isinstance(value, float):
        return ("Number", value)
    if isinstance(value, str):
        return ("Text", value)
    if isinstance(value, (dict, list)):
        return ("StructuredValue", value)
    if value is None:
        return ("Text", "")
    raise PayloadError(f"unsupported value type: {type(value).__name__}")


def validate_against_dataTypes(
    attr: str,
    ngsi_type: str,
    value: Any,
    data_types: dict[str, str] | None,
) -> bool:
    """Return True iff `(attr, ngsi_type)` is consistent with `data_types`.

    When `data_types` is None or `attr` not declared, validation is
    skipped (returns True). Numeric int→float is already handled in
    `infer_ngsi_type`, so the wire-level type check here is exact.
    """
    if not data_types or attr not in data_types:
        return True
    expected = data_types[attr]
    if expected == ngsi_type:
        return True
    # Boolean published into a Number slot is rejected (would mask bugs).
    return False
