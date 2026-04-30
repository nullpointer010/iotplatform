# Design — 0002 Data model decision

This ticket has no production code. The deliverable is a single doc,
`agent-workflow/data-model.md`. Below is the **full proposed content**;
once approved it is moved verbatim to that path and `architecture.md`
gains a link to it.

---

## Strategy

Flat schema, attribute names aligned with FIWARE Smart Data Models
naming. **No** full SDM adoption (no `@context`, no SDM JSON-Schema
validation). Migration to full SDM later only adds a context document and
stricter validation; no field renames.

## FIWARE conventions

- `fiware-service: iot`
- `fiware-servicepath: /`
- NGSI v2 (Orion 4.4.0). NGSI-LD migration is a future concern.
- Stored entity id is a URN: `urn:ngsi-ld:Device:<uuid>`. The API accepts
  a bare UUID in requests and normalises to the URN before talking to
  Orion. Responses always carry the URN form.

## HTTP error contract

| Code | When                                                                  |
|------|-----------------------------------------------------------------------|
| 200  | Successful read or partial update                                     |
| 201  | Resource created                                                      |
| 400  | Malformed query string (bad date, bad pagination)                     |
| 404  | Unknown id                                                            |
| 409  | Duplicate id on create                                                |
| 415  | Reserved for upload tickets (PDF)                                     |
| 413  | Reserved for upload tickets (PDF)                                     |
| 422  | Validation error in request body (FastAPI default)                    |
| 5xx  | Upstream Orion / QuantumLeap / CrateDB failure (mapped 502/503)       |

## Optional attributes

When a client omits an optional attribute, the API omits it from the
Orion payload (does not send `null`). On read, the API returns only the
attributes Orion holds; absent attributes are simply absent from the JSON
response.

## Device — base attributes (NGSI entity type `Device`)

All field names are lowerCamelCase to match NGSI / SDM conventions.

| API / NGSI name      | NGSI type        | Required | backend.md source           | SDM alignment              | Example |
|----------------------|------------------|----------|-----------------------------|----------------------------|---------|
| `id`                 | (entity id)      | yes      | `id`                        | `Device.id`                | `urn:ngsi-ld:Device:550e8400-e29b-41d4-a716-446655440000` |
| `type`               | (entity type)    | yes      | n/a (always `Device`)       | `Device.type`              | `Device` |
| `name`               | Text             | yes      | `name`                      | `Device.name`              | `Sensor de Temperatura Sala A` |
| `category`           | Text             | yes      | `type` (sensor/actuator/…)  | `Device.category`          | `sensor` |
| `controlledProperty` | StructuredValue (array of Text) | no | `metadata` (per-type)   | `Device.controlledProperty`| `["temperature","humidity"]` |
| `serialNumber`       | Text             | no       | `device_id.id_value`        | `Device.serialNumber`      | `00:1B:44:11:3A:B7` |
| `serialNumberType`   | Text             | no       | `device_id.id_type`         | n/a (extension)            | `MAC` |
| `supportedProtocol`  | Text             | yes      | `protocol`                  | `Device.supportedProtocol` | `mqtt` |
| `location`           | geo:point        | no       | `location.{latitude,longitude}` | `Device.location`      | `40.4168,-3.7038` |
| `address`            | StructuredValue  | no       | `location.site_area`        | `Device.address`           | `{"streetAddress":"Almacén Principal"}` |
| `manufacturerName`   | Text             | no       | `admin_data.manufacturer`   | `Device.manufacturerName`  | `Siemens` |
| `modelName`          | Text             | no       | `admin_data.model`          | `Device.modelName`         | `S7-1200` |
| `dateInstalled`      | DateTime         | no       | `admin_data.installation_date` | `Device.dateInstalled`  | `2023-01-15T00:00:00Z` |
| `owner`              | StructuredValue (array of Text) | no | `admin_data.owner`        | `Device.owner`             | `["Juan Pérez"]` |
| `firmwareVersion`    | Text             | no       | `technical_specs.firmware_version` | `Device.firmwareVersion` | `v1.2.3` |
| `ipAddress`          | StructuredValue (array of Text) | no | `technical_specs.ip_address` | `Device.ipAddress`     | `["192.168.1.100"]` |
| `deviceState`        | Text             | no       | "estado del dispositivo"    | `Device.deviceState`       | `active` (one of: active, inactive, maintenance) |

