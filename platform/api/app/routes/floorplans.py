"""Routes for site floor plans + device placements (ticket 0017)."""

from __future__ import annotations

from collections import Counter
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select

from app import floorplans as storage
from app.auth import Principal, get_principal, require_roles
from app.deps import OrionDep, SessionDep
from app.models_floorplans import DevicePlacement, SiteFloorplan
from app.ngsi import from_ngsi
from app.schemas import to_urn
from app.schemas_floorplans import (
    FloorplanOut,
    PlacementIn,
    PlacementOut,
    SiteSummary,
)


router = APIRouter(tags=["sites"])


# ---------- helpers ----------


async def _all_devices(orion) -> list[dict]:
    """Fetch every device from Orion, paginating to be safe."""
    out: list[dict] = []
    offset = 0
    page = 1000
    while True:
        chunk = await orion.list_entities(limit=page, offset=offset)
        if not chunk:
            break
        out.extend(chunk)
        if len(chunk) < page:
            break
        offset += page
    return [from_ngsi(e) for e in out]


def _device_uuid_or_404(raw: str) -> UUID:
    try:
        urn = to_urn(raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )
    return UUID(urn.rsplit(":", 1)[-1])


def _site_area_of(device: dict) -> str | None:
    loc = device.get("location") or {}
    sa = loc.get("site_area") if isinstance(loc, dict) else None
    if isinstance(sa, str) and sa.strip():
        return sa
    return None


def _device_state_of(device: dict) -> str | None:
    """Return the device's `deviceState` value as a plain string, if any."""
    s = device.get("deviceState")
    if isinstance(s, str) and s.strip():
        return s
    return None


def _primary_property_of(device: dict) -> str | None:
    """First entry of the device's `controlledProperty` list, if any."""
    cp = device.get("controlledProperty")
    if isinstance(cp, list) and cp:
        first = cp[0]
        if isinstance(first, str) and first.strip():
            return first
    return None


# ---------- /sites ----------


@router.get(
    "/sites",
    response_model=list[SiteSummary],
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def list_sites(orion: OrionDep, session: SessionDep) -> list[SiteSummary]:
    devices = await _all_devices(orion)
    counts: Counter[str] = Counter()
    for d in devices:
        sa = _site_area_of(d)
        if sa:
            counts[sa] += 1
    plans = {
        row.site_area
        for row in await session.scalars(select(SiteFloorplan))
    }
    return [
        SiteSummary(site_area=sa, device_count=n, has_floorplan=sa in plans)
        for sa, n in sorted(counts.items())
    ]


# ---------- /sites/{site_area}/floorplan ----------


@router.put(
    "/sites/{site_area}/floorplan",
    response_model=FloorplanOut,
    dependencies=[Depends(require_roles("operator", "maintenance_manager"))],
)
async def upload_floorplan(
    site_area: str,
    file: UploadFile,
    session: SessionDep,
    response: Response,
    principal: Principal = Depends(get_principal),
) -> SiteFloorplan:
    size, ext = await storage.save_streaming(site_area, file)
    existing = await session.get(SiteFloorplan, site_area)
    if existing is None:
        row = SiteFloorplan(
            site_area=site_area,
            filename=file.filename or f"{site_area}.{ext}",
            content_type=storage.content_type_for(ext),
            size_bytes=size,
            storage_key=storage.storage_key(site_area, ext),
            uploaded_by=principal.username or None,
        )
        session.add(row)
        response.status_code = status.HTTP_201_CREATED
    else:
        existing.filename = file.filename or f"{site_area}.{ext}"
        existing.content_type = storage.content_type_for(ext)
        existing.size_bytes = size
        existing.storage_key = storage.storage_key(site_area, ext)
        existing.uploaded_by = principal.username or None
        from sqlalchemy import func as _f
        existing.uploaded_at = _f.now()  # type: ignore[assignment]
        row = existing
        response.status_code = status.HTTP_200_OK
    await session.commit()
    await session.refresh(row)
    return row


@router.get(
    "/sites/{site_area}/floorplan",
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def get_floorplan(site_area: str, session: SessionDep) -> FileResponse:
    row = await session.get(SiteFloorplan, site_area)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found"
        )
    ext = row.storage_key.rsplit(".", 1)[-1]
    p = storage.path_for(site_area, ext)
    if not p.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found"
        )
    return FileResponse(
        p,
        media_type=row.content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(row.filename)}"
        },
    )


@router.delete(
    "/sites/{site_area}/floorplan",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles())],  # admin only
)
async def delete_floorplan(site_area: str, session: SessionDep) -> Response:
    row = await session.get(SiteFloorplan, site_area)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Floor plan not found"
        )
    ext = row.storage_key.rsplit(".", 1)[-1]
    await session.delete(row)
    await session.commit()
    storage.delete(site_area, ext)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- /sites/{site_area}/placements ----------


@router.get(
    "/sites/{site_area}/placements",
    response_model=list[PlacementOut],
    dependencies=[Depends(require_roles("viewer", "operator", "maintenance_manager"))],
)
async def list_placements(
    site_area: str, orion: OrionDep, session: SessionDep
) -> list[PlacementOut]:
    devices = await _all_devices(orion)
    devs = [d for d in devices if _site_area_of(d) == site_area]
    placements = {
        row.device_id: row
        for row in await session.scalars(select(DevicePlacement))
    }
    out: list[PlacementOut] = []
    for d in devs:
        try:
            uid = UUID(str(d["id"]).rsplit(":", 1)[-1])
        except (ValueError, KeyError):
            continue
        p = placements.get(uid)
        out.append(
            PlacementOut(
                device_id=uid,
                name=d.get("name"),
                x_pct=p.x_pct if p else None,
                y_pct=p.y_pct if p else None,
                device_state=_device_state_of(d),
                primary_property=_primary_property_of(d),
            )
        )
    return out


# ---------- /devices/{id}/placement ----------


@router.put(
    "/devices/{device_id}/placement",
    response_model=PlacementOut,
    dependencies=[Depends(require_roles("operator", "maintenance_manager"))],
)
async def upsert_placement(
    device_id: str,
    payload: PlacementIn,
    orion: OrionDep,
    session: SessionDep,
    principal: Principal = Depends(get_principal),
) -> PlacementOut:
    device_uuid = _device_uuid_or_404(device_id)
    entity = await orion.get_entity(f"urn:ngsi-ld:Device:{device_uuid}")
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
        )
    row = await session.get(DevicePlacement, device_uuid)
    if row is None:
        row = DevicePlacement(
            device_id=device_uuid,
            x_pct=payload.x_pct,
            y_pct=payload.y_pct,
            updated_by=principal.username or None,
        )
        session.add(row)
    else:
        row.x_pct = payload.x_pct
        row.y_pct = payload.y_pct
        row.updated_by = principal.username or None
        from sqlalchemy import func as _f
        row.updated_at = _f.now()  # type: ignore[assignment]
    await session.commit()
    await session.refresh(row)
    parsed = from_ngsi(entity)
    return PlacementOut(
        device_id=row.device_id,
        name=parsed.get("name"),
        x_pct=row.x_pct,
        y_pct=row.y_pct,
        device_state=_device_state_of(parsed),
        primary_property=_primary_property_of(parsed),
    )


@router.delete(
    "/devices/{device_id}/placement",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles())],  # admin only
)
async def delete_placement(device_id: str, session: SessionDep) -> Response:
    device_uuid = _device_uuid_or_404(device_id)
    row = await session.get(DevicePlacement, device_uuid)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Placement not found"
        )
    await session.delete(row)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
