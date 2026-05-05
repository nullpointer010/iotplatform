"""ORM model for per-device ingest keys (ticket 0019)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DeviceIngestKey(Base):
    __tablename__ = "device_ingest_keys"

    device_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
