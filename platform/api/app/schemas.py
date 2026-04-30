from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


URN_PREFIX = "urn:ngsi-ld:Device:"


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


class DeviceIn(_DeviceCommon):
    """Body for POST /devices. Required fields enforced here."""

    id: str | None = None  # bare UUID or URN; generated if omitted
    name: str
    category: Category
    supportedProtocol: Protocol

    @model_validator(mode="after")
    def _check_protocol_requirements(self) -> "DeviceIn":
        required = _PROTOCOL_REQUIRED.get(self.supportedProtocol, ())
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(
                f"protocol '{self.supportedProtocol.value}' requires: {', '.join(missing)}"
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
