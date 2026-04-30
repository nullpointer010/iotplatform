# Self-review

| AC | Status | Notes |
|----|--------|-------|
| Devices form exposes `location.site_area`, `address`, `dateInstalled`, `owner`, `ipAddress` and the per-protocol JSON fields. | OK | New Location + Administrative sections in `device-form.tsx`; JSON textareas added under MQTT and PLC sections. |
| `site_area` round-trips through the API. | OK | `test_create_with_location_site_area_round_trips` (`platform/api/tests/test_devices.py`); `make test` 76 passed. |
| Devices list supports text search, filter by category/protocol/state, and sort by name/category/state. | OK | Client-side `useMemo` pipeline in `web/src/app/devices/page.tsx`; toolbar exposes search input, three filter selects, sort dropdown and Clear button; "Showing X of Y" line. |
| Overview tab displays the new groups. | OK | Location and Administrative card groups in `overview-tab.tsx`. |
| Repeatable seed script creates ~50 devices, 8 op-types, ~150 maintenance entries and pushes telemetry. | OK | `platform/scripts/add_test_data.py` (stdlib only); live run produced 50 / 8 / 150 / 1824 telemetry points. |
| `make seed` wired. | OK | New `seed` target in `Makefile` (depends on `check-env`). |
| Web build green. | OK | `npx next build` — all 7 routes compile. |
| API tests green. | OK | `make test` — 76 passed. |

## Observations / follow-ups

- JSON textareas are intentionally raw; a structured editor for
  `plcTagsMapping` and `mqttSecurity` would be a nicer ergonomic next
  step but is out of scope here.
- Devices list sort is local to the loaded page (client side); when the
  device count exceeds the current 100-item default the UI will need
  server-side pagination + sort. Not needed for the current test data
  set.
- The seed wipe matches by the `Seed Device ` name prefix; manually
  created devices with that prefix will be wiped. Consider tagging seed
  entities with a dedicated attribute if that becomes a concern.

## External review
