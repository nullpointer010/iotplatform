# Design

## Backend

- `schemas.GeoPoint` gains `site_area: str | None = None` (extra="forbid"
  still). One unit-style test verifies the round-trip.
- No new endpoints; no changes to the devices list query interface
  (search stays client-side per requirements).

## Web

### Types & schema

- `Device`: add `site_area` to `location`. No other shape change — the
  remaining fields already exist on the type.
- `deviceFormSchema`:
  - `latitude`, `longitude`: optional numeric (preprocess empty → undef);
    refine "both or neither".
  - `siteArea`: optional string.
  - `addressJson`: optional JSON string (parsed on submit).
  - `dateInstalled`: optional `datetime-local` string converted to ISO.
  - `ownerCsv`, `ipAddressCsv`: optional CSV → string[].
  - `dataTypesJson`, `mqttSecurityJson`, `plcCredentialsJson`: optional
    JSON strings.
- `toApiPayload` performs the JSON parsing and CSV splitting; on parse
  errors it submits the raw string and lets the server reject (consistent
  with how `plcTagsMapping` already behaves).

### Form layout

- New "Location" section: lat / lon / site area.
- New "Administrative" section: dateInstalled, owner, ipAddress, address
  (JSON textarea).
- MQTT section: add `dataTypes` and `mqttSecurity` JSON textareas.
- PLC section: add `plcCredentials` JSON textarea.

### Devices list

- `useState` for `q` (search), `category`, `protocol`, `state`, `sort`.
- A toolbar above the table with one Input + three Selects + one sort
  Select + a "Clear" button.
- Filtering and sorting computed via `useMemo` over `devices.data`.
- Sort options: name asc/desc, category asc, state asc.
- Empty state when the filter excludes all rows ("No matches").

### Overview tab

- Add the new fields to the existing groups so they render automatically
  (location: latitude/longitude/site_area; admin: dateInstalled, owner,
  ipAddress, address). The `render` helper already handles arrays and
  objects.

## Seed script

- `platform/scripts/add_test_data.py` (Python, stdlib + httpx).
- Targets `http://localhost` (API), `http://localhost:1026` (Orion).
  Both overridable via env: `IOT_API_URL`, `IOT_ORION_URL`.
- Wipe phase:
  1. `GET /api/v1/devices?limit=10000`, delete every device whose id
     starts with `urn:ngsi-ld:Device:seed-`.
  2. `GET /api/v1/maintenance/operation-types`, delete every op-type
     whose name starts with `Seed: `.
  3. Maintenance logs cascade with device deletion; nothing else to do.
- Seed phase:
  - 8 operation types: Calibración, Reemplazo de batería, Limpieza,
    Inspección visual, Actualización de firmware, Sustitución de sensor,
    Reparación, Configuración.
  - 50 devices: deterministic UUIDv5 from `seed-N` + a "seed-" prefix in
    the URN so wipe targets them. Mix of categories/protocols/states.
    All use `location` and `address` populated from a small list of
    Spanish farms.
  - 150 maintenance log entries: random device × op-type × ±90 days.
  - Telemetry: for each sensor device with controlledProperty, push 3
    days × 8 readings/day of synthetic numeric measurements via Orion
    (`POST /v2/entities`). QuantumLeap subscription set up by
    `bootstrap.sh` indexes them.
- Idempotent: every run wipes the previous seed batch first. Non-seed
  data is left untouched (we filter by URN/name prefix).
- Make target: `make seed` runs `python3 platform/scripts/add_test_data.py`.
