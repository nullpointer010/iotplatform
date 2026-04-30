"""Operational system endpoints (ticket 0018+)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth import require_roles

router = APIRouter(prefix="/system", tags=["system"])


@router.get(
    "/mqtt",
    dependencies=[Depends(require_roles())],  # admin-only
)
async def mqtt_stats(request: Request) -> dict:
    bridge = getattr(request.app.state, "mqtt_bridge", None)
    if bridge is None:
        return {
            "connected": False,
            "subscribed_topics": 0,
            "last_message_at": None,
            "dropped_invalid": 0,
        }
    return bridge.stats()
