# Review — Ticket 0021a

## What changed

Backend (`platform/api/`):
- `app/routes/telemetry.py`: when `lastN` is provided, omit
  `limit` from the QL call so QL returns the full last-N. `limit`
  upper bound bumped from 1000 → 10000 (no caller forces it
  today; widening only).
- `tests/test_telemetry.py`: new
  `test_query_lastN_not_capped_by_default_limit` (seeds 105
  measurements; previously route capped at 100).

Frontend (`web/`):
- `src/lib/paginate.ts` (new): pure `paginate(items, page,
  pageSize=100)` clamping into `[1, totalPages]`.
- `src/lib/paginate.test.ts` (new): 6 cases.
- `src/components/ui/datetime-input.tsx` (new): controlled
  two-text-input widget parsing `dd/MM/yyyy HH:mm` via date-fns.
  Emits ISO or null; renders an inline error when partially
  filled with garbage.
- `src/components/ui/datetime-input.test.tsx` (new): 3 cases
  (parse OK, invalid, empty). Adds `@testing-library/react` +
  `@testing-library/jest-dom` as devDeps.
- `src/app/devices/[id]/telemetry-tab.tsx`: rewires Personalizado
  to `<DateTimeInput>`; switches `customFrom/To` state to
  `string | null`; paginates the raw-data table at 100/page; resets
  page to 1 when `cp`, `range`, `customFrom`, or `customTo` change.
- `src/i18n/messages/{en,es}.json`: new `telemetry.custom.*` and
  `telemetry.table.*` keys.

## Acceptance criteria — evidence

- **A.1** `routes/telemetry.py` now passes `limit=None` to QL when
  `lastN is not None`.
- **A.2** New backend test asserts 105 entries on `lastN=1000`.
- **A.3..A.7** Custom widget + i18n; behaves regardless of OS
  locale.
- **A.9..A.12** Raw-table paginates 100/page; prev/next + page
  indicator; resets on dataset change; `paginate.test.ts` covers
  the helper.
- **A.13** `make test` 185/185, `npm test` 32/32, lint + tsc
  clean.

## Follow-ups

- **FU1** `test_query_lastN_limits_results` was already flagged
  flaky in `agent-workflow/memory/gotchas.md` (QL ordering when
  multiple measurements arrive within the same second). The fix
  here side-steps it by not passing `limit`, but the underlying
  ordering instability remains for future tickets that pass small
  `lastN` values.
- **FU2** A real popover/calendar `<DateTimePicker>` (single
  control, keyboard nav). The two-input fix is intentionally
  minimal.
- **FU3** Server-side pagination (`offset` plumbing through the
  API) when telemetry windows routinely exceed 1000 samples.
