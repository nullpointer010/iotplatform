# Ticket 0021b — datetime-keep-native-picker

## Problem

In 0021a I overshot the user's request. They asked to fix the
12 h / AM-PM display on the telemetry custom range; I replaced the
native `<input type="datetime-local">` with a two-text-input
custom widget, which works but **removes the calendar pop-up**
the user relied on. Maintenance and device-form still use the
native widget and still show AM/PM on the same browser, so the
two-input replacement also failed to fix the broader issue.

## Goal

Keep the native calendar picker everywhere (`<input
type="datetime-local">`) and force 24 h + EU date order via the
`lang="es-ES"` attribute, which Chromium and Firefox honour on
date/time inputs.

## Acceptance criteria

- [ ] **A.1** Telemetry "Personalizado" inputs are native
  `<input type="datetime-local" lang="es-ES">` again; the calendar
  pop-up works, format is `dd/mm/aaaa, HH:mm` (no AM/PM).
- [ ] **A.2** `MaintenanceLogForm` (`startedAt`, `endedAt`) and
  `DeviceForm` (`dateInstalled`) gain `lang="es-ES"` so they too
  show 24 h.
- [ ] **A.3** `DateTimeInput` component + its test are removed.
- [ ] **A.4** Unused i18n keys `telemetry.custom.*` are removed
  from `en.json` and `es.json`.
- [ ] **A.5** `paginate()` helper, raw-table pagination, and the
  backend `lastN` fix from 0021a remain intact.
- [ ] **A.6** `npm test`, `npm run lint`, `npx tsc --noEmit`
  clean. No backend change → no `make test` re-run needed.

## Out of scope

- A custom popover/calendar component (FU2 of 0021a).
- Locale-driven `lang` (we hard-code `es-ES` since the product is
  Spanish-only today; switch to `useLocale()` when we ship en).

## Approved 2026-05-06

User: "Fix it but not removing the calendar."
