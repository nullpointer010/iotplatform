"""device_manuals table

Revision ID: 0002_device_manuals
Revises: 0001_initial_maintenance
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_device_manuals"
down_revision: str | None = "0001_initial_maintenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_manuals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("uploaded_by", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "idx_device_manuals_device_id", "device_manuals", ["device_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_device_manuals_device_id", table_name="device_manuals")
    op.drop_table("device_manuals")
