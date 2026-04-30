"""GET /me — echoes the current user identity from the validated token.

Used by the web to drive role-aware UI (ticket 0015).
"""

from fastapi import APIRouter, Depends

from app.auth import Principal, get_principal

router = APIRouter()


@router.get("/me")
def me(p: Principal = Depends(get_principal)) -> dict:
    return {"username": p.username, "sub": p.sub, "roles": sorted(p.roles)}
