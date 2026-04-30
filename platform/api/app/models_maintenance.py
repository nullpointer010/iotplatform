"""SQLAlchemy 2.0 ORM models for maintenance tables."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class MaintenanceOperationType(Base):
    __tablename__ = "maintenance_operation_types"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_component: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MaintenanceLog(Base):
    __tablename__ = "maintenance_log"
    __table_args__ = (
        Index("idx_maintenance_log_device_id", "device_id"),
        Index("idx_maintenance_log_operation_type", "operation_type_id"),
        Index("idx_maintenance_log_start_time", "start_time"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    operation_type_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("maintenance_operation_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    performed_by_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    start_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    component_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    operation_type: Mapped[MaintenanceOperationType] = relationship(lazy="joined")
