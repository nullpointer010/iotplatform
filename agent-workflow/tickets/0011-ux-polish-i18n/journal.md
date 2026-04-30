# Journal — Ticket 0011 (ux-polish-i18n)

## 2026-04-30

- Decision: kept `next-intl` integration minimal — custom `i18n/index.ts`
  reading cookie via `next/headers`, single `<NextIntlClientProvider>` at the
  root. Skipped the official `i18n/request.ts` config because we do not use
  `[locale]` route segments.
- Decision: i18n error key encoding: zod refinement emits
  `orionForbidden:<char>`; forms split-and-translate via
  `t('zod.orionForbidden', { char })`. Avoids leaking translation logic into
  schema and keeps zod purely synchronous.
- Decision: `useMutateWithToast` wraps `useMutation` and surfaces
  `ApiError.message` in the destructive toast description so 0010's
  observability gains (real Orion errors) are visible to users without
  per-call boilerplate.
- Decision: `optimisticListDelete` returns a `{ rollback }` thunk rather than
  full optimistic-update lifecycle hooks. The mutation function snapshots,
  removes, calls API, rolls back on throw — simpler and good enough for the
  three list-delete flows.
- Surprise: `next-intl@^4.11.0` was installed (npm picked latest), not v3 as
  the original design plan assumed. v4 keeps the same `useTranslations` /
  `NextIntlClientProvider` surface so no rewrite needed.
- Surprise: Zod's `optionalNonEmpty(s: ZodString)` typing broke once we
  started passing `ZodEffects` (from `superRefine`) — generalised to
  `<T extends z.ZodTypeAny>` to accept refined strings.
- Surprise: backend `test_query_lastN_limits_results` flaked twice in a row
  (`[52,54]` instead of `[53,54]`). 0011 changed no backend code; the test
  depends on QuantumLeap ingestion ordering. Filed as follow-up rather than
  blocking this ticket.
- Pivot: original plan had a `noOrionUnsafeChars` exported helper; consolidated
  it inside `lib/zod.ts` as `orionSafe()` / `orionSafeCsv()` because the
  refinement and the message-key emission are tightly coupled.

## Lessons (to propagate on close)

- → `memory/patterns.md`: i18n error keys carrying parameters via
  `key:value` strings (parsed in the consumer) keeps Zod schemas pure and
  sync while still feeding `next-intl` ICU placeholders.
- → `memory/patterns.md`: `useMutateWithToast` + `optimisticListDelete` is
  the agreed mutation/list pattern for this codebase. Reuse for any future
  CRUD list (operation types, maintenance, future telemetry sources).
- → `memory/gotchas.md`: `next-intl` v4 silently shipped — pin or document
  the major bump for any agent looking at older docs.
- → `memory/gotchas.md`: when `superRefine`-ing a `ZodString`, downstream
  helpers must take `ZodTypeAny` (or `ZodEffects`), not `ZodString`.
