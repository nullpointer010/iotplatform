# Journal

## Decisions

- **Stack subset.** Mirrored `crop-edc/frontend` choices but kept only what
  this ticket needs: Next.js 14 App Router, Tailwind, Radix primitives,
  TanStack Query, react-hook-form + Zod. Skipped i18n, theme switcher,
  storybook, MSW, etc. Keep the surface small.
- **Palette mapping.** Crop colors live as Tailwind extensions
  (`crop-dark/olive/lime/light`) and as HSL tokens
  (`--primary: 143 32% 27%`) so shadcn-style components consume them
  via `bg-primary`, `text-primary-foreground`. One source of truth.
- **No type codegen.** Manually mirrored Pydantic schemas in
  `src/lib/types.ts`. Keeps the frontend buildable without a backend
  running. Worth revisiting if the API surface grows.
- **JSON-typed PLC mapping.** `plcTagsMapping` is a free-form JSON object
  on the API. UI exposes a textarea and `JSON.parse`s on submit; surfaces
  parse errors as a Zod refinement.
- **DELETE /devices/{id}.** Not in original `backend.md`, but the user
  explicitly asked for delete in the UI. Implemented surgically: Orion
  204 → cascade remove `maintenance_log` rows for that device id; Orion
  404 → 404. No new tests in this ticket (manual smoke only); flagged
  as a follow-up for 0009 alongside auth tests.
- **Auth placeholder.** User menu has logout that toasts a "coming in
  0009" message. Avoids wiring fake auth state that would have to be
  ripped out.
- **Cross-protocol fields.** Reused 0006 server-side validation; the
  client form simply hides the irrelevant sections based on
  `supportedProtocol`. The server still enforces the rule, the form is
  just a UX convenience.

## Lessons

- TanStack Query v5 returns `isPending` (not `isLoading`) for mutations
  but still uses `isLoading` for queries. Easy to mix up.
- Next.js 14 App Router needs `"use client"` for any tree using hooks
  (`useQuery`, `useForm`); kept the layout server-side and pushed the
  Provider boundary into `providers.tsx`.
- Telemetry test flake reproduced once again — the `lastN` ingestion
  race in `test_query_lastN_limits_results`. Re-running passed. Tracked
  in 0006 journal; no action here.
