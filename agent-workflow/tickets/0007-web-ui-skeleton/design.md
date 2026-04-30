# 0007 — Design

## Layout
```
web/
  package.json
  tsconfig.json
  next.config.mjs
  postcss.config.mjs
  tailwind.config.ts
  .env.local.example
  .gitignore
  src/
    app/
      layout.tsx
      providers.tsx
      globals.css
      page.tsx                       # dashboard
      devices/
        page.tsx                     # list
        new/page.tsx
        [id]/
          page.tsx                   # detail (tabs)
          edit/page.tsx
      maintenance/
        operation-types/page.tsx
    components/
      top-nav.tsx
      user-menu.tsx
      logo.tsx
      delete-confirm.tsx
      forms/
        device-form.tsx              # shared by new/edit
        operation-type-form.tsx
        maintenance-log-form.tsx
      ui/                            # shadcn-style primitives
        button.tsx, input.tsx, label.tsx, textarea.tsx,
        select.tsx, dialog.tsx, dropdown-menu.tsx,
        table.tsx, badge.tsx, card.tsx, tabs.tsx,
        toast.tsx, toaster.tsx, use-toast.ts
    lib/
      api.ts                         # typed fetch + endpoints
      types.ts                       # API DTOs (mirror Pydantic)
      zod.ts                         # form schemas
      utils.ts                       # cn() helper
```

## API client
`src/lib/api.ts` exposes a tiny typed wrapper around `fetch` keyed on
`NEXT_PUBLIC_API_BASE_URL`. Errors carry `status` and `detail`. React
Query consumes it. No code generation; types live by hand in
`src/lib/types.ts` (mirror of `app/schemas*.py`).

## Forms
- `device-form.tsx` is a single component used in both `new` and `edit`.
  Mode prop: `"create" | "edit"`. Zod schema in `src/lib/zod.ts` reflects
  server-side validators (cross-protocol leak rejection is *not*
  duplicated client-side; we let the API 422 surface as a toast).

## Conditional fields
On `supportedProtocol` change, form reveals the matching field group
(MQTT / PLC / LoRaWAN). All extension fields are optional in the form;
required ones are marked with `*` and validated by the API.

## Backend change (CORS)
`platform/api/app/main.py`: add `fastapi.middleware.cors.CORSMiddleware`
with origins from `settings.cors_allow_origins` (comma-separated env,
default `http://localhost:3000`). No new dependency (CORS middleware
ships with FastAPI/Starlette).

## Auth placeholder
`UserMenu` shows a User icon button. Dropdown has one item: "Sign out"
which calls `toast({title: "Logout will arrive in ticket 0009"})`. No
session, no redirect, no cookies.

## Build/run
- `cd web && npm install && npm run dev` → http://localhost:3000.
- API must be reachable at `NEXT_PUBLIC_API_BASE_URL`.

## What this ticket does NOT change
- `make` targets and Docker compose stay the same (web is dev-only for
  now; production packaging arrives later).
- Existing 75 pytest tests still pass after the CORS middleware is added.
