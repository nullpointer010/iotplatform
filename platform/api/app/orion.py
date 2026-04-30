"""Async HTTP client for Orion Context Broker (NGSI v2)."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class OrionError(RuntimeError):
    """Unexpected upstream error from Orion."""


class DuplicateEntity(RuntimeError):
    """Orion returned 422 AlreadyExists on POST /v2/entities."""


class OrionClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._client = client
        self._base = settings.orion_url.rstrip("/")
        self._headers = {
            "Fiware-Service": settings.fiware_service,
            "Fiware-ServicePath": settings.fiware_servicepath,
        }

    async def create_entity(self, entity: dict[str, Any]) -> None:
        r = await self._client.post(
            f"{self._base}/v2/entities",
            json=entity,
            headers=self._headers,
        )
        if r.status_code == 201:
            return
        if r.status_code == 422 and "Already Exists" in r.text:
            raise DuplicateEntity(entity["id"])
        raise OrionError(f"create_entity {r.status_code}: {r.text}")

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        r = await self._client.get(
            f"{self._base}/v2/entities/{entity_id}",
            headers=self._headers,
        )
        if r.status_code == 404:
            return None
        if r.status_code == 200:
            return r.json()
        raise OrionError(f"get_entity {r.status_code}: {r.text}")

    async def list_entities(
        self,
        limit: int,
        offset: int,
        type_: str = "Device",
    ) -> list[dict[str, Any]]:
        r = await self._client.get(
            f"{self._base}/v2/entities",
            headers=self._headers,
            params={"type": type_, "limit": limit, "offset": offset},
        )
        if r.status_code == 200:
            return r.json()
        raise OrionError(f"list_entities {r.status_code}: {r.text}")

    async def patch_entity(self, entity_id: str, attrs: dict[str, Any]) -> bool:
        if not attrs:
            return True
        # POST /attrs has append-or-update semantics: missing attrs are created,
        # existing ones overwritten. PATCH would 422 on first-time attributes.
        r = await self._client.post(
            f"{self._base}/v2/entities/{entity_id}/attrs",
            json=attrs,
            headers=self._headers,
        )
        if r.status_code in (204, 200):
            return True
        if r.status_code == 404:
            return False
        raise OrionError(f"patch_entity {r.status_code}: {r.text}")

    async def delete_entity(self, entity_id: str) -> bool:
        r = await self._client.delete(
            f"{self._base}/v2/entities/{entity_id}",
            headers=self._headers,
        )
        if r.status_code == 204:
            return True
        if r.status_code == 404:
            return False
        raise OrionError(f"delete_entity {r.status_code}: {r.text}")
