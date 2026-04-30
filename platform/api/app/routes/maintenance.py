from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import OrionDep, SessionDep
from app.models_maintenance import MaintenanceLog, MaintenanceOperationType
from app.schemas import to_urn
from app.schemas_maintenance import (
    MaintenanceLogIn,
    MaintenanceLogOut,
    MaintenanceLogUpdate,
    OperationTypeIn,
    OperationTypeOut,
    OperationTypeUpdate,
)


router = APIRouter(tags=["maintenance"])


def _normalise_device_id_or_404(raw: str) -> UUID:
    try:
        urn = to_urn(raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return UUID(urn.rsplit(":", 1)[-1])


# ---------- operation types ----------


@router.get("/maintenance/operation-types", response_model=list[OperationTypeOut])
async def list_operation_types(session: SessionDep) -> list[MaintenanceOperationType]:
    rows = await session.scalars(select(MaintenanceOperationType).order_by(MaintenanceOperationType.name))
    return list(rows)


@router.post(
    "/maintenance/operation-types",
    response_model=OperationTypeOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_operation_type(
    payload: OperationTypeIn, session: SessionDep
) -> MaintenanceOperationType:
    row = MaintenanceOperationType(
        id=uuid4(),
        name=payload.name,
        description=payload.description,
        requires_component=payload.requires_component,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Operation type '{payload.name}' already exists",
        )
    await session.refresh(row)
    return row


@router.patch("/maintenance/operation-types/{op_id}", response_model=OperationTypeOut)
async def patch_operation_type(
    op_id: UUID, payload: OperationTypeUpdate, session: SessionDep
) -> MaintenanceOperationType:
    row = await session.get(MaintenanceOperationType, op_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation type not found",
        )
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(row, k, v)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operation type name already exists",
        )
    await session.refresh(row)
    return row


@router.delete(
    "/maintenance/operation-types/{op_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_operation_type(op_id: UUID, session: SessionDep) -> Response:
    row = await session.get(MaintenanceOperationType, op_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation type not found",
        )
    await session.delete(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operation type is referenced by maintenance log entries",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- maintenance log ----------


@router.post(
    "/devices/{device_id}/maintenance/log",
    response_model=MaintenanceLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_maintenance_log(
    device_id: str,
    payload: MaintenanceLogIn,
    orion: OrionDep,
    session: SessionDep,
) -> MaintenanceLog:
    device_uuid = _normalise_device_id_or_404(device_id)

    if payload.end_time is not None and payload.end_time < payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be >= start_time",
        )

    if await orion.get_entity(f"urn:ngsi-ld:Device:{device_uuid}") is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    op_type = await session.get(MaintenanceOperationType, payload.operation_type_id)
    if op_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown operation_type_id",
        )
    if op_type.requires_component and not payload.component_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="component_path is required for this operation type",
        )

    row = MaintenanceLog(
        id=uuid4(),
        device_id=device_uuid,
        operation_type_id=payload.operation_type_id,
        performed_by_id=payload.performed_by_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        component_path=payload.component_path,
        details_notes=payload.details_notes,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.get(
    "/devices/{device_id}/maintenance/log",
    response_model=list[MaintenanceLogOut],
)
async def list_maintenance_log(
    device_id: str,
    session: SessionDep,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[MaintenanceLog]:
    device_uuid = _normalise_device_id_or_404(device_id)
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date must be <= to_date",
        )

    stmt = select(MaintenanceLog).where(MaintenanceLog.device_id == device_uuid)
    if from_date:
        stmt = stmt.where(MaintenanceLog.start_time >= from_date)
    if to_date:
        stmt = stmt.where(MaintenanceLog.start_time <= to_date)
    stmt = (
        stmt.order_by(MaintenanceLog.start_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = await session.scalars(stmt)
    return list(rows)


@router.patch("/maintenance/log/{log_id}", response_model=MaintenanceLogOut)
async def patch_maintenance_log(
    log_id: UUID, payload: MaintenanceLogUpdate, session: SessionDep
) -> MaintenanceLog:
    row = await session.get(MaintenanceLog, log_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance log entry not found",
        )

    data = payload.model_dump(exclude_none=True)
    new_start = data.get("start_time", row.start_time)
    new_end = data.get("end_time", row.end_time)
    if new_end is not None and new_end < new_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be >= start_time",
        )

    if "operation_type_id" in data:
        new_type = await session.get(MaintenanceOperationType, data["operation_type_id"])
        if new_type is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown operation_type_id",
            )

    for k, v in data.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return row


@router.delete("/maintenance/log/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_log(log_id: UUID, session: SessionDep) -> Response:
    row = await session.get(MaintenanceLog, log_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance log entry not found",
        )
    await session.delete(row)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
