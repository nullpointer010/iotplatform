from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.orion import OrionClient
from app.quantumleap import QuantumLeapClient


def get_orion(request: Request) -> OrionClient:
    return request.app.state.orion


def get_ql(request: Request) -> QuantumLeapClient:
    return request.app.state.ql


OrionDep = Annotated[OrionClient, Depends(get_orion)]
QuantumLeapDep = Annotated[QuantumLeapClient, Depends(get_ql)]
