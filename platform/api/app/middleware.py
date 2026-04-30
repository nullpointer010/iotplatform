"""ASGI middleware that attaches a stable request id to every request.

Reads ``X-Request-ID`` from the incoming request when present and well
formed; otherwise mints a 12-hex id. The value is stored on
``request.state.request_id`` and echoed back as the ``X-Request-ID``
response header so clients and log lines can be correlated.
"""

from __future__ import annotations

import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_VALID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id")
        rid = incoming if incoming and _VALID.match(incoming) else uuid.uuid4().hex[:12]
        request.state.request_id = rid
        try:
            response: Response = await call_next(request)
        except Exception:
            # Re-raise so the registered Exception handler can build the
            # JSON envelope with the same rid (still on request.state).
            raise
        response.headers["X-Request-ID"] = rid
        return response
