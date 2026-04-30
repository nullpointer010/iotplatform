from __future__ import annotations

import os
import time
from collections.abc import Iterator

import httpx
import psycopg
import pytest


API_BASE = os.environ.get("API_INTERNAL_URL", "http://iot-api:8000")
ORION_BASE = os.environ.get("ORION_URL", "http://orion:1026")
QL_BASE = os.environ.get("QUANTUMLEAP_URL", "http://quantumleap:8668")
KEYCLOAK_BASE = os.environ.get("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "iot-platform")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "iot-web")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "dev-iot-web-secret")
FIWARE_SERVICE = os.environ.get("FIWARE_SERVICE", "iot")
FIWARE_SERVICEPATH = os.environ.get("FIWARE_SERVICEPATH", "/")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://iot_user:iot_password@postgres:5432/iot_database",
)


# Realm seed users and the password schema documented in
# platform/config/keycloak/realm-iot.json (`change-me-<role>`).
SEED_USERS: dict[str, str] = {
    "viewer": "change-me-viewer",
    "operator": "change-me-operator",
    "manager": "change-me-manager",
    "admin": "change-me-admin",
}


def _fetch_token(username: str, password: str) -> str:
    url = f"{KEYCLOAK_BASE}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET,
        "username": username,
        "password": password,
        "scope": "openid",
    }
    # Retry briefly: Keycloak may not be ready when the first test runs.
    last_err: Exception | None = None
    for _ in range(20):
        try:
            r = httpx.post(url, data=data, timeout=5.0)
            if r.status_code == 200:
                return r.json()["access_token"]
            last_err = AssertionError(f"{r.status_code} {r.text}")
        except httpx.HTTPError as exc:
            last_err = exc
        time.sleep(0.5)
    raise RuntimeError(f"could not fetch token for {username}: {last_err}")


@pytest.fixture(scope="session")
def tokens() -> dict[str, str]:
    return {role: _fetch_token(role, pw) for role, pw in SEED_USERS.items()}


def _sync_pg_dsn() -> str:
    # Strip SQLAlchemy driver suffix; psycopg accepts the PostgreSQL URI.
    return DATABASE_URL.replace("+asyncpg", "").replace("postgresql+psycopg2://", "postgresql://")


_FIWARE_HEADERS = {
    "Fiware-Service": FIWARE_SERVICE,
    "Fiware-ServicePath": FIWARE_SERVICEPATH,
}


@pytest.fixture(scope="session")
def api(tokens: dict[str, str]) -> Iterator[httpx.Client]:
    headers = {"Authorization": f"Bearer {tokens['admin']}"}
    with httpx.Client(base_url=API_BASE, timeout=30.0, headers=headers) as c:
        yield c


@pytest.fixture(scope="session")
def orion() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=ORION_BASE, timeout=10.0, headers=_FIWARE_HEADERS) as c:
        yield c


@pytest.fixture(scope="session")
def ql() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=QL_BASE, timeout=10.0, headers=_FIWARE_HEADERS) as c:
        yield c


@pytest.fixture
def created_ids(orion: httpx.Client) -> Iterator[list[str]]:
    """Tests append entity ids here; teardown deletes via Orion.

    Works for both Device and DeviceMeasurement entity ids.
    """
    ids: list[str] = []
    yield ids
    for eid in ids:
        try:
            orion.delete(f"/v2/entities/{eid}")
        except httpx.HTTPError:
            pass


@pytest.fixture(autouse=True)
def pg_clean() -> Iterator[None]:
    """TRUNCATE maintenance tables before each test for isolation.

    Cheap on a near-empty database; keeps tests order-independent.
    """
    with psycopg.connect(_sync_pg_dsn(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE device_placements, site_floorplans, device_manuals, "
                "maintenance_log, maintenance_operation_types "
                "RESTART IDENTITY CASCADE"
            )
    yield


def push_measurement(
    orion: httpx.Client,
    *,
    device_uuid: str,
    controlled_property: str,
    num_value: float,
    date_observed: str,
    unit_code: str | None = None,
) -> str:
    """Create or update a DeviceMeasurement entity in Orion.

    Returns the measurement entity URN. Caller is responsible for cleanup
    (typically by appending the URN to ``created_ids``).
    """
    suffix = controlled_property[:1].upper() + controlled_property[1:]
    entity_id = f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:{suffix}"
    attrs: dict = {
        "refDevice": {"type": "Text", "value": f"urn:ngsi-ld:Device:{device_uuid}"},
        "controlledProperty": {"type": "Text", "value": controlled_property},
        "numValue": {"type": "Number", "value": num_value},
        "dateObserved": {"type": "DateTime", "value": date_observed},
    }
    if unit_code is not None:
        attrs["unitCode"] = {"type": "Text", "value": unit_code}

    # Try create first; if it exists, fall through to update.
    create = orion.post(
        "/v2/entities",
        json={"id": entity_id, "type": "DeviceMeasurement", **attrs},
    )
    if create.status_code == 422 and "Already Exists" in create.text:
        # Append-or-update existing attrs.
        upd = orion.post(f"/v2/entities/{entity_id}/attrs", json=attrs)
        upd.raise_for_status()
    else:
        create.raise_for_status()
    return entity_id


def wait_for_ql(
    ql: httpx.Client,
    entity_id: str,
    *,
    expected_count: int,
    timeout_s: float = 8.0,
) -> dict:
    """Poll QuantumLeap until ``entity_id`` has at least ``expected_count``
    entries, or raise ``TimeoutError``."""
    deadline = time.monotonic() + timeout_s
    last: dict | None = None
    while time.monotonic() < deadline:
        r = ql.get(
            f"/v2/entities/{entity_id}",
            params={"type": "DeviceMeasurement", "attrs": "numValue,unitCode"},
        )
        if r.status_code == 200:
            last = r.json()
            idx = last.get("index", []) or []
            if len(idx) >= expected_count:
                return last
        time.sleep(0.25)
    raise TimeoutError(
        f"QL did not index {expected_count} entries for {entity_id} in {timeout_s}s "
        f"(last response: {last})"
    )
