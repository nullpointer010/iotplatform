"""Live ingest simulator (ticket 0019b).

Auto-creates a small fleet of demo devices in Orion and continuously
publishes realistic measurements through both real ingestion paths
(MQTT broker + HTTP /telemetry endpoint), so a freshly-started stack
shows live data in the UI without any extra command.

Off by default. Enabled in compose via ``SIMULATOR_ENABLED=true``.
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
from app.ngsi import from_ngsi, to_ngsi
from app.orion import DuplicateEntity, OrionClient

log = logging.getLogger("app.simulator")

# Stable namespace for demo device URNs (UUIDv5).
_DEMO_NS = uuid.UUID("00000000-0000-0000-0000-0000000051ed")
_DEMO_NAME_PREFIX = "[demo] "

# Per-attribute clamp + random-walk step.
_RANGES: dict[str, tuple[float, float, float]] = {
    "temperature": (18.0, 30.0, 0.4),
    "humidity": (30.0, 90.0, 1.5),
}


def _demo_urn(slug: str) -> str:
    return f"urn:ngsi-ld:Device:{uuid.uuid5(_DEMO_NS, slug)}"


def _is_demo(device_urn: str) -> bool:
    """Check whether a URN belongs to our demo namespace.

    We re-derive each demo URN once at startup and store the set;
    this helper only exists for documentation / readability.
    """
    return device_urn.startswith("urn:ngsi-ld:Device:")


# Layout of the demo fleet. Order matters: the slug feeds UUIDv5.
_DEMO_LAYOUT: list[dict[str, Any]] = [
    {"slug": "demo-mqtt-1", "proto": "mqtt", "topic": "demo/sensor-1"},
    {"slug": "demo-mqtt-2", "proto": "mqtt", "topic": "demo/sensor-2"},
    {"slug": "demo-mqtt-3", "proto": "mqtt", "topic": "demo/sensor-3"},
    {"slug": "demo-http-1", "proto": "http", "topic": None},
    {"slug": "demo-http-2", "proto": "http", "topic": None},
]


def _demo_device_payload(idx: int, spec: dict[str, Any]) -> dict[str, Any]:
    proto = spec["proto"]
    label = f"{_DEMO_NAME_PREFIX}{proto.upper()} sensor {idx}"
    payload: dict[str, Any] = {
        "id": _demo_urn(spec["slug"]),
        "name": label,
        "category": "sensor",
        "supportedProtocol": proto,
        "deviceState": "active",
        "controlledProperty": ["temperature", "humidity"],
        "manufacturerName": "CropDataSpace Demo",
        "modelName": "demo-sim-1",
        "serialNumber": f"DEMO-{idx:03d}",
        "owner": ["simulator"],
    }
    if proto == "mqtt":
        payload["mqttTopicRoot"] = spec["topic"]
        payload["mqttClientId"] = spec["slug"]
        payload["dataTypes"] = {
            "temperature": "Number",
            "humidity": "Number",
        }
    return payload


class LiveSimulator:
    """Background task: ensure demo devices, then pump telemetry."""

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
        # device_urn -> cleartext ingest key (for HTTP demo devices)
        self._http_keys: dict[str, str] = {}
        # device_urn -> True/False (skip if operator owns the key)
        self._http_skip: dict[str, bool] = {}
        # The set of demo URNs we own.
        self._demo_urns: set[str] = {_demo_urn(s["slug"]) for s in _DEMO_LAYOUT}
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

        # Connect MQTT publisher (separate client from the bridge).
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
        log.info("simulator started (interval=%ss)",
                 self._settings.simulator_interval_seconds)

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
            await self._bootstrap_devices()
        except Exception:
            log.exception("simulator bootstrap failed; will retry next tick")

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

    # ─── bootstrap ─────────────────────────────────────────────────

    async def _bootstrap_devices(self) -> None:
        assert self._orion is not None
        for idx, spec in enumerate(_DEMO_LAYOUT, start=1):
            payload = _demo_device_payload(idx, spec)
            entity = to_ngsi(payload)
            try:
                await self._orion.create_entity(entity)
                log.info("simulator created %s (%s)", payload["name"], spec["proto"])
            except DuplicateEntity:
                # Re-PATCH the protocol-specific attrs to heal any
                # schema drift across simulator versions.
                heal = {k: v for k, v in entity.items() if k not in ("id", "type")}
                await self._orion.patch_entity(payload["id"], heal)
        # Make the MQTT bridge pick up our new MQTT-protocol devices.
        if self._bridge is not None:
            try:
                await self._bridge.refresh()
            except Exception:
                log.exception("simulator bridge refresh failed")

    # ─── tick ──────────────────────────────────────────────────────

    async def _tick(self, http: httpx.AsyncClient) -> None:
        assert self._orion is not None
        # Re-fetch each demo device fresh: protocol/topic can change.
        for urn in self._demo_urns:
            ent = await self._orion.get_entity(urn)
            if ent is None:
                # Was deleted (e.g. by a test). Re-create on next bootstrap.
                continue
            d = from_ngsi(ent)
            proto = d.get("supportedProtocol")
            if proto == "mqtt":
                self._publish_mqtt(d)
            elif proto == "http":
                await self._publish_http(http, d)

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
        for attr in d.get("controlledProperty") or []:
            if not isinstance(attr, str):
                continue
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
        attrs = [
            a for a in (d.get("controlledProperty") or []) if isinstance(a, str)
        ]
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
