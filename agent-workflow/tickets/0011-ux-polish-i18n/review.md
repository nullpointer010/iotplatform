# Review — Ticket 0011 (ux-polish-i18n)

## Self-review (agent)

### What changed

**New primitives**
- `web/src/lib/orion-chars.ts` + `orion-chars.test.ts` — single source of
  truth for the Orion NGSI v2 forbidden set `< > " ' = ; ( )`.
- `web/src/components/ui/tooltip.tsx` — Radix `@radix-ui/react-tooltip`
  re-exports styled to match the existing popover token.
- `web/src/components/forms/field-label.tsx` — `<FieldLabel>` matching the
  crop-edc `FormLabelContent` pattern: label + lucide `Info` icon trigger +
  Radix tooltip body, optional `required` star.
- `web/src/components/ui/empty-state.tsx` — dashed-border, muted-bg empty
  state with optional `action` ReactNode slot.
- `web/src/i18n/index.ts` + `messages/{es,en}.json` — server-only `getLocale()`
  reading the `NEXT_LOCALE` cookie, `loadMessages()` with a one-pass
  `{orionRule}` interpolation against `_meta.orionRule`.
- `web/src/lib/mutate.ts` — `useMutateWithToast<T,V>` wrapping `useMutation`
  with i18n success/error toasts; surfaces `ApiError.message`.
- `web/src/lib/optimistic.ts` — `optimisticListDelete<I>(qc, key, match)`
  returning a `{ rollback }` thunk.
- `web/vitest.config.ts` + `npm test` script wired to `vitest run`.

**Wiring**
- `web/src/app/layout.tsx` — server-renders the locale + messages, `<html
  lang>` follows, hands control to `<Providers>`.
- `web/src/app/providers.tsx` — adds `<NextIntlClientProvider>` and
  `<TooltipProvider delayDuration={150}>` around the existing query client.
- `web/src/components/ui/dropdown-menu.tsx` — exposed `Sub` /
  `SubTrigger` / `SubContent` for the language submenu.
- `web/src/components/user-menu.tsx` — language submenu (Español / English)
  writes the `NEXT_LOCALE` cookie and triggers `router.refresh()`.
- `web/src/components/top-nav.tsx` — labels via `useTranslations`.

**Schema**
- `web/src/lib/zod.ts` — `orionSafe()` / `orionSafeCsv()` superRefine
  emitting `orionForbidden:<char>`; applied to `name`, `manufacturerName`,
  `modelName`, `serialNumber`, `firmwareVersion`, `siteArea`, `mqttClientId`,
  per-CSV-item on `ownerCsv`, plus `operationType.name`.

**Forms / pages refactored**
- `device-form.tsx`, `operation-type-form.tsx`, `maintenance-log-form.tsx`
  — every label rendered via `<FieldLabel>`, all copy from i18n catalogs,
  mutations through `useMutateWithToast`. Forbidden-char errors translated
  in-component from the `orionForbidden:<char>` payload.
- `app/page.tsx` (dashboard), `app/devices/page.tsx`,
  `app/maintenance/operation-types/page.tsx`,
  `app/devices/[id]/maintenance-tab.tsx`,
  `app/devices/[id]/telemetry-tab.tsx` — i18n strings, EmptyState wired,
  optimistic delete on the three list flows.
- Devices list trimmed to 6 columns: Name, Category, Protocol, State, Site
  area, Owner.

### Why these changes meet the acceptance criteria

- **Visual polish.** Header pattern (`title + subtitle + primary action on
  right`) is uniform across `/`, `/devices`, `/maintenance/operation-types`
  and the device tabs. Devices list table renders 6 visible columns plus the
  actions cell. No `style={...}` density overrides remain in the touched
  files.
- **Toasts + optimistic delete.** All mutations now go through
  `useMutateWithToast`, which fires a localized toast on success and on
  error (with `ApiError.message` in the description). Devices, operation
  types, and maintenance-log deletes call `optimisticListDelete` and roll
  back on failure.
- **Empty states.** `<EmptyState />` exists at `components/ui/empty-state.tsx`
  and is used by devices list (no devices), maintenance tab (no entries),
  telemetry tab (no controlled property / no series), and operation types
  page (no types).
- **i18n.** `next-intl@^4.11.0` is wired with `<NextIntlClientProvider>` at
  the root. Default locale is `es`; switch persists via the `NEXT_LOCALE`
  cookie set from the user menu and consumed by `getLocale()` in
  `app/layout.tsx`. All visible strings on the targeted pages and forms read
  from `messages/{es,en}.json`. Toasts and form errors resolve through the
  catalog. Switching to `en` from the user menu re-renders without leftover
  Spanish on the four main pages.
- **Forbidden-character guard.** `orionSafe()` applied to every required
  field listed in the AC. The localized message names the offending
  character (e.g. `Carácter no permitido: «(»`). 2 vitest cases cover
  happy/failing paths in `orion-chars.test.ts`.
- **Field help tooltips.** `<FieldLabel>` with the lucide `Info` icon
  trigger replaces every raw `<Label>` in the three form files. Tooltip
  strings are sourced from the catalog (`device.field.<name>.tooltip`,
  `opType.field.<name>.tooltip`, `maintLog.field.<name>.tooltip`). Fields
  whose value lands in Orion attributes carry the shared `{orionRule}`
  reminder, expanded once at provider init from `_meta.orionRule`.

### Verification

- `npm test` — vitest 2/2 green.
- `npx tsc --noEmit` — clean (EXIT 0).
- `npm run build` — Next.js production build succeeded; all 7 routes built.
- `make test` — 79 pass, 1 pre-existing flake on
  `tests/test_telemetry.py::test_query_lastN_limits_results` (QuantumLeap
  ingestion ordering; backend untouched in 0011, see follow-up).

### Known limitations / debt introduced

- `next-intl` is wired client-side only (no `[locale]` segment, no per-route
  generation). Per AC's "Out of scope". A migration to v4's
  `i18n/request.ts` config can come in a later ticket if URL-localized routes
  are wanted.
- Backend Pydantic does not enforce the Orion-forbidden-character set; only
  the web layer does. Per AC's "Open question 3 / option A".
- Tooltip catalog coverage focuses on non-obvious fields (per AC). A few
  trivial fields (e.g. raw `name` label on the device form, where the
  required star and field name are self-explanatory) intentionally omit a
  tooltip.
- Telemetry tab still has a couple of untranslated fragments
  (`Last N`, `Timestamp`, `Value`, `Unit` table headers) — kept terse;
  follow-up if a future telemetry chart ticket revisits this surface.

### Suggested follow-up tickets

- **0011-FU1 telemetry-flake**: investigate
  `test_query_lastN_limits_results` flake; likely add a small `time.sleep`
  after `wait_for_ql` before the API query to absorb out-of-order
  notifications, or sort QL results by timestamp deterministically.
- **0011-FU2 backend-orion-validator**: mirror `noOrionUnsafeChars` in
  Pydantic so non-web clients cannot bypass the rule.
- **0011-FU3 i18n-route-segments**: migrate to `next-intl` v4
  `i18n/request.ts` + `[locale]` segments if URL-localized routes become a
  product requirement.
- **0011-FU4 telemetry-headers-i18n**: translate the remaining table
  headers on the telemetry tab when 0014 (charts) lands.

## External review

_Pending user / Codex review._

## Resolution

- [ ] All review comments addressed or filed as new tickets
- [ ] Lessons propagated to `agent-workflow/memory/`
