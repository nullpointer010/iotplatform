from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.orion import OrionClient
from app.quantumleap import QuantumLeapClient


def get_orion(request: Request) -> OrionClient:
    return request.app.state.orion


def get_ql(request: Request) -> QuantumLeapClient:
    return request.app.state.ql


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session


OrionDep = Annotated[OrionClient, Depends(get_orion)]
QuantumLeapDep = Annotated[QuantumLeapClient, Depends(get_ql)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
