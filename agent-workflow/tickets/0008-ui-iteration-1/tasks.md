# Tasks

- [x] Backend: add `site_area: str | None` to `GeoPoint`, write a unit
  test that round-trips it through `POST /devices` and `GET /devices/{id}`.
- [x] Web types: add `site_area` to `Device.location`.
- [x] Web zod: extend `deviceFormSchema` (lat/lon/siteArea/address/
  dateInstalled/owner/ipAddress + JSON dicts).
- [x] Web form: add Location + Administrative sections, plus the JSON
  textareas in MQTT/PLC sections.
- [x] Web list: search input + 3 filter selects + sort dropdown + clear
  button, all client-side.
- [x] Overview tab: include new fields in the group definitions.
- [x] Seed script `platform/scripts/add_test_data.py` (wipe + reseed
  devices, op-types, log, telemetry).
- [x] Add `make seed` target.
- [x] Run `make test` (76 expected) + `npm run build`.
- [x] Run the seed script against the live stack and eyeball the UI.
- [x] Close-out: journal, review, status=done, roadmap update,
  commit + push.
