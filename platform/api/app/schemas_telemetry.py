from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TelemetryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dateObserved: str
    numValue: float
    unitCode: str | None = None


class TelemetryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deviceId: str
    controlledProperty: str
    entries: list[TelemetryEntry]


class StateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deviceState: str | None = None
    dateLastValueReported: str | None = None
    batteryLevel: float | None = None
    # Arbitrary attributes pushed via MQTT (ticket 0018). Keyed by attribute
    # name; each value is `{type, value}` mirroring the NGSI-v2 attribute.
    attributes: dict[str, dict] | None = None
