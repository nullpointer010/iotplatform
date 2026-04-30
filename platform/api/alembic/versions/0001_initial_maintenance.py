"""initial maintenance schema

Revision ID: 0001_initial_maintenance
Revises:
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_maintenance"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance_operation_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "requires_component",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_table(
        "maintenance_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "operation_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("maintenance_operation_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("performed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("start_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("component_path", sa.String(length=255), nullable=True),
        sa.Column("details_notes", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_maintenance_log_device_id", "maintenance_log", ["device_id"]
    )
    op.create_index(
        "idx_maintenance_log_operation_type",
        "maintenance_log",
        ["operation_type_id"],
    )
    op.create_index(
        "idx_maintenance_log_start_time", "maintenance_log", ["start_time"]
    )


def downgrade() -> None:
    op.drop_index("idx_maintenance_log_start_time", table_name="maintenance_log")
    op.drop_index("idx_maintenance_log_operation_type", table_name="maintenance_log")
    op.drop_index("idx_maintenance_log_device_id", table_name="maintenance_log")
    op.drop_table("maintenance_log")
    op.drop_table("maintenance_operation_types")
