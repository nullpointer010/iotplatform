# Ticket 0021a — telemetry-pagination-and-date-format

## Problem

Two regressions reported on `/devices/[id]` telemetry tab:

1. **Pagination cap.** Switching the range to 24 h / 7 d / 30 d (or
   exporting CSV) only ever shows ~50–100 entries, even when many
   more samples exist in QuantumLeap. Root cause: the backend route
   `GET /devices/{id}/telemetry` declares `limit: int = 100` with
   `le=1000` and forwards it to QL alongside `lastN=1000` from the
   front end. QL applies both, so the result is capped to `limit`,
   not `lastN`. The front end never overrides `limit`, so it stays
   at 100.

2. **Date/time format on "Personalizado".** The custom range uses
   `<input type="datetime-local">`, whose display format is dictated
   by the browser/OS locale. The user is on a Spanish OS yet still
   sees `MM/DD/YYYY` and 12-h AM/PM — likely the browser running
   under a non-`es_ES` profile, or Chromium falling back to its
   own UI locale. Rather than chase the platform mismatch we replace
   the native widget with a small custom one we fully control. The
   stored `value` on `<input type="datetime-local">` is
   locale-independent (`YYYY-MM-DDTHH:mm`), but the rendered widget
   is not.

Both bugs degrade the operator workflow (incomplete CSV exports,
ambiguous date entry) so they get a small dedicated ticket before
moving on to 0023 alerts.

## Goal

Make `/devices/[id]` telemetry return all samples in the selected
window (up to a sensible hard cap), and present the custom-range
date/time inputs in 24 h / EU (`dd/mm/yyyy HH:mm`) format
regardless of browser locale.

## User stories

- As an **operator**, when I pick `7d` or `30d` on the telemetry
  tab, I want to see every sample in that window so the chart and
  CSV export reflect reality.
- As an **operator**, when I open "Personalizado", I want the date
  inputs to read `dd/mm/yyyy` and the time inputs to be 24-hour, so
  I don't accidentally pick the wrong day or AM/PM.

## Acceptance criteria (verifiable)

### Backend
- [ ] **A.1** `GET /api/v1/devices/{id}/telemetry`:
  - When `lastN` is provided, the route forwards `limit=lastN` to
    QuantumLeap (so QL doesn't silently cap the response below
    `lastN`).
  - When `lastN` is not provided, `limit` stays at the existing
    default but its hard cap is raised to `10000` to match QL's
    natural ceiling for a single page.
  - The validation bounds (`ge=1`) are kept; `lastN` retains its
    `le=1000` upper bound (FE only ever asks for 1000 today).
- [ ] **A.2** New backend test `test_query_lastN_not_capped_by_default_limit`
  in `tests/test_telemetry.py` seeds 200 measurements for one
  attribute and asserts `GET …?controlledProperty=…&lastN=1000`
  returns all 200 entries (today it returns 100). Test seeds via
  the existing fixtures (no new infra).

### Frontend
- [ ] **A.3** `/devices/[id]` telemetry tab "Personalizado" replaces
  both `<input type="datetime-local">` widgets with a small custom
  control rendered as **two adjacent text inputs**: a date input
  with placeholder `dd/mm/aaaa` and a time input with placeholder
  `hh:mm` (24 h). Each input validates against its format using
  `date-fns/parse`; invalid values disable the query (the chart
  shows the "select a property / range" empty state) and surface a
  small inline error under the field.
- [ ] **A.4** The component emits ISO-8601 timestamps to the existing
  `customFrom` / `customTo` state (so `rangeWindow` continues to
  work unchanged), preserving the existing query-key shape and
  CSV-export filename behaviour.
- [ ] **A.5** The control is locale-aware via `next-intl`: Spanish
  uses `dd/mm/aaaa hh:mm`, English uses `dd/mm/yyyy hh:mm` (still
  EU order — the project standardised on EU date order regardless
  of UI language, per existing convention in the dashboard cards).
- [ ] **A.6** Vitest unit test for the new control covers: valid
  parse → ISO emitted; invalid date → no ISO emitted + error flag;
  empty value → no ISO emitted + no error.
- [ ] **A.7** i18n keys `telemetry.custom.datePlaceholder`,
  `telemetry.custom.timePlaceholder`, `telemetry.custom.invalid`
  added to `en.json` and `es.json`.

### Frontend — raw table pagination
- [ ] **A.9** The "Raw table" `<details>` section under the chart
  paginates client-side at **100 rows / page**. The chart keeps
  consuming the full series.
- [ ] **A.10** Pagination controls: "Anterior" / "Siguiente"
  buttons + a `Page X of Y` indicator. Disabled at edges. State
  resets to page 1 when the property, range, or custom window
  changes.
- [ ] **A.11** i18n keys `telemetry.table.prev`,
  `telemetry.table.next`, `telemetry.table.pageOf` (with `{page}`
  / `{total}` placeholders).
- [ ] **A.12** Vitest unit test for the slice helper:
  `paginate(entries, page, pageSize)` returns the right window and
  clamps `page` into `[1, totalPages]`.

### Verification
- [ ] **A.13** `make test` and `npm test` pass; `npm run lint` and
  `npx tsc --noEmit` clean.

## Out of scope

- Streaming / paginated infinite scroll for very large windows
  (\u003e10 000 samples). The hard cap stays at 1000 per request via
  `lastN`; bigger downloads remain a future ticket.
- Changing CSV column layout or filename scheme.
- A full date-time picker calendar (popover + grid). Two text
  inputs are sufficient for this fix.
- Per-user locale override (the project still uses next-intl's
  current locale).

## Open questions

None — both bugs are well-scoped.