`backend.md` `admin_data.maintenance_history` is **not** modelled on the
device entity; maintenance is a separate Postgres subsystem (ticket
0005).

`backend.md` `technical_specs` (CPU/RAM/storage) beyond `firmwareVersion`
and `ipAddress` is dropped for now — out of scope until a real ticket
needs it.

## Per-protocol extensions

Extension attributes are added to the same `Device` entity (no separate
type). Required protocol attributes are mandatory **only when**
`supportedProtocol` matches.

### MQTT (when `supportedProtocol == "mqtt"`)

| Attribute        | NGSI type        | Required | backend.md source | Example |
|------------------|------------------|----------|-------------------|---------|
| `mqttTopicRoot`  | Text             | yes      | `mqtt_topic_root` | `instalacion/salaA/temp/sensor1` |
| `mqttClientId`   | Text             | yes      | `client_id`       | `sensor1` |
| `mqttQos`        | Number (0/1/2)   | no       | `qos`             | `1` |
| `dataTypes`      | StructuredValue  | no       | `data_types`      | `{"instalacion/salaA/temp":"float"}` |
| `mqttSecurity`   | StructuredValue  | no       | `security`        | `{"type":"TLS"}` |

### PLC (when `supportedProtocol == "plc"`)

| Attribute          | NGSI type        | Required | backend.md source     | Example |
|--------------------|------------------|----------|-----------------------|---------|
| `plcIpAddress`     | Text             | yes      | `ip_address`          | `192.168.1.100` |
| `plcPort`          | Number           | yes      | `port`                | `502` |
| `plcConnectionMethod` | Text          | yes      | `connection_method`   | `Modbus TCP` |
| `plcCredentials`   | StructuredValue  | no       | `credentials`         | `{"username":"admin","password":"…"}` (stored opaque; ticket 0009 will move secrets out) |
| `plcReadFrequency` | Number (seconds) | no       | `read_frequency`      | `10` |
| `plcTagsMapping`   | StructuredValue  | yes      | `tags_mapping`        | `{"DB1.DW10":"Temperatura Caldera"}` |

### LoRaWAN (when `supportedProtocol == "lorawan"`)

| Attribute         | NGSI type | Required | backend.md source | Example |
|-------------------|-----------|----------|-------------------|---------|
| `loraAppEui`      | Text      | yes      | `appeui`          | `70B3D57ED00001A6` |
| `loraDevEui`      | Text      | yes      | `deveui`          | `0004A30B001C0530` |
| `loraAppKey`      | Text      | yes      | `appkey`          | `8D7F3A2C…` (opaque now; secrets in 0009) |
| `loraNetworkServer` | Text    | yes      | `network_server`  | `lora.example.com` |
| `loraPayloadDecoder` | Text   | yes      | `payload_decoder` | `decoder_v1` |

## Allowed values

- `category`: `sensor`, `actuator`, `gateway`, `plc`, `iotStation`,
  `endgun`, `weatherStation`, `other`. Validation in API layer.
- `supportedProtocol`: `mqtt`, `coap`, `http`, `modbus`, `bacnet`,
  `lorawan`, `plc`, `other`. Lowercase only.
- `deviceState`: `active`, `inactive`, `maintenance`.

## Telemetry — NGSI to CrateDB

### Entity-type-per-measurement-class

Each device emits telemetry into one or more **measurement entities**,
not into the `Device` entity itself. This keeps the Device record stable
and matches Smart Data Models' `DeviceMeasurement` pattern.

Convention:

- Measurement entity id: `urn:ngsi-ld:DeviceMeasurement:<deviceUuid>:<property>`
  (e.g. `…:Temperature`, `…:Humidity`).
