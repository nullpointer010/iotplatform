"""Live ingest simulator (ticket 0019b).

For every registered device, continuously publishes realistic
measurements through the device's declared protocol:

- ``mqtt`` → real ``paho.publish`` to the platform broker; the
  bridge consumes it and runs the canonical writer.
- ``http`` → real ``POST /api/v1/devices/{id}/telemetry`` with a
  per-device ``X-Device-Key`` (auto-issued on first need).
- anything else (``lorawan``, ``plc``, ``modbus``, ``coap`` …) →
  forced to ``deviceState="maintenance"`` once. We don't have an
  ingestion adapter for those yet.

Off by default in `Settings`. Enabled in compose so `make up` shows
live data without any extra command.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import secrets
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import paho.mqtt.client as mqtt
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.models_ingest_keys import DeviceIngestKey
from app.mqtt_bridge import MqttBridge
from app.ngsi import from_ngsi
from app.orion import OrionClient

log = logging.getLogger("app.simulator")

# Per-attribute clamp + random-walk step. Mirrors `add_test_data.py`.
_RANGES: dict[str, tuple[float, float, float]] = {
    "temperature": (18.0, 30.0, 0.4),
    "humidity": (30.0, 90.0, 1.5),
    "windSpeed": (0.0, 12.0, 0.6),
    "rainfall": (0.0, 4.0, 0.2),
    "pressure": (1.0, 5.0, 0.1),
    "soilMoisture": (10.0, 60.0, 1.0),
    "luminosity": (0.0, 100000.0, 5000.0),
}

# Default attrs to publish when a device declares no `controlledProperty`.
_DEFAULT_ATTRS = ("temperature", "humidity")

# URNs of demo devices created by an earlier version of this module.
# Kept around so `make up` after an upgrade cleans them up.
_LEGACY_DEMO_NS = uuid.UUID("00000000-0000-0000-0000-0000000051ed")
_LEGACY_DEMO_SLUGS = (
    "demo-mqtt-1",
    "demo-mqtt-2",
    "demo-mqtt-3",
    "demo-http-1",
    "demo-http-2",
)


class LiveSimulator:
    """Background task: pump realistic telemetry for every device."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._orion: Optional[OrionClient] = None
        self._sessionmaker: Optional[async_sessionmaker] = None
        self._bridge: Optional[MqttBridge] = None
        self._mqtt: Optional[mqtt.Client] = None
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        # (device_urn, attr) -> current simulated value
        self._values: dict[tuple[str, str], float] = {}
        # device_urn -> cleartext ingest key (HTTP devices)
        self._http_keys: dict[str, str] = {}
        # device_urn -> True when an operator owns the key (skip).
        self._http_skip: dict[str, bool] = {}
        # device_urn already PATCHed to deviceState=maintenance (one-shot).
        self._maintenance_done: set[str] = set()
        self._mqtt_lock = threading.Lock()

    # ─── lifecycle ─────────────────────────────────────────────────

    async def start(
        self,
        loop: asyncio.AbstractEventLoop,
        orion: OrionClient,
        sessionmaker: async_sessionmaker,
        bridge: Optional[MqttBridge] = None,
    ) -> None:
        self._loop = loop
        self._orion = orion
        self._sessionmaker = sessionmaker
        self._bridge = bridge

        # Connect MQTT publisher (separate paho client from the bridge).
        c = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="iot-api-simulator",
            clean_session=True,
        )
        c.username_pw_set(self._settings.mqtt_username, self._settings.mqtt_password)
        c.reconnect_delay_set(min_delay=1, max_delay=30)
        try:
            c.connect_async(
                self._settings.mqtt_host,
                self._settings.mqtt_port,
                keepalive=30,
            )
            c.loop_start()
        except Exception as exc:  # pragma: no cover
            log.warning("simulator MQTT connect failed: %s", exc)
        self._mqtt = c

        self._task = asyncio.create_task(self._run(), name="simulator")
        log.info(
            "simulator started (interval=%ss)",
            self._settings.simulator_interval_seconds,
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
            self._task = None
        if self._mqtt is not None:
            try:
                self._mqtt.disconnect()
                self._mqtt.loop_stop()
            except Exception:  # pragma: no cover
                pass
            self._mqtt = None

    # ─── main loop ─────────────────────────────────────────────────

    async def _run(self) -> None:
        # Give the rest of the stack a moment: uvicorn binding,
        # MQTT bridge subscribing, Orion ready.
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=5)
            return
        except asyncio.TimeoutError:
            pass

        try:
            await self._cleanup_legacy_demo_devices()
        except Exception:
            log.exception("simulator legacy cleanup failed")

        async with httpx.AsyncClient(timeout=10.0) as http:
            interval = max(1, self._settings.simulator_interval_seconds)
            while not self._stop.is_set():
                try:
                    await self._tick(http)
                except Exception:
                    log.exception("simulator tick failed")
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass

    # ─── one-time cleanup of older demo entities ──────────────────

    async def _cleanup_legacy_demo_devices(self) -> None:
        assert self._orion is not None
        for slug in _LEGACY_DEMO_SLUGS:
            urn = f"urn:ngsi-ld:Device:{uuid.uuid5(_LEGACY_DEMO_NS, slug)}"
            try:
                deleted = await self._orion.delete_entity(urn)
                if deleted:
                    log.info("simulator removed legacy demo %s", urn)
            except Exception:
                log.exception("simulator delete legacy %s failed", urn)

    # ─── tick: walk every device ──────────────────────────────────

    async def _tick(self, http: httpx.AsyncClient) -> None:
        assert self._orion is not None
        offset = 0
        page = 1000
        while not self._stop.is_set():
            entities = await self._orion.list_entities(limit=page, offset=offset)
            if not entities:
                break
            for raw in entities:
                d = from_ngsi(raw)
                proto = d.get("supportedProtocol")
                if proto == "mqtt":
                    self._publish_mqtt(d)
                elif proto == "http":
                    await self._publish_http(http, d)
                else:
                    await self._ensure_maintenance(d)
            if len(entities) < page:
                break
            offset += page

    def _attrs_for(self, d: dict[str, Any]) -> list[str]:
        cps = d.get("controlledProperty") or []
        out = [a for a in cps if isinstance(a, str)]
        return out or list(_DEFAULT_ATTRS)

    def _next_value(self, device_urn: str, attr: str) -> float:
        rng = _RANGES.get(attr)
        if rng is None:
            return round(random.uniform(0, 100), 2)
        lo, hi, step = rng
        key = (device_urn, attr)
        cur = self._values.get(key)
        if cur is None:
            cur = random.uniform(lo + (hi - lo) * 0.3, lo + (hi - lo) * 0.7)
        else:
            cur += random.uniform(-step, step)
            cur = max(lo, min(hi, cur))
        self._values[key] = cur
        return round(cur, 2)

    # ─── MQTT path ─────────────────────────────────────────────────

    def _publish_mqtt(self, d: dict[str, Any]) -> None:
        if self._mqtt is None or not self._mqtt.is_connected():
            return
        root = d.get("mqttTopicRoot")
        if not isinstance(root, str) or not root:
            return
        root = root.rstrip("/")
        for attr in self._attrs_for(d):
            value = self._next_value(d["id"], attr)
            payload = json.dumps({"value": value})
            with self._mqtt_lock:
                self._mqtt.publish(f"{root}/{attr}", payload, qos=0, retain=False)

    # ─── HTTP path ─────────────────────────────────────────────────

    async def _ensure_http_key(self, device_urn: str) -> Optional[str]:
        if self._http_skip.get(device_urn):
            return None
        cached = self._http_keys.get(device_urn)
        if cached is not None:
            return cached
        assert self._sessionmaker is not None
        duuid = uuid.UUID(device_urn.rsplit(":", 1)[-1])
        prefix_secret = secrets.token_hex(4)
        body = secrets.token_hex(16)
        cleartext = f"dik_{prefix_secret}_{body}"
        prefix = f"dik_{prefix_secret}"
        khash = hashlib.sha256(cleartext.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)
        async with self._sessionmaker() as s:
            existing = await s.get(DeviceIngestKey, duuid)
            if existing is None:
                s.add(
                    DeviceIngestKey(
                        device_id=duuid,
                        key_hash=khash,
                        prefix=prefix,
                        created_at=now,
                        created_by="simulator",
                    )
                )
            elif existing.created_by == "simulator":
                # Our row, but we don't have the cleartext (e.g. after
                # a process restart). Rotate.
                existing.key_hash = khash
                existing.prefix = prefix
                existing.created_at = now
            else:
                # Operator owns this key. Don't touch it.
                self._http_skip[device_urn] = True
                log.info(
                    "simulator skipping %s: operator-owned ingest key",
                    device_urn,
                )
                return None
            await s.commit()
        self._http_keys[device_urn] = cleartext
        return cleartext

    async def _publish_http(
        self, http: httpx.AsyncClient, d: dict[str, Any]
    ) -> None:
        attrs = self._attrs_for(d)
        if not attrs:
            return
        try:
            key = await self._ensure_http_key(d["id"])
        except Exception:
            log.exception("simulator: ensure key failed for %s", d["id"])
            return
        if key is None:
            return
        device_uuid = d["id"].rsplit(":", 1)[-1]
        url = (
            f"{self._settings.simulator_api_base_url.rstrip('/')}"
            f"{self._settings.api_prefix}/devices/{device_uuid}/telemetry"
        )
        measurements = [
            {"controlledProperty": a, "value": self._next_value(d["id"], a)}
            for a in attrs
        ]
        body: dict[str, Any]
        if len(measurements) == 1:
            body = measurements[0]
        else:
            body = {"measurements": measurements}
        try:
            r = await http.post(
                url, headers={"X-Device-Key": key}, json=body
            )
            if r.status_code == 401:
                # Stale cached key (e.g. table was wiped by tests).
                self._http_keys.pop(d["id"], None)
                return
            if r.status_code not in (200, 202):
                log.warning(
                    "simulator http %s -> %s %s",
                    url, r.status_code, r.text[:200],
                )
        except httpx.HTTPError as exc:
            log.warning("simulator http error %s: %s", url, exc)

    # ─── non-live protocols → maintenance ─────────────────────────

    async def _ensure_maintenance(self, d: dict[str, Any]) -> None:
        urn = d["id"]
        if urn in self._maintenance_done:
            return
        if d.get("deviceState") == "maintenance":
            self._maintenance_done.add(urn)
            return
        assert self._orion is not None
        try:
            ok = await self._orion.patch_entity(
                urn, {"deviceState": {"type": "Text", "value": "maintenance"}}
            )
            if ok:
                self._maintenance_done.add(urn)
                log.info(
                    "simulator → %s set to maintenance (protocol=%s)",
                    urn, d.get("supportedProtocol"),
                )
        except Exception:
            log.exception("simulator maintenance PATCH failed for %s", urn)
