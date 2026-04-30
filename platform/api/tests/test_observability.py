"""In-process tests for global exception handling and request-id middleware.

Unlike the rest of the suite (which talks to the live ``iot-api``
container over HTTP), these run an in-process FastAPI app via
``TestClient`` so they can attach a ``__boom`` route that always raises
and observe both the HTTP envelope and the captured log records.
"""

from __future__ import annotations

import logging
import re

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()

    @app.get("/__boom")
    async def _boom() -> None:  # pragma: no cover - body unreachable
        raise RuntimeError("boom-from-test")

    # ``TestClient`` enters the lifespan; we do not need DB / Orion for
    # this test, so we just bypass lifespan by NOT using it as a context
    # manager. Direct construction is supported and skips startup hooks.
    return TestClient(app, raise_server_exceptions=False)


def test_unhandled_exception_returns_envelope_and_logs(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.errors"):
        r = client.get("/__boom", headers={"X-Request-ID": "testrid123"})

    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error", "request_id": "testrid123"}
    assert r.headers["X-Request-ID"] == "testrid123"

    records = [rec for rec in caplog.records if rec.name == "app.errors"]
    assert len(records) == 1, [r.getMessage() for r in records]
    rec = records[0]
    assert rec.levelno == logging.ERROR
    assert rec.exc_info is not None
    assert rec.exc_info[0] is RuntimeError
    assert "rid=testrid123" in rec.getMessage()
    assert "/__boom" in rec.getMessage()


def test_request_id_generated_when_absent(client: TestClient) -> None:
    r = client.get("/__boom")
    assert r.status_code == 500
    rid = r.headers["X-Request-ID"]
    assert re.fullmatch(r"[a-f0-9]{12}", rid), rid
    assert r.json()["request_id"] == rid


def test_request_id_present_on_success(client: TestClient) -> None:
    # Health route exists and does not require DB/Orion.
    r = client.get("/healthz")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", r.headers["X-Request-ID"])


def test_malformed_incoming_request_id_is_replaced(client: TestClient) -> None:
    # Spaces and slashes are not in the allow-list; middleware must mint a fresh id.
    r = client.get("/__boom", headers={"X-Request-ID": "bad id with spaces"})
    rid = r.headers["X-Request-ID"]
    assert rid != "bad id with spaces"
    assert re.fullmatch(r"[a-f0-9]{12}", rid)
