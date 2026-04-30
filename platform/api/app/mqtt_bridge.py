"""In-process MQTT → Orion bridge (ticket 0018).

Connects to the platform Mosquitto broker, subscribes to
``<mqttTopicRoot>/+`` for every MQTT-enabled device, and forwards each
received message as an attribute update on ``Device:<id>`` via
``OrionClient.patch_entity``. All blocking paho work runs on the paho
thread; Orion calls hop back to the asyncio loop via
``run_coroutine_threadsafe``.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional

import paho.mqtt.client as mqtt

from app.config import Settings
from app.mqtt_payload import (
    PayloadError,
    infer_ngsi_type,
    parse_payload,
    validate_against_dataTypes,
)
from app.ngsi import from_ngsi
from app.orion import OrionClient, OrionError

log = logging.getLogger("app.mqtt")

_INFLIGHT_CAP = 256


class MqttBridge:
    """Subscribe to per-device topics and forward messages to Orion.

    The bridge is designed to be safe to construct unconditionally: if
    `start()` fails to reach the broker, `paho` keeps reconnecting in
    the background; nothing else in the API breaks.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._orion: Optional[OrionClient] = None
        self._client: Optional[mqtt.Client] = None
        # device_id (URN) → mqttTopicRoot, with the cached dataTypes.
        self._subs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._inflight = 0
        # Stats (read by GET /system/mqtt).
        self.connected = False
        self.last_message_at: Optional[datetime] = None
        self.dropped_invalid = 0
        self._refresh_lock: Optional[asyncio.Lock] = None

    # ─── lifecycle ─────────────────────────────────────────────────

    async def start(
        self, loop: asyncio.AbstractEventLoop, orion: OrionClient
    ) -> None:
        self._loop = loop
        self._orion = orion
        self._refresh_lock = asyncio.Lock()
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="iot-api-bridge",
            clean_session=True,
        )
        client.username_pw_set(self._settings.mqtt_username, self._settings.mqtt_password)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client = client
        try:
            client.connect_async(self._settings.mqtt_host, self._settings.mqtt_port, keepalive=30)
            client.loop_start()
        except Exception as exc:  # pragma: no cover — paho rarely raises here
            log.warning("MQTT bridge initial connect failed: %s", exc)
        # Build initial subscription set from Orion.
        await self.refresh()

    async def stop(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
                self._client.loop_stop()
            except Exception as exc:  # pragma: no cover
                log.warning("MQTT bridge stop error: %s", exc)
            self._client = None

    # ─── public API ────────────────────────────────────────────────

    async def refresh(self) -> None:
        """Reload subscriptions from Orion. Safe to call concurrently."""
        if self._client is None or self._orion is None or self._refresh_lock is None:
            return
        async with self._refresh_lock:
            try:
                desired = await self._desired_subs()
            except OrionError as exc:
                log.warning("MQTT bridge refresh: orion error: %s", exc)
                return
            with self._lock:
                old_topics = {info["root"] + "/+" for info in self._subs.values()}
                new_topics = {info["root"] + "/+" for info in desired.values()}
                for topic in old_topics - new_topics:
                    try:
                        self._client.unsubscribe(topic)
                    except Exception as exc:  # pragma: no cover
                        log.warning("unsubscribe %s failed: %s", topic, exc)
                for topic in new_topics - old_topics:
                    try:
                        self._client.subscribe(topic, qos=0)
                    except Exception as exc:  # pragma: no cover
                        log.warning("subscribe %s failed: %s", topic, exc)
                self._subs = desired

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "connected": self.connected,
                "subscribed_topics": len(self._subs),
                "last_message_at": (
                    self.last_message_at.isoformat() if self.last_message_at else None
                ),
                "dropped_invalid": self.dropped_invalid,
            }

    # ─── helpers ───────────────────────────────────────────────────

    async def _desired_subs(self) -> dict[str, dict[str, Any]]:
        assert self._orion is not None
        out: dict[str, dict[str, Any]] = {}
        offset = 0
        page = 1000
        while True:
            entities = await self._orion.list_entities(limit=page, offset=offset)
            if not entities:
                break
            for raw in entities:
                d = from_ngsi(raw)
                if d.get("supportedProtocol") != "mqtt":
                    continue
                root = d.get("mqttTopicRoot")
                if not isinstance(root, str) or not root:
                    continue
                root = root.rstrip("/")
                out[d["id"]] = {
                    "root": root,
                    "dataTypes": d.get("dataTypes") or {},
                }
            if len(entities) < page:
                break
            offset += page
        return out

    def _device_for_topic(self, topic: str) -> Optional[tuple[str, dict[str, Any], str]]:
        """Return ``(device_id, dataTypes, attr)`` for an inbound topic."""
        # topic shape: <root>/<attr>; we keep the lookup linear (small N).
        with self._lock:
            for device_id, info in self._subs.items():
                root = info["root"]
                if topic.startswith(root + "/"):
                    attr = topic[len(root) + 1 :]
                    if "/" in attr or not attr:
                        return None
                    return device_id, info["dataTypes"], attr
        return None

    # ─── paho callbacks (run on the paho thread) ───────────────────

    def _on_connect(self, client: mqtt.Client, userdata, flags, reason_code, properties=None) -> None:
        ok = getattr(reason_code, "is_failure", False) is False
        with self._lock:
            self.connected = bool(ok)
            subs = list(self._subs.values())
        if ok:
            log.info("MQTT bridge connected to %s:%s", self._settings.mqtt_host, self._settings.mqtt_port)
            for info in subs:
                try:
                    client.subscribe(info["root"] + "/+", qos=0)
                except Exception as exc:  # pragma: no cover
                    log.warning("resubscribe %s failed: %s", info["root"], exc)
        else:
            log.warning("MQTT bridge connect failed: %s", reason_code)

    def _on_disconnect(self, client: mqtt.Client, userdata, *args, **kwargs) -> None:
        with self._lock:
            self.connected = False
        log.warning("MQTT bridge disconnected; paho will reconnect")

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        # Hard cap on in-flight forwards — protect the asyncio loop.
        with self._lock:
            if self._inflight >= _INFLIGHT_CAP:
                self.dropped_invalid += 1
                log.warning("MQTT inflight cap reached; dropping topic=%s", msg.topic)
                return
            self._inflight += 1
        try:
            self._handle_message(msg)
        finally:
            with self._lock:
                self._inflight -= 1

    def _handle_message(self, msg: mqtt.MQTTMessage) -> None:
        try:
            value = parse_payload(msg.payload, self._settings.mqtt_max_payload_bytes)
        except PayloadError as exc:
            self._drop("bad-payload", msg.topic, str(exc))
            return
        match = self._device_for_topic(msg.topic)
        if match is None:
            self._drop("unknown-topic", msg.topic, "no device for topic")
            return
        device_id, data_types, attr = match
        try:
            ngsi_type, ngsi_value = infer_ngsi_type(value)
        except PayloadError as exc:
            self._drop("bad-value", msg.topic, str(exc))
            return
        if not validate_against_dataTypes(attr, ngsi_type, ngsi_value, data_types):
            self._drop(
                "dataTypes-mismatch",
                msg.topic,
                f"attr={attr} got={ngsi_type} expected={data_types.get(attr)}",
            )
            return
        with self._lock:
            self.last_message_at = datetime.now(timezone.utc)
        # Schedule the Orion patch on the asyncio loop.
        if self._loop is None or self._orion is None:
            return
        coro = self._forward(device_id, attr, ngsi_type, ngsi_value)
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except RuntimeError as exc:  # pragma: no cover
            log.warning("MQTT forward schedule failed: %s", exc)

    async def _forward(
        self, device_id: str, attr: str, ngsi_type: str, value: Any
    ) -> None:
        assert self._orion is not None
        attrs = {attr: {"type": ngsi_type, "value": value}}
        try:
            await self._orion.patch_entity(device_id, attrs)
        except OrionError as exc:
            log.warning("MQTT forward orion error device=%s: %s", device_id, exc)

    def _drop(self, reason: str, topic: str, detail: str) -> None:
        with self._lock:
            self.dropped_invalid += 1
        log.warning("MQTT drop reason=%s topic=%s detail=%s", reason, topic, detail)
