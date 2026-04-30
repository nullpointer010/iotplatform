"""Routes for device manual PDFs (ticket 0016)."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from urllib.parse import quote

from app import manuals as storage
from app.auth import Principal, get_principal, require_roles
from app.deps import OrionDep, SessionDep
from app.models_manuals import DeviceManual
from app.schemas import to_urn
from app.schemas_manuals import DeviceManualOut


router = APIRouter(tags=["manuals"])


def _device_uuid_or_404(raw: str) -> UUID:
    try:
        urn = to_urn(raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return UUID(urn.rsplit(":", 1)[-1])


@router.post(
    "/devices/{device_id}/manuals",
    response_model=DeviceManualOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("operator", "maintenance_manager"))],
)
async def upload_manual(
    device_id: str,
    file: UploadFile,
    orion: OrionDep,
    session: SessionDep,
    principal: Principal = Depends(get_principal),
) -> DeviceManual:
    device_uuid = _device_uuid_or_404(device_id)
    if await orion.get_entity(f"urn:ngsi-ld:Device:{device_uuid}") is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )

    if (file.content_type or "").lower() != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File is not a PDF",
        )

    file_id = uuid4()
    try:
        size = await storage.save_streaming(file_id, file)
    except HTTPException:
        storage.delete(file_id)
        raise

    row = DeviceManual(
        id=file_id,
        device_id=device_uuid,
        filename=file.filename or f"{file_id}.pdf",
        content_type="application/pdf",
        size_bytes=size,
        storage_key=storage.storage_key(file_id),
        uploaded_by=principal.username or None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.get(
    "/devices/{device_id}/manuals",
    response_model=list[DeviceManualOut],
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def list_manuals(
    device_id: str, orion: OrionDep, session: SessionDep
) -> list[DeviceManual]:
    device_uuid = _device_uuid_or_404(device_id)
    if await orion.get_entity(f"urn:ngsi-ld:Device:{device_uuid}") is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )
    rows = await session.scalars(
        select(DeviceManual)
        .where(DeviceManual.device_id == device_uuid)
        .order_by(DeviceManual.uploaded_at.desc())
    )
    return list(rows)


@router.get(
    "/manuals/{manual_id}",
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def download_manual(manual_id: UUID, session: SessionDep) -> FileResponse:
    row = await session.get(DeviceManual, manual_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manual not found"
        )
    p = storage.path_for(manual_id)
    if not p.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manual not found"
        )
    return FileResponse(
        p,
        media_type=row.content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(row.filename)}"
        },
    )


@router.delete(
    "/manuals/{manual_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles())],  # admin only (admin is implicit)
)
async def delete_manual(manual_id: UUID, session: SessionDep) -> Response:
    row = await session.get(DeviceManual, manual_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Manual not found"
        )
    await session.delete(row)
    await session.commit()
    storage.delete(manual_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
