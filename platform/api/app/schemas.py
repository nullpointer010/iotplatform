from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


URN_PREFIX = "urn:ngsi-ld:Device:"

# MQTT topic: at least one segment, no leading/trailing slash, no whitespace,
# no MQTT subscription wildcards `+` or `#`.
_MQTT_TOPIC_RE = re.compile(r"^[^/+#\s]+(?:/[^/+#\s]+)*$")
_HEX16_RE = re.compile(r"^[0-9A-Fa-f]{16}$")
_HEX32_RE = re.compile(r"^[0-9A-Fa-f]{32}$")


class Category(str, Enum):
    sensor = "sensor"
    actuator = "actuator"
    gateway = "gateway"
    plc = "plc"
    iotStation = "iotStation"
    endgun = "endgun"
    weatherStation = "weatherStation"
    other = "other"


class Protocol(str, Enum):
    mqtt = "mqtt"
    coap = "coap"
    http = "http"
    modbus = "modbus"
    bacnet = "bacnet"
    lorawan = "lorawan"
    plc = "plc"
    other = "other"


class DeviceState(str, Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"


class GeoPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


_PROTOCOL_REQUIRED: dict[Protocol, tuple[str, ...]] = {
    Protocol.mqtt: ("mqttTopicRoot", "mqttClientId"),
    Protocol.plc: ("plcIpAddress", "plcPort", "plcConnectionMethod", "plcTagsMapping"),
    Protocol.lorawan: (
        "loraAppEui",
        "loraDevEui",
        "loraAppKey",
        "loraNetworkServer",
        "loraPayloadDecoder",
    ),
}

# All extension fields tied to a given protocol. Required ⊆ this set.
_PROTOCOL_FIELDS: dict[Protocol, tuple[str, ...]] = {
    Protocol.mqtt: (
        "mqttTopicRoot",
        "mqttClientId",
        "mqttQos",
        "dataTypes",
        "mqttSecurity",
    ),
    Protocol.plc: (
        "plcIpAddress",
        "plcPort",
        "plcConnectionMethod",
        "plcCredentials",
        "plcReadFrequency",
        "plcTagsMapping",
    ),
    Protocol.lorawan: (
        "loraAppEui",
        "loraDevEui",
        "loraAppKey",
        "loraNetworkServer",
        "loraPayloadDecoder",
    ),
}


def validate_protocol_invariants(
    merged: dict[str, Any], protocol: Protocol
) -> None:
    """Raise ValueError if merged device state violates protocol invariants.

    Enforces:
      * required fields per protocol are present (non-None).
      * no extension field belonging to a *different* protocol is present.
    """
    required = _PROTOCOL_REQUIRED.get(protocol, ())
    missing = [f for f in required if merged.get(f) is None]
    if missing:
        raise ValueError(
            f"protocol '{protocol.value}' requires: {', '.join(missing)}"
        )
    for other, fields in _PROTOCOL_FIELDS.items():
        if other == protocol:
            continue
        leaked = [f for f in fields if merged.get(f) is not None]
        if leaked:
            raise ValueError(
                f"fields {leaked} belong to protocol '{other.value}', "
                f"not '{protocol.value}'"
            )


class _DeviceCommon(BaseModel):
    """Fields shared between create and update payloads."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    category: Category | None = None
    controlledProperty: list[str] | None = None
    serialNumber: str | None = None
    serialNumberType: str | None = None
    supportedProtocol: Protocol | None = None
    location: GeoPoint | None = None
    address: dict[str, Any] | None = None
    manufacturerName: str | None = None
    modelName: str | None = None
    dateInstalled: datetime | None = None
    owner: list[str] | None = None
    firmwareVersion: str | None = None
    ipAddress: list[str] | None = None
    deviceState: DeviceState | None = None

    # MQTT
    mqttTopicRoot: str | None = None
    mqttClientId: str | None = None
    mqttQos: int | None = Field(default=None, ge=0, le=2)
    dataTypes: dict[str, Any] | None = None
    mqttSecurity: dict[str, Any] | None = None

    # PLC
    plcIpAddress: str | None = None
    plcPort: int | None = Field(default=None, ge=1, le=65535)
    plcConnectionMethod: str | None = None
    plcCredentials: dict[str, Any] | None = None
    plcReadFrequency: int | None = Field(default=None, ge=1)
    plcTagsMapping: dict[str, Any] | None = None

    # LoRaWAN
    loraAppEui: str | None = None
    loraDevEui: str | None = None
    loraAppKey: str | None = None
    loraNetworkServer: str | None = None
    loraPayloadDecoder: str | None = None

    @field_validator("mqttTopicRoot")
    @classmethod
    def _v_mqtt_topic(cls, v: str | None) -> str | None:
        if v is not None and not _MQTT_TOPIC_RE.match(v):
            raise ValueError(
                "mqttTopicRoot must have no leading/trailing '/', no whitespace, "
                "no '+' or '#' wildcards"
            )
        return v

    @field_validator("plcIpAddress")
    @classmethod
    def _v_plc_ip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ipaddress.IPv4Address(v)
        except ValueError as exc:
            raise ValueError(f"plcIpAddress must be a valid IPv4 address: {exc}")
        return v

    @field_validator("loraAppEui", "loraDevEui")
    @classmethod
    def _v_lora_eui(cls, v: str | None) -> str | None:
        if v is not None and not _HEX16_RE.match(v):
            raise ValueError("must be 16 hexadecimal characters")
        return v

    @field_validator("loraAppKey")
    @classmethod
    def _v_lora_appkey(cls, v: str | None) -> str | None:
        if v is not None and not _HEX32_RE.match(v):
            raise ValueError("loraAppKey must be 32 hexadecimal characters")
        return v


class DeviceIn(_DeviceCommon):
    """Body for POST /devices. Required fields enforced here."""

    id: str | None = None  # bare UUID or URN; generated if omitted
    name: str
    category: Category
    supportedProtocol: Protocol

    @model_validator(mode="after")
    def _check_protocol_requirements(self) -> "DeviceIn":
        validate_protocol_invariants(
            self.model_dump(exclude_none=True), self.supportedProtocol
        )
        return self

    @model_validator(mode="after")
    def _normalise_id(self) -> "DeviceIn":
        self.id = to_urn(self.id)
        return self


class DeviceUpdate(_DeviceCommon):
    """Body for PATCH /devices/{id}. All fields optional, no protocol cross-checks."""


def to_urn(id_in: str | None) -> str:
    """Accept bare UUID or URN; return URN. Raises ValueError on bad UUID."""
    if id_in is None:
        return URN_PREFIX + str(uuid4())
    if id_in.startswith(URN_PREFIX):
        UUID(id_in[len(URN_PREFIX):])
        return id_in
    UUID(id_in)
    return URN_PREFIX + id_in
