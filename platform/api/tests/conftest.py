from __future__ import annotations

import os
from collections.abc import Iterator

import httpx
import pytest


API_BASE = os.environ.get("API_INTERNAL_URL", "http://iot-api:8000")
ORION_BASE = os.environ.get("ORION_URL", "http://orion:1026")
FIWARE_SERVICE = os.environ.get("FIWARE_SERVICE", "iot")
FIWARE_SERVICEPATH = os.environ.get("FIWARE_SERVICEPATH", "/")

_ORION_HEADERS = {
    "Fiware-Service": FIWARE_SERVICE,
    "Fiware-ServicePath": FIWARE_SERVICEPATH,
}


@pytest.fixture(scope="session")
def api() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=API_BASE, timeout=10.0) as c:
        yield c


@pytest.fixture(scope="session")
def orion() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=ORION_BASE, timeout=10.0, headers=_ORION_HEADERS) as c:
        yield c


@pytest.fixture
def created_ids(orion: httpx.Client) -> Iterator[list[str]]:
    """Tests append entity ids here; teardown deletes via Orion."""
    ids: list[str] = []
    yield ids
    for eid in ids:
        try:
            orion.delete(f"/v2/entities/{eid}")
        except httpx.HTTPError:
            pass
