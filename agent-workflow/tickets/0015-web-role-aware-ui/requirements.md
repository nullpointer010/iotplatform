# 0015 — Web role-aware UI

## Problem

The API now enforces RBAC (ticket 0014). The web UI doesn't know about
the user's role: every button is rendered for everyone. A `viewer`
sees a "Create device" button, clicks it, fills the form, and gets
a 403. That's a bad experience and it leaks the existence of features
that should be invisible.

## Goal

The UI knows who the user is and what role(s) they have, then **hides**
(not disables) anything the role cannot do. Backed by belt-and-braces
guards inside the React components so a missing `if` somewhere doesn't
silently expose a button.

Test users (already seeded by Keycloak):

| User       | Password              | Role(s)               |
| ---------- | --------------------- | --------------------- |
| `viewer`   | `change-me-viewer`    | `viewer`              |
| `operator` | `change-me-operator`  | `operator`            |
| `manager`  | `change-me-manager`   | `maintenance_manager` |
| `admin`    | `change-me-admin`     | `admin`               |

## Visibility matrix (UI side)

| Element                                     | viewer | operator | manager | admin |
| ------------------------------------------- | :----: | :------: | :-----: | :---: |
| `/devices` list                             |   ✓    |    ✓     |    ✓    |   ✓   |
| "Create device" button on `/devices`        |        |    ✓     |         |   ✓   |
| "Edit" link on device detail                |        |    ✓     |         |   ✓   |
| "Delete device" button                      |        |          |         |   ✓   |
| Maintenance tab                             |   ✓    |    ✓     |    ✓    |   ✓   |
| "Add log entry" button                      |        |    ✓     |    ✓    |   ✓   |
| "Edit log entry"                            |        |    ✓     |    ✓    |   ✓   |
| "Delete log entry"                          |        |          |    ✓    |   ✓   |
| `/maintenance/operation-types` page in nav  |        |          |    ✓    |   ✓   |
| Create / edit / delete operation-type       |        |          |    ✓    |   ✓   |
| Telemetry / state tabs                      |   ✓    |    ✓     |    ✓    |   ✓   |
| User menu shows username + role badge       |   ✓    |    ✓     |    ✓    |   ✓   |
| "Sign out"                                  |   ✓    |    ✓     |    ✓    |   ✓   |

`admin` is implicitly allowed everywhere on the UI side too (matches
the API's `require_roles` semantics).

## Acceptance criteria

1. The web exposes the current user via a small read-only endpoint
   `GET /api/v1/me` that the FastAPI handler builds from the validated
   token (using ticket 0014's `Principal`). Returns
   `{ "username": str, "roles": [str] }`.
2. The web fetches `/api/v1/me` once per session via TanStack Query,
   exposes it through a `useMe()` / `useHasRole()` pair.
3. Every action gated by RBAC is **hidden** from users without the
   role. Pages that are entirely role-restricted (e.g.
   `/maintenance/operation-types` for non-managers) redirect to
   `/devices` with a soft toast rather than 403-fetching server-side.
4. Defence in depth: each component that renders a destructive button
   re-checks the role at render time **and** wraps the action in a
   guard that throws if the role is absent. Tests cover both layers.
5. If the API ever returns 401 (e.g. cookie expired), the web does a
   full reload to `/oauth2/sign_in` so Keycloak can re-issue a token.
   If it returns 403 (defence-in-depth saved the day, but a stale role
   cache slipped a button through), show a Spanish toast
   ("No tiene permisos para esta acción") and refresh `/me`.
6. The user menu shows username + a small role badge so it's obvious
   which user is logged in (helps when testing with multiple seed users).
7. Tests:
   - Vitest: `useHasRole`, `Gate` component (renders / hides), and a
     small smoke for the toast-on-403 reaction.
   - The existing API rbac suite stays green (no behavioural change
     server-side beyond `/me`).
8. Same-origin still works (no new env vars or hostnames).

## Out of scope

- Per-resource ownership rules ("operator A can edit only their own
  devices"). v1 is role-based only.
- Tenant scoping (`Fiware-Service` per user).
- Forbidden-state UI for entire pages with a custom layout — a redirect
  + toast is the v1 pattern.

## Open questions

1. **`/me` endpoint vs. parsing `X-Auth-Request-User` headers.**
   oauth2-proxy already injects identity headers (it sets
   `X-Auth-Request-User`, `X-Auth-Request-Email`, etc., and the
   `Authorization: Bearer …` header). We could read those server-side
   in a tiny Next.js route handler, *or* expose a FastAPI `/me`. The
   FastAPI route is more honest (it's the same source of truth as
   RBAC: the token itself).
   *Recommended: FastAPI `/api/v1/me`. Single source of truth.*

2. **Where to hold the role cache.** TanStack Query (existing pattern)
   or a small React Context.
   *Recommended: TanStack Query, key `["me"]`, `staleTime: 5 minutes`.
   No new state plumbing.*

3. **`Gate` component shape.**
   `<Gate roles={['operator','admin']}>{children}</Gate>` vs.
   imperative `useHasRole('operator')` and `null`.
   *Recommended: provide both — `<Gate>` for JSX, `useHasRole` for
   conditional logic and route guards.*

4. **Role badge style.** Small uppercase pill in user-menu trigger,
   colour-coded? Or plain text under the username?
   *Recommended: small lowercase pill (`viewer`, `operator`,
   `manager`, `admin`), neutral background. Matches the existing
   minimal styling.*

5. **Spanish translations for forbidden toasts.**
   *Recommended: "No tiene permisos para esta acción". Keep the
   English equivalent in `en.json` for symmetry.*

6. **Hard-fail on missing `/me`.** If the API can't be reached at
   all (e.g. cookie expired), what happens?
   *Recommended: redirect to `/oauth2/sign_in` after one failed retry
   with a 401. For 5xx / network errors, show the existing offline
   banner and treat the user as having no roles (UI is empty, no
   actions are exposed).*
