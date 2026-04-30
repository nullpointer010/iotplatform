"""floorplans + placements

Revision ID: 0003_floorplans_and_placements
Revises: 0002_device_manuals
Create Date: 2026-05-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_floorplans_and_placements"
down_revision: str | None = "0002_device_manuals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_floorplans",
        sa.Column("site_area", sa.String(length=255), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("uploaded_by", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "device_placements",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("x_pct", sa.Float(), nullable=False),
        sa.Column("y_pct", sa.Float(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("device_placements")
    op.drop_table("site_floorplans")
