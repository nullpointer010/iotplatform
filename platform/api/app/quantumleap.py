"""Async HTTP client for QuantumLeap REST API."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class QuantumLeapError(RuntimeError):
    """Unexpected upstream error from QuantumLeap."""


class QuantumLeapClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._client = client
        self._base = settings.quantumleap_url.rstrip("/")
        self._headers = {
            "Fiware-Service": settings.fiware_service,
            "Fiware-ServicePath": settings.fiware_servicepath,
        }

    async def query_entity(
        self,
        entity_id: str,
        *,
        type_: str,
        attrs: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        last_n: int | None = None,
        limit: int | None = None,
        offset: int | None = None,
        aggr_method: str | None = None,
        aggr_period: str | None = None,
    ) -> dict[str, Any] | None:
        params: dict[str, Any] = {"type": type_}
        if attrs:
            params["attrs"] = attrs
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        if last_n is not None:
            params["lastN"] = last_n
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if aggr_method is not None:
            params["aggrMethod"] = aggr_method
        if aggr_period is not None:
            params["aggrPeriod"] = aggr_period

        r = await self._client.get(
            f"{self._base}/v2/entities/{entity_id}",
            headers=self._headers,
            params=params,
        )
        if r.status_code == 404:
            return None
        if r.status_code == 200:
            return r.json()
        raise QuantumLeapError(f"query_entity {r.status_code}: {r.text}")

    async def count_entity(
        self,
        entity_id: str,
        *,
        type_: str,
        attrs: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> int | None:
        """Return the total row count for the given window via
        QuantumLeap's ``options=count`` mode.

        Reads the ``Fiware-Total-Count`` response header. Returns
        ``None`` if the entity is unknown (404) or the header is
        absent.
        """
        params: dict[str, Any] = {"type": type_, "options": "count", "limit": 1}
        if attrs:
            params["attrs"] = attrs
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date

        r = await self._client.get(
            f"{self._base}/v2/entities/{entity_id}",
            headers=self._headers,
            params=params,
        )
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise QuantumLeapError(f"count_entity {r.status_code}: {r.text}")
        total = r.headers.get("Fiware-Total-Count") or r.headers.get(
            "fiware-total-count"
        )
        try:
            return int(total) if total is not None else None
        except (TypeError, ValueError):
            return None
