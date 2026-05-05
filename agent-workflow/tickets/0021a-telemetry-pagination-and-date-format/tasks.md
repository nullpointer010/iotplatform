# Tasks — Ticket 0021a

- [x] T1. Backend: in `app/routes/telemetry.py`, forward
      `limit=lastN` to QL when `lastN` is set; bump `limit`'s
      `Query(le=…)` from 1000 to 10000.
      *(Implemented as: omit `limit` when `lastN` is set; passing
      both broke an existing test.)*
- [x] T2. Backend test `test_query_lastN_not_capped_by_default_limit`
      seeds 105 measurements and asserts `lastN=1000` returns 105.
- [x] T3. `make test` green (185 passed).
- [x] T4. Web: add `web/src/lib/paginate.ts`.
- [x] T5. Web: add `web/src/lib/paginate.test.ts`.
- [x] T6. Web: add `web/src/components/ui/datetime-input.tsx`.
- [x] T7. Web: add `web/src/components/ui/datetime-input.test.tsx`
      (+ added `@testing-library/react` and
      `@testing-library/jest-dom` as devDeps).
- [x] T8. Web: rewire `telemetry-tab.tsx`.
- [x] T9. Web: i18n keys in `en.json` + `es.json`.
- [x] T10. `npx tsc --noEmit`, `npm run lint`, `npm test` clean
      (32 passed).
- [~] T11. Manual smoke (user).
- [x] T12. Close ticket: journal + review + status flip + roadmap.