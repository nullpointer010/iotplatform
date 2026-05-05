"""Pydantic schemas for the HTTP ingest endpoint (ticket 0019)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_ATTR_RE = re.compile(r"^[A-Za-z0-9_]+$")


class MeasurementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    controlledProperty: str = Field(min_length=1, max_length=64)
    value: Any
    ts: datetime | None = None
    unitCode: str | None = Field(default=None, max_length=16)

    @field_validator("controlledProperty")
    @classmethod
    def _attr_shape(cls, v: str) -> str:
        if not _ATTR_RE.match(v):
            raise ValueError("controlledProperty must match ^[A-Za-z0-9_]+$")
        return v


class TelemetryIngestIn(BaseModel):
    """Single (top-level fields) or batch (`measurements`)."""
    model_config = ConfigDict(extra="forbid")
    controlledProperty: str | None = Field(default=None, min_length=1, max_length=64)
    value: Any = None
    ts: datetime | None = None
    unitCode: str | None = Field(default=None, max_length=16)
    measurements: list[MeasurementIn] | None = Field(default=None, max_length=100)

    @field_validator("controlledProperty")
    @classmethod
    def _attr_shape(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _ATTR_RE.match(v):
            raise ValueError("controlledProperty must match ^[A-Za-z0-9_]+$")
        return v

    @model_validator(mode="after")
    def _exactly_one_shape(self) -> "TelemetryIngestIn":
        single = self.controlledProperty is not None
        batch = self.measurements is not None
        if single and batch:
            raise ValueError(
                "send either {controlledProperty,value,...} OR {measurements:[...]}, not both"
            )
        if not single and not batch:
            raise ValueError("missing measurement: provide controlledProperty+value or measurements")
        if single and self.value is None:
            raise ValueError("value is required when controlledProperty is set")
        if batch and len(self.measurements or []) < 1:
            raise ValueError("measurements must not be empty")
        return self

    def as_list(self) -> list[MeasurementIn]:
        if self.measurements is not None:
            return list(self.measurements)
        return [
            MeasurementIn(
                controlledProperty=self.controlledProperty or "",
                value=self.value,
                ts=self.ts,
                unitCode=self.unitCode,
            )
        ]


class TelemetryIngestOut(BaseModel):
    accepted: int


class IngestKeyOut(BaseModel):
    key: str
    prefix: str
    createdAt: datetime
