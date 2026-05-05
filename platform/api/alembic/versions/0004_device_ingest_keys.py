"""device ingest keys (ticket 0019)

Revision ID: 0004_device_ingest_keys
Revises: 0003_floorplans_and_placements
Create Date: 2026-05-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_device_ingest_keys"
down_revision: str | None = "0003_floorplans_and_placements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_ingest_keys",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("device_ingest_keys")
