# Tasks — Ticket 0009

- [x] Replace `SITES` with the 8-row IFAPA La Cañada + UAL list.
- [x] Replace `OWNERS` with IFAPA/UAL-tagged variants (no parens — Orion forbids them).
- [x] Slugify `city` for `mqttTopicRoot` so `"La Cañada"` → `la-canada`.
- [x] `make seed` against live stack: 50/50 devices created, 8 op-types, 150 maintenance, 1872 telemetry points.
- [x] Spot-checks pass:
  - cities ⊂ `{"Almería", "La Cañada"}`
  - 8 unique `site_area` values, all IFAPA La Cañada or UAL prefixed
  - lat ∈ [36.819, 36.845], lon ∈ [−2.414, −2.392] — inside the acceptance box
  - owners include both `(IFAPA)` and `(UAL)` tagged values
  - mqtt topics slugified, e.g. `crop/la-canada/dev001`