- Measurement entity type: `DeviceMeasurement`.
- Refers to source device via attribute `refDevice` (Relationship-style
  Text holding the Device URN).

### DeviceMeasurement attributes

| Attribute          | NGSI type | Required | SDM alignment                     | Example |
|--------------------|-----------|----------|-----------------------------------|---------|
| `refDevice`        | Text      | yes      | `DeviceMeasurement.refDevice`     | `urn:ngsi-ld:Device:550e…` |
| `controlledProperty` | Text    | yes      | `DeviceMeasurement.controlledProperty` | `temperature` |
| `numValue`         | Number    | yes      | `DeviceMeasurement.numValue`      | `25.4` |
| `unitCode`         | Text (UN/CEFACT code) | no | `DeviceMeasurement.unitCode`     | `CEL` (Celsius), `P1` (percent), `KGM`, `MTR` |
| `dateObserved`     | DateTime  | yes      | `DeviceMeasurement.dateObserved`  | `2026-04-30T12:34:56Z` |
| `location`         | geo:point | no       | inherited from device             | `40.4168,-3.7038` |

For non-numeric measurements (`"ON"`, `"OFF"`, error codes) use a parallel
`textValue` attribute and omit `numValue`. Future ticket if needed; not
mandatory for the first telemetry slice.

### CrateDB tables (created automatically by QuantumLeap)

QuantumLeap creates one table per `(fiware-service, entity-type)` pair.
With `fiware-service: iot`:

- Schema: `mtiot`
- Table: `etdevicemeasurement` (lowercased entity type with `et` prefix)
- Columns mirror the NGSI attributes above plus QL-managed `entity_id`,
  `entity_type`, `time_index`, `fiware_servicepath`.

### Scaling: monthly partitioning

After QL creates the table on first ingest, a one-time DDL applies
monthly partitioning:

```sql
ALTER TABLE mtiot.etdevicemeasurement
  PARTITION BY (date_trunc('month', time_index));
```

Rationale: at sustained 1 Hz across 1000 devices we hit ~2.6 B rows/year;
monthly partitions (~220 M rows/month) keep pruning effective and let us
drop old months in one DDL. Operational ticket later will automate
retention; the partitioning shape is fixed now.

The DDL is applied by a small idempotent script in 0004 (the first
telemetry ticket). This ticket only **fixes the policy**.

### API query path

- `GET /api/v1/devices/{id}/telemetry` ⇒ API → QuantumLeap REST
  (`/v2/entities/<measurement-urn>` with `lastN`, `fromDate`, `toDate`,
  `limit`, `offset`). The API never issues raw CrateDB SQL on this
  endpoint.
- Analytics / batch queries against CrateDB (e.g. Superset) are an
  operational concern, not an API endpoint. Out of scope.

## Pagination & filtering conventions

Used by every list endpoint:

| Param       | Type     | Default | Notes |
|-------------|----------|---------|-------|
| `limit`     | int 1–1000 | 100   | Mirrors Orion `limit`. |
| `offset`    | int ≥ 0    | 0     | Mirrors Orion `offset`. |
| `fromDate`  | ISO 8601 | —       | Telemetry only. |
| `toDate`    | ISO 8601 | —       | Telemetry only. Must satisfy `fromDate ≤ toDate`. |

Bad pagination → 400; bad date → 400; `fromDate > toDate` → 400.

## What this ticket is *not* deciding

- Authentication / Keycloak field mapping (ticket 0009).
- Maintenance schema (already fixed by `backend.md`; adopted in 0005).
- PDF documents (optional, ticket 0008).
- CrateDB retention policy / pruning automation.
- NGSI-LD migration.

## Deliverables

1. Move the content above to `agent-workflow/data-model.md` (verbatim,
   strip the "Design — 0002" header).
2. Add a "Data model" section to `agent-workflow/architecture.md`
   pointing to `data-model.md`.
3. No code, no compose, no Makefile changes.