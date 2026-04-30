"""Pydantic schemas for floor plans + placements (ticket 0017)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SiteSummary(BaseModel):
    site_area: str
    device_count: int
    has_floorplan: bool


class FloorplanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    site_area: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    uploaded_by: str | None


class PlacementIn(BaseModel):
    x_pct: float = Field(ge=0.0, le=100.0)
    y_pct: float = Field(ge=0.0, le=100.0)


class PlacementOut(BaseModel):
    device_id: UUID
    name: str | None
    x_pct: float | None
    y_pct: float | None
