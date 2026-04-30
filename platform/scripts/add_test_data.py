#!/usr/bin/env python3
"""Seed the IoT platform with realistic test data.

Wipes any previous seed batch (devices whose URN starts with
``urn:ngsi-ld:Device:seed-`` and operation types whose name starts with
``Seed: ``) before recreating ~50 devices, 8 operation types and ~150
maintenance log entries. For every sensor/weather-station device, three
days of synthetic measurements are pushed straight into Orion so the
QuantumLeap subscription indexes them in CrateDB.

Run against a stack started with ``make up``. Requires only the Python
standard library (uses ``urllib.request``).

Environment variables (all optional):

* ``IOT_API_URL``     default ``http://localhost``
* ``IOT_ORION_URL``   default ``http://localhost:1026``
* ``IOT_FIWARE_SERVICE``      default ``iot``
* ``IOT_FIWARE_SERVICEPATH``  default ``/``
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

API_URL = os.environ.get("IOT_API_URL", "http://localhost").rstrip("/")
ORION_URL = os.environ.get("IOT_ORION_URL", "http://localhost:1026").rstrip("/")
FIWARE_SERVICE = os.environ.get("IOT_FIWARE_SERVICE", "iot")
FIWARE_SERVICEPATH = os.environ.get("IOT_FIWARE_SERVICEPATH", "/")

SEED_NS = uuid.UUID("00000000-0000-0000-0000-0000000005ed")
SEED_DEVICE_NAME_PREFIX = "Seed Device "
SEED_OPTYPE_PREFIX = "Seed: "

random.seed(42)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


class HttpError(RuntimeError):
    def __init__(self, method: str, url: str, status: int, body: str) -> None:
        super().__init__(f"{method} {url} -> {status}: {body[:300]}")
        self.status = status
        self.body = body


def _request(
    method: str,
    url: str,
    *,
    json_body: object | None = None,
    headers: dict | None = None,
    expect: tuple[int, ...] = (200, 201, 204),
) -> tuple[int, str]:
    data = None
    h = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code in expect:
            return exc.code, body
        raise HttpError(method, url, exc.code, body)


def api_get(path: str) -> object:
    _, body = _request("GET", f"{API_URL}{path}")
    return json.loads(body) if body else None


def api_post(path: str, body: object) -> object:
    status, text = _request("POST", f"{API_URL}{path}", json_body=body)
    return json.loads(text) if text else {"_status": status}


def api_delete(path: str) -> int:
    status, _ = _request("DELETE", f"{API_URL}{path}", expect=(204, 404))
    return status


def orion_post(path: str, body: object, expect=(200, 201, 204, 422)) -> tuple[int, str]:
    return _request(
        "POST",
        f"{ORION_URL}{path}",
        json_body=body,
        headers={
            "Fiware-Service": FIWARE_SERVICE,
            "Fiware-ServicePath": FIWARE_SERVICEPATH,
        },
        expect=expect,
    )


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

SITES = [
    {"site_area": "Finca Norte - Invernadero 1", "latitude": 40.4501, "longitude": -3.7202, "city": "Madrid"},
    {"site_area": "Finca Norte - Invernadero 2", "latitude": 40.4523, "longitude": -3.7188, "city": "Madrid"},
    {"site_area": "Finca Sur - Almacén Principal", "latitude": 39.4699, "longitude": -0.3763, "city": "Valencia"},
    {"site_area": "Finca Sur - Cabezal de Riego", "latitude": 39.4670, "longitude": -0.3781, "city": "Valencia"},
    {"site_area": "Finca Este - Sala Técnica", "latitude": 41.3851, "longitude": 2.1734, "city": "Barcelona"},
    {"site_area": "Finca Oeste - Pivote 1", "latitude": 37.3891, "longitude": -5.9845, "city": "Sevilla"},
    {"site_area": "Finca Oeste - Pivote 2", "latitude": 37.3905, "longitude": -5.9821, "city": "Sevilla"},
    {"site_area": "Estación Meteorológica Central", "latitude": 38.3452, "longitude": -0.4810, "city": "Alicante"},
]

OWNERS = ["Juan Pérez", "María García", "Carlos Ruiz", "Ana Sánchez", "Luis Fernández"]
MANUFACTURERS = ["Acme Sensors", "Siemens", "Bosch", "Libelium", "Davis Instruments"]
MODELS = ["S-100", "S-200X", "T-1000", "Vantage Pro", "Plug-Smart-3", "PLC-12-DC"]

OPERATION_TYPES = [
    ("Calibración", "Calibración periódica del sensor.", False),
    ("Reemplazo de batería", "Sustitución de batería primaria.", True),
    ("Limpieza", "Limpieza de carcasa y elementos sensibles.", False),
    ("Inspección visual", "Revisión general del estado físico.", False),
    ("Actualización de firmware", "Flash de la última versión de firmware.", False),
    ("Sustitución de sensor", "Cambio del módulo sensor.", True),
    ("Reparación", "Reparación tras incidencia o fallo detectado.", True),
    ("Configuración", "Reconfiguración de parámetros operativos.", False),
]

SENSOR_PROPERTIES = {
    "sensor": ["temperature", "humidity"],
    "weatherStation": ["temperature", "humidity", "windSpeed", "rainfall"],
    "endgun": ["pressure"],
    "iotStation": ["temperature", "humidity"],
}

UNITS = {
    "temperature": ("CEL", 18.0, 30.0),
    "humidity": ("P1", 30.0, 90.0),
    "windSpeed": ("MTS", 0.0, 12.0),
    "rainfall": ("MMT", 0.0, 4.0),
    "pressure": ("BAR", 1.0, 5.0),
}


# ---------------------------------------------------------------------------
# Build payloads
# ---------------------------------------------------------------------------


def _seed_device_id(n: int) -> str:
    """Stable URN derived from a fixed namespace so re-runs hit the same id."""
    return f"urn:ngsi-ld:Device:{uuid.uuid5(SEED_NS, f'device-{n}')}"


def _build_device(n: int) -> dict:
    site = random.choice(SITES)
    proto_pool = ["mqtt", "mqtt", "http", "plc", "lorawan", "modbus"]
    protocol = random.choice(proto_pool)
    category_pool = (
        ["sensor"] * 5
        + ["actuator", "gateway", "weatherStation", "endgun", "iotStation", "plc"]
    )
    if protocol == "plc":
        category = "plc"
    else:
        category = random.choice(category_pool)
    state = random.choices(
        ["active", "active", "active", "maintenance", "inactive"],
        k=1,
    )[0]
    name = f"Seed Device {n:03d} - {category}/{protocol}"
    payload: dict = {
        "id": _seed_device_id(n),
        "name": name,
        "category": category,
        "supportedProtocol": protocol,
        "deviceState": state,
        "manufacturerName": random.choice(MANUFACTURERS),
        "modelName": random.choice(MODELS),
        "firmwareVersion": f"{random.randint(1, 4)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        "serialNumber": f"SN-{n:05d}",
        "serialNumberType": random.choice(["MAC", "IMEI", "Internal"]),
        "owner": random.sample(OWNERS, k=random.randint(1, 2)),
        "ipAddress": [f"10.{random.randint(0, 50)}.{random.randint(0, 255)}.{random.randint(2, 254)}"],
        "dateInstalled": (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 720))).isoformat().replace("+00:00", "Z"),
        "location": {
            "latitude": site["latitude"] + random.uniform(-0.01, 0.01),
            "longitude": site["longitude"] + random.uniform(-0.01, 0.01),
            "site_area": site["site_area"],
        },
        "address": {"city": site["city"], "country": "ES"},
    }
    if category in SENSOR_PROPERTIES:
        payload["controlledProperty"] = SENSOR_PROPERTIES[category]
    if protocol == "mqtt":
        payload["mqttTopicRoot"] = f"crop/{site['city'].lower()}/dev{n:03d}"
        payload["mqttClientId"] = f"seed-{n:03d}"
        payload["mqttQos"] = random.choice([0, 1, 1, 2])
        payload["mqttSecurity"] = {"type": random.choice(["TLS", "none"])}
    elif protocol == "plc":
        payload["plcIpAddress"] = f"192.168.{random.randint(1, 5)}.{random.randint(2, 254)}"
        payload["plcPort"] = random.choice([502, 4840])
        payload["plcConnectionMethod"] = random.choice(["Modbus TCP", "OPC UA"])
        payload["plcReadFrequency"] = random.choice([5, 10, 30, 60])
        payload["plcTagsMapping"] = {
            f"DB1.DW{i*2}": f"tag_{i}" for i in range(random.randint(2, 5))
        }
        payload["plcCredentials"] = {"username": "operator", "password": "***"}
    elif protocol == "lorawan":
        payload["loraAppEui"] = uuid.uuid4().hex[:16].upper()
        payload["loraDevEui"] = uuid.uuid4().hex[:16].upper()
        payload["loraAppKey"] = uuid.uuid4().hex.upper()
        payload["loraNetworkServer"] = "tts.example.com"
        payload["loraPayloadDecoder"] = "decoder_v1"
    return payload


# ---------------------------------------------------------------------------
# Wipe
# ---------------------------------------------------------------------------


def wipe_seed_data() -> None:
    print("Wiping previous seed data ...")
    devices = api_get("/api/v1/devices?limit=1000") or []
    seed_devices = [
        d for d in devices if (d.get("name") or "").startswith(SEED_DEVICE_NAME_PREFIX)
    ]
    for d in seed_devices:
        api_delete(f"/api/v1/devices/{d['id']}")
    print(f"  removed {len(seed_devices)} seed devices")

    op_types = api_get("/api/v1/maintenance/operation-types") or []
    seed_ops = [o for o in op_types if o["name"].startswith(SEED_OPTYPE_PREFIX)]
    for o in seed_ops:
        api_delete(f"/api/v1/maintenance/operation-types/{o['id']}")
    print(f"  removed {len(seed_ops)} seed operation types")


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


def seed_operation_types() -> list[dict]:
    print("Creating operation types ...")
    out = []
    for name, desc, requires in OPERATION_TYPES:
        body = {
            "name": f"{SEED_OPTYPE_PREFIX}{name}",
            "description": desc,
            "requires_component": requires,
        }
        created = api_post("/api/v1/maintenance/operation-types", body)
        out.append(created)
    print(f"  created {len(out)} operation types")
    return out


def seed_devices(count: int = 50) -> list[dict]:
    print(f"Creating {count} devices ...")
    devices = []
    for n in range(1, count + 1):
        try:
            body = _build_device(n)
            d = api_post("/api/v1/devices", body)
            devices.append(d)
        except HttpError as exc:
            print(f"  ! device {n} skipped: {exc}", file=sys.stderr)
    print(f"  created {len(devices)} devices")
    return devices


def seed_maintenance(devices: list[dict], op_types: list[dict], count: int = 150) -> int:
    print(f"Creating ~{count} maintenance log entries ...")
    if not devices or not op_types:
        return 0
    created = 0
    now = datetime.now(timezone.utc)
    for _ in range(count):
        d = random.choice(devices)
        op = random.choice(op_types)
        start = now - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23))
        end = start + timedelta(minutes=random.randint(15, 240))
        body = {
            "operation_type_id": op["id"],
            "start_time": start.isoformat().replace("+00:00", "Z"),
            "end_time": end.isoformat().replace("+00:00", "Z"),
            "details_notes": random.choice(
                [
                    "Operación rutinaria.",
                    "Detectada anomalía menor, resuelta.",
                    "Sensor recalibrado tras desviación.",
                    "Cambio preventivo.",
                    None,
                ]
            ),
        }
        if op.get("requires_component"):
            body["component_path"] = random.choice(
                ["sensor_temperatura_1", "battery_pack", "valvula_solenoide", "antena"]
            )
        try:
            api_post(f"/api/v1/devices/{d['id']}/maintenance/log", body)
            created += 1
        except HttpError as exc:
            print(f"  ! log skipped: {exc}", file=sys.stderr)
    print(f"  created {created} maintenance entries")
    return created


def seed_telemetry(devices: list[dict], days: int = 3, per_day: int = 8) -> int:
    print(f"Pushing telemetry ({days} days × {per_day} pts) for sensor-like devices ...")
    pushed = 0
    now = datetime.now(timezone.utc).replace(microsecond=0)
    for d in devices:
        cps = d.get("controlledProperty") or []
        if not cps:
            continue
        device_uuid = d["id"].rsplit(":", 1)[-1]
        for cp in cps:
            unit, lo, hi = UNITS.get(cp, ("", 0.0, 1.0))
            entity_id = f"urn:ngsi-ld:DeviceMeasurement:{device_uuid}:{cp}"
            for i in range(days * per_day):
                ts = now - timedelta(hours=(days * per_day - i) * (24 / per_day))
                value = round(random.uniform(lo, hi), 2)
                attrs = {
                    "refDevice": {"type": "Text", "value": d["id"]},
                    "controlledProperty": {"type": "Text", "value": cp},
                    "numValue": {"type": "Number", "value": value},
                    "dateObserved": {
                        "type": "DateTime",
                        "value": ts.isoformat().replace("+00:00", "Z"),
                    },
                    "unitCode": {"type": "Text", "value": unit},
                }
                status, body = orion_post(
                    "/v2/entities",
                    {"id": entity_id, "type": "DeviceMeasurement", **attrs},
                )
                if status == 422 and "Already Exists" in body:
                    orion_post(
                        f"/v2/entities/{entity_id}/attrs",
                        attrs,
                        expect=(200, 201, 204),
                    )
                pushed += 1
                # Small breather to avoid overwhelming Orion / QL.
                if pushed % 50 == 0:
                    time.sleep(0.05)
    print(f"  pushed {pushed} telemetry points")
    return pushed


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    print(f"API   : {API_URL}")
    print(f"Orion : {ORION_URL}")
    try:
        api_get("/api/v1/devices?limit=1")
    except HttpError as exc:
        print(f"ERROR: cannot reach API at {API_URL}: {exc}", file=sys.stderr)
        return 1

    wipe_seed_data()
    op_types = seed_operation_types()
    devices = seed_devices(50)
    seed_maintenance(devices, op_types, 150)
    seed_telemetry(devices, days=3, per_day=8)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
