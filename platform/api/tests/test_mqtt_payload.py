"""Unit tests for the MQTT payload helpers (ticket 0018)."""
from __future__ import annotations

import pytest

from app.mqtt_payload import (
    PayloadError,
    infer_ngsi_type,
    parse_payload,
    validate_against_dataTypes,
)


# ─── parse_payload ───────────────────────────────────────────────────


def test_parse_payload_unwraps_value_envelope() -> None:
    assert parse_payload(b'{"value": 24.7}', 1024) == 24.7


def test_parse_payload_accepts_bare_scalar() -> None:
    assert parse_payload(b"42", 1024) == 42
    assert parse_payload(b"true", 1024) is True
    assert parse_payload(b'"hi"', 1024) == "hi"


def test_parse_payload_accepts_object() -> None:
    assert parse_payload(b'{"a": 1, "b": 2}', 1024) == {"a": 1, "b": 2}


def test_parse_payload_rejects_oversized() -> None:
    with pytest.raises(PayloadError):
        parse_payload(b"x" * 1025, 1024)


def test_parse_payload_rejects_non_json() -> None:
    with pytest.raises(PayloadError):
        parse_payload(b"not-json", 1024)


# ─── infer_ngsi_type ─────────────────────────────────────────────────


def test_infer_int_is_number_float() -> None:
    assert infer_ngsi_type(24) == ("Number", 24.0)


def test_infer_bool_is_boolean_not_number() -> None:
    assert infer_ngsi_type(True) == ("Boolean", True)
    assert infer_ngsi_type(False) == ("Boolean", False)


def test_infer_float_is_number() -> None:
    assert infer_ngsi_type(24.7) == ("Number", 24.7)


def test_infer_str_is_text() -> None:
    assert infer_ngsi_type("hi") == ("Text", "hi")


def test_infer_dict_is_structuredvalue() -> None:
    assert infer_ngsi_type({"a": 1}) == ("StructuredValue", {"a": 1})


def test_infer_list_is_structuredvalue() -> None:
    assert infer_ngsi_type([1, 2, 3]) == ("StructuredValue", [1, 2, 3])


# ─── validate_against_dataTypes ──────────────────────────────────────


def test_validate_match() -> None:
    assert validate_against_dataTypes("temp", "Number", 24.0, {"temp": "Number"})


def test_validate_skipped_when_no_dataTypes() -> None:
    assert validate_against_dataTypes("temp", "Number", 24.0, None)
    assert validate_against_dataTypes("temp", "Number", 24.0, {})


def test_validate_skipped_when_attr_not_declared() -> None:
    assert validate_against_dataTypes("temp", "Number", 24.0, {"door": "Boolean"})


def test_validate_rejects_bool_for_number_slot() -> None:
    assert not validate_against_dataTypes("door", "Boolean", True, {"door": "Number"})


def test_validate_rejects_text_for_number_slot() -> None:
    # Comes from a string payload published to a Number-typed attr.
    assert not validate_against_dataTypes("temp", "Text", "42", {"temp": "Number"})
