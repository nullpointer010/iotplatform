# Tasks — Ticket 0011

## Goals (verifiable)
- [ ] `npm --prefix web run build` succeeds.
- [ ] `npm --prefix web test` runs vitest and passes.
- [ ] `make test` (backend) still passes 80/80.
- [ ] Manual smoke: `npm --prefix web run dev` against the live API; locale toggle, tooltips on hover/focus, optimistic delete + rollback on simulated 500, empty-state CTAs.

## Steps

### 1. Deps + tooling
- [ ] Add `next-intl`, `@radix-ui/react-tooltip` to `web/package.json` deps.
- [ ] Add `vitest`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/jest-dom` (optional) to devDeps.
- [ ] Add `"test": "vitest run"` to scripts.
- [ ] Create `web/vitest.config.ts` (jsdom env).
- [ ] `npm install` inside `web/`.

### 2. Primitives
- [ ] `web/src/lib/orion-chars.ts` — regex + helper + human string.
- [ ] `web/src/lib/orion-chars.test.ts` — two cases (happy + failing). Run `npm test`.
- [ ] `web/src/components/ui/tooltip.tsx` — Radix re-exports + styled `TooltipContent`.
- [ ] `web/src/components/forms/field-label.tsx` — FieldLabel with `Info` icon trigger.
- [ ] `web/src/components/ui/empty-state.tsx` — title/description/action.

### 3. i18n
- [ ] `web/src/i18n/index.ts` — `getLocaleFromCookie()`, `loadMessages(locale)`, `LOCALES`.
- [ ] `web/src/i18n/messages/es.json` + `en.json` — full catalog from design.
- [ ] `web/src/app/layout.tsx` — wrap in `<NextIntlClientProvider>` + `<TooltipProvider>`. Read cookie via `next/headers`. Substitute `{orionRule}` once at provider init.

### 4. Mutation helpers
- [ ] `web/src/lib/mutate.ts` — `useMutateWithToast` (uses `useTranslations`).
- [ ] `web/src/lib/optimistic.ts` — `optimisticListDelete` returning a `rollback`.

### 5. Zod
- [ ] `web/src/lib/zod.ts` — add `noOrionUnsafeChars`. Apply to: `name`, `manufacturerName`, `modelName`, `serialNumber`, `firmwareVersion`, `siteArea`, `mqttClientId`, and per-item to `ownerCsv`.
- [ ] In forms, render `orionForbidden:{char}` token via `t('zod.orionForbidden', { char })`.

### 6. Forms
- [ ] `device-form.tsx` — replace local `Field`/`<Label>` with `<FieldLabel>`. Pull labels + tooltips from `t('device.field.<name>.label')` / `tooltip`. Section titles from `device.section.<id>.title`. Translate "Name *", "Save"/"Cancel", "Save failed" toasts.
- [ ] `operation-type-form.tsx` — same pattern.
- [ ] `maintenance-log-form.tsx` — same pattern.

### 7. List + detail pages
- [ ] `app/devices/page.tsx` — 6-column trim, `<EmptyState>` for the no-devices branch with "Create your first device" CTA, switch delete to `useMutateWithToast` + `optimisticListDelete`.
- [ ] `app/devices/[id]/overview-tab.tsx` — uniform typography (`<dt class="text-xs uppercase tracking-wide text-muted-foreground">` / `<dd class="text-sm">`), 2-col grid, no inline `style=`.
- [ ] `app/devices/[id]/maintenance-tab.tsx` — empty state + optimistic delete.
- [ ] `app/devices/[id]/telemetry-tab.tsx` — empty state.
- [ ] `app/maintenance/operation-types/page.tsx` — empty state + optimistic delete + i18n strings.
- [ ] `app/page.tsx` (dashboard) — i18n strings.

### 8. Top nav + user menu
- [ ] `components/top-nav.tsx` — link labels via `t('nav.…')`.
- [ ] `components/user-menu.tsx` — add a `Language` submenu with `Español` / `English`. On click: write cookie + `router.refresh()`.

### 9. Header pattern
- [ ] Devices list / device detail / device new / device edit / op-types: uniform `<header>` row (Tailwind, no new component): h1 + subtitle + right-aligned primary action.

### 10. Verification
- [ ] `npm --prefix web run lint` clean.
- [ ] `npm --prefix web run build` clean.
- [ ] `npm --prefix web test` green.
- [ ] `make test` 80/80 green (no regression).
- [ ] Manual: every form field that should show an `(i)` icon shows it; hovering opens the tooltip; focusing the icon with Tab opens it.
- [ ] Manual: paste `Juan (IFAPA)` into Owner CSV → inline error in Spanish citing `(`. Submit blocked.
- [ ] Manual: delete a device → row disappears immediately; success toast. Stop the API container, delete again → row reappears (rollback) and a destructive toast shows.
- [ ] Manual: switch locale to English in user menu → all 4 main pages flip with no leftover Spanish.
- [ ] Manual: empty op-types list → CTA visible.
- [ ] Update `journal.md` with decisions actually taken; finalize `review.md`; flip `status.md` to `review`.
