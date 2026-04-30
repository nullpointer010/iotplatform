# Review — Ticket 0009 — almeria-seed-context

## Self-review (agent)

### Acceptance criteria
- [x] Seed creates 50 devices in the IFAPA La Cañada / UAL Almería area.
- [x] All `address.city` values ∈ `{"Almería", "La Cañada"}`.
- [x] 8 unique `site_area` values, all prefixed `IFAPA La Cañada` or `UAL`.
- [x] All coordinates inside the acceptance box `[36.81, 36.86] × [−2.42, −2.38]`. Live: lat 36.819–36.845, lon −2.414–−2.392.
- [x] At least one owner contains `IFAPA` and one contains `UAL`.
- [x] `mqttTopicRoot` accepted by the API (slugified city).

### Files changed
- `platform/scripts/add_test_data.py` — `SITES`, `OWNERS`, new `_slug()` helper, `mqttTopicRoot` line.

No production routes, schemas, tests, or compose files touched.

### Notes / follow-ups
- Map UI ticket (0012 external map) can rely on these coordinates.
- Two pre-existing non-seed devices remain in the system (created in earlier manual tests). Not in scope for the seed wipe (it filters by `Seed Device ` name prefix). If desired, a future ticket can add a `--purge-non-seed` flag.

## External review (Codex / human)
<empty — awaiting reviewer>
