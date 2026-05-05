# Journal — Ticket 0021a

## 2026-05-05

### Decisions
- Bug 1 fix: when `lastN` is set, omit `limit` from the QL query
  entirely. Initial attempt was to forward `limit=lastN`, but QL
  returned a different ordering when both bounds matched the
  result size (the previously-flaky
  `test_query_lastN_limits_results` started failing
  deterministically). Letting `lastN` drive QL alone restores the
  documented "last N entries" behaviour.
- Bug 2 fix: replaced `<input type="datetime-local">` with two
  shadcn `<Input>`s parsed via `date-fns` (`dd/MM/yyyy HH:mm`).
  User confirmed OS is Spanish; the locale mismatch is somewhere
  in browser/OS plumbing we can't reach. Going with the controlled
  widget is the safer, locale-stable option.
- Raw-table pagination at 100 rows/page client-side. The chart
  still consumes the full series (max 1000 from QL); only the
  table is paginated.

### Surprises
- RTL `cleanup` is not automatic in this repo's vitest config
  (`globals: false`). Without `afterEach(cleanup)`, multiple
  `render()` calls accumulate inside the same jsdom document and
  `getAllByRole` returns both trees' inputs. Caught it via a
  scratch debug test that showed the spy *was* being called — on
  the wrong harness.

### Verified
- `make test`: 185 passed (was 184; +1 new pagination test).
- `npx tsc --noEmit`: clean.
- `npm run lint`: clean.
- `npm test`: 32 passed (was 23; +6 paginate, +3 datetime-input).
