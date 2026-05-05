# Journal — Ticket 0021

## 2026-05-05 — Plan & implementation

### Decisions
- Reused the existing endpoints. `PlacementOut` now carries
  `device_state` and `primary_property` so the client can render
  the marker state without a second Orion fetch. The numeric badge
  still requires a per-device telemetry call (`lastN: 1`); a
  proper `/sites/{area}/live` aggregate is tracked as FU1.
- `useQueries` with `refetchIntervalInBackground: false` covers
  A.4 ("pauses when document.hidden"). No custom
  `visibilitychange` handler needed.
- Stale = older than 5 min, irrespective of `deviceState`. The
  classifier returns `stale` early so a `stale-and-active` device
  reads as "should be green but isn't reporting".
- Visuals use Tailwind tokens already in the palette
  (`emerald-500`, `amber-500`, `muted`). Stale uses the green hue
  at 40 % opacity + dashed border so the relationship to "active"
  is preserved. Dark-mode tweaks are FU.

### Surprises
- `from_ngsi` flattens Orion attributes, so `device.deviceState`
  is a plain string and `device.controlledProperty` is a plain
  list. The original design draft assumed `{type, value}`
  wrappers; corrected before writing the helpers.
- Ran into a stray `);` after a multi-replace: the page edit had
  an outdated `oldString` slice that didn't include the closing
  paren of the prior block. Caught immediately by tsc.

### Verified
- `make test`: 184 passed (was 183; +1 new placement test).
- `npx tsc --noEmit`: clean.
- `npm run lint`: clean.
- `npm test`: 23 passed (was 17; +6 new marker-state tests).
