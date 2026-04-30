# Journal — 0015 web-role-aware-ui

## Decisions

- **`/api/v1/me` over header-parsing.** oauth2-proxy already injects
  `X-Auth-Request-*` but the token is the source of truth — the API
  validates it anyway. A 10-line FastAPI route reusing
  `Depends(get_principal)` is cheaper to maintain than parsing proxy
  headers in a Next.js handler.
- **Hide, don't disable.** Per user request: viewers literally don't
  see the "Crear dispositivo", "Edit", "Delete", etc. buttons. Less
  noise, fewer "this is broken" support questions. The
  operation-types route is gated at the page level and redirects
  non-managers to `/devices`.
- **`<Gate roles={[]}>` = admin only.** Mirrors the API's
  `require_roles()` semantics so the matrices are identical.
- **Defence in depth via `assertRole`.** Pure helper used in
  destructive code paths. The API is the source of truth, but if a
  stray button slipped past a `<Gate>`, the mutation would still
  abort client-side before hitting the wire.
- **TanStack Query `["me"]` cache, 5 minute staleTime.** Same library
  the rest of the app uses — no new state plumbing.
- **401 → hard redirect to `/oauth2/sign_in`.** Cookie expiry is the
  only realistic 401 path; navigating to oauth2-proxy refreshes it
  via Keycloak SSO without bouncing the user back to a login page.

## Bugs and gotchas

- The previous `user-menu.tsx` imported `toast` but never used it; my
  replacement drops the import. tsc would have caught it.
- `make test` flake: `test_query_lastN_limits_results` is the
  pre-existing Orion→QL ingest race documented in 0013b. Not caused
  by this work.
- Operation-types redirect: I used a `useEffect` + `router.replace`
  rather than throwing. With React Query the role result is async on
  first render, and a synchronous `redirect()` would fire before
  `useMe` resolves. Returning `null` while not allowed avoids a flash
  of forbidden content.

## Verification

- `docker exec iot-api pytest tests/test_rbac.py -q` → 20/20 (was 15;
  +5 for `/me`).
- `make test` → 99/100 (1 pre-existing flake).
- `cd web && npm test` → 5/5 (was 2; +3 `assertRole`).
- `cd web && npx tsc --noEmit` → clean.
- `cd web && npx next build` → 7/7 routes compile.

## Manual smoke (to do post-commit)

1. Log in as `viewer/change-me-viewer`. Confirm: no "Crear", no
   "Edit", no "Delete", no "Tipos de operación" in nav. Direct nav to
   `/maintenance/operation-types` redirects to `/devices`.
2. Log in as `operator/change-me-operator`. Crear/Edit are visible,
   Delete is not, no opTypes nav.
3. Log in as `manager/change-me-manager`. opTypes nav visible, can
   create+delete op-types and delete maintenance log entries.
4. Log in as `admin/change-me-admin`. Everything visible.
5. User-menu shows the right username and role badge in each session.
