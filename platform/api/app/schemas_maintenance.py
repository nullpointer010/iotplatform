from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator


# ---------- operation types ----------


class OperationTypeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    description: str | None = None
    requires_component: bool = False


class OperationTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str | None, StringConstraints(min_length=1, max_length=100)] = None
    description: str | None = None
    requires_component: bool | None = None

    @model_validator(mode="after")
    def _at_least_one(self):
        if self.name is None and self.description is None and self.requires_component is None:
            raise ValueError("At least one field must be provided")
        return self


class OperationTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    name: str
    description: str | None = None
    requires_component: bool


# ---------- maintenance log ----------


class MaintenanceLogIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_type_id: UUID
    performed_by_id: UUID | None = None
    start_time: datetime
    end_time: datetime | None = None
    component_path: str | None = None
    details_notes: str | None = None


class MaintenanceLogUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_type_id: UUID | None = None
    performed_by_id: UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    component_path: str | None = None
    details_notes: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self):
        if self.model_dump(exclude_none=True) == {}:
            raise ValueError("At least one field must be provided")
        return self


class MaintenanceLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    device_id: UUID
    operation_type_id: UUID
    performed_by_id: UUID | None = None
    start_time: datetime
    end_time: datetime | None = None
    component_path: str | None = None
    details_notes: str | None = None
