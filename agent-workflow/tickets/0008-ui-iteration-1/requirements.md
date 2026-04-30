# Requirements

Iterate on the UI delivered by 0007 and close the worst gaps against
`context/doc/backend.md`.

## In scope

1. **Device form: missing fields.** Surface every metadata field already
   accepted by the API but not exposed in the UI:
   - `location` (latitude, longitude, optional zone label)
   - `address` (free dict — JSON)
   - `dateInstalled`, `owner` (list), `ipAddress` (list)
   - `dataTypes` and `mqttSecurity` (MQTT, JSON)
   - `plcCredentials` (PLC, JSON)
2. **Backend: location zone.** Backend.md lists `site_area` as part of
   location ("Almacén Principal", etc.). Extend `GeoPoint` with optional
   `site_area: str | None` so it is a structured field, not buried in
   `address`.
3. **Devices list browsing.** Client-side search by name/id, filter by
   category/protocol/state, sort by name/category/state.
4. **Detail view.** Show the new fields in the overview tab.
5. **Seed script.** `platform/scripts/add_test_data.py` populates the
   platform with realistic data: ~50 devices (mix of MQTT / PLC /
   LoRaWAN / HTTP / sensors / weather stations), 8 operation types,
   ~150 maintenance log entries, plus a few days of synthetic
   measurements for sensors. Re-running wipes previous seed data and
   recreates it.

## Out of scope

- Server-side search/filter/sort on `GET /devices`.
- `processing_capacity` and "last seen" derived columns.
- CSV export, tags/labels, audit timestamps on devices.
- Authentication (still 0009).

## Acceptance criteria

- `make test` stays green (75/75 + 1 new test for `site_area`).
- `npm run build` stays green.
- New seed script runs end-to-end against a fresh `make up` and the UI
  shows the seeded data.
- Device form lets you set every backend-accepted metadata field; UI
  re-displays them faithfully on the detail page.
- Devices list has search, three filters, and a sort dropdown that
  work on the current page of fetched devices.
