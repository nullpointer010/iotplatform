# 0007 — Web UI skeleton

## Why
A minimal but complete operator UI for the platform features built in
0001–0006. Same stack family as `/home/maru/crop-edc/frontend` for
consistency. Real authentication is **out of scope**; Keycloak lands in
0009. The user dropdown shows a placeholder "Sign out" entry.

## Acceptance criteria

- AC1 New top-level `web/` Next.js 14 project, TypeScript, App Router,
  Tailwind, lints clean and `next build` succeeds.
- AC2 Top bar: logo/title (left), nav links (Dashboard, Devices,
  Operation Types), user dropdown (right) with a Sign-out placeholder.
- AC3 Devices list: shows name, category, supportedProtocol, deviceState,
  with view/edit/delete actions. Delete asks for confirmation.
- AC4 Device create form: required fields validated client-side via Zod;
  protocol-specific fields appear conditionally for mqtt/plc/lorawan.
- AC5 Device detail page with tabs: Overview (all attributes), Telemetry
  (table for a chosen `controlledProperty` and date range), Maintenance
  (per-device log list + create form).
- AC6 Device edit form (PATCH): same shape as create, all fields optional.
- AC7 Operation types CRUD page (list + create + edit + delete).
- AC8 React Query for fetching, RHF + Zod for forms, toast on success/
  error.
- AC9 API base URL via `NEXT_PUBLIC_API_BASE_URL` env, default
  `http://localhost:8000`.
- AC10 FastAPI exposes CORS for the dev origin (`CORS_ALLOW_ORIGINS` env,
  default `http://localhost:3000`).

## Out of scope
- Real auth / Keycloak (ticket 0009).
- Telemetry charts (table only).
- i18n.
- UI tests (Playwright/Jest) — added later if needed.
- PDF manual upload UI (ticket 0008).
- Server-side rendering of authenticated data (everything is client-rendered
  with React Query against the public dev API).
