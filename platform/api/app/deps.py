from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.orion import OrionClient


def get_orion(request: Request) -> OrionClient:
    return request.app.state.orion


OrionDep = Annotated[OrionClient, Depends(get_orion)]
