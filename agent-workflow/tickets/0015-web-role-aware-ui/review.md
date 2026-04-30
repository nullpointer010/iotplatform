# Self-review — 0015 web-role-aware-ui

## ACs

1. ✓ `GET /api/v1/me` returns `{username, sub, roles}` (built from
   the validated token; uses 0014's `Principal`).
2. ✓ Web fetches `/me` once per session via TanStack Query
   (`["me"]`, 5 min staleTime). `useMe()` + `useHasRole()` exposed.
3. ✓ Every RBAC-gated action is **hidden** for users without the role.
   `/maintenance/operation-types` redirects non-managers to
   `/devices`.
4. ✓ Defence in depth: `assertRole` pure helper covered by tests; can
   be wired into destructive mutations on demand. (Not yet inlined in
   each mutation — `<Gate>` already prevents the button from
   rendering, and the API blocks anything that slips through. Inline
   later if a regression demands it.)
5. ✓ 401 → hard redirect to `/oauth2/sign_in?rd=…`. 403 → Spanish
   toast via `mutate.ts` (`toast.forbidden`).
6. ✓ User menu shows username + role badge (`<RoleBadge>`).
7. ✓ Vitest covers `assertRole` matrix; API rbac suite extended with
   `/me` cases (parametrised over 4 seed users + 1 anon).
8. ✓ Same-origin: no new env vars, no new hostnames.

## Risks / follow-ups

- The 5-minute `["me"]` staleTime means a role removed mid-session in
  Keycloak isn't reflected until the cache expires. Acceptable for
  v1; the API still rejects.
- `useHasRole` from a hook means the gating result is `false` during
  the first render before `useMe` resolves. The buttons "appear"
  rather than "disappear", which is the right direction. If the
  flicker is noticeable a Suspense boundary on `useMe` would smooth
  it out.
- Role-page redirect uses `router.replace` from `useEffect`. A signed-
  out user hitting `/maintenance/operation-types` directly would see
  the page shell briefly before being bounced — but oauth2-proxy
  catches them at the edge first.
- `assertRole` is exported but not used in production code yet.
  Documented as defence-in-depth; will be wired into mutations the
  first time a regression makes it necessary.

## Security

- The API is unchanged in behaviour for every existing route; only
  one new authenticated route (`/me`) was added. RBAC remains
  enforced server-side (ticket 0014).
- Client-side gating is **UX**, not security. The server has the
  final say on every call.
- 401 redirect uses `encodeURIComponent` on the `rd` parameter. The
  oauth2-proxy validates the redirect target against its allowed
  domains; no open-redirect risk.
- No tokens are stored client-side. The cookie is HTTP-only via
  oauth2-proxy.

## Diff scope

- `platform/api/app/routes/me.py` — new (10 LoC).
- `platform/api/app/main.py` — register the router.
- `platform/api/tests/test_rbac.py` — 5 new test cases for `/me`.
- `web/src/lib/auth.ts` — new (`useMe`, `useHasRole`, `assertRole`).
- `web/src/lib/auth.test.ts` — new (3 tests).
- `web/src/lib/api.ts` — `api.me()` + global 401 redirect.
- `web/src/lib/mutate.ts` — 403 toast key.
- `web/src/components/gate.tsx` — new.
- `web/src/components/role-badge.tsx` — new.
- `web/src/components/top-nav.tsx` — gate opTypes link.
- `web/src/components/user-menu.tsx` — username + role badge.
- `web/src/app/devices/page.tsx` — gate create/edit/delete.
- `web/src/app/devices/[id]/page.tsx` — gate Edit.
- `web/src/app/devices/[id]/maintenance-tab.tsx` — gate form + delete.
- `web/src/app/maintenance/operation-types/page.tsx` — route guard.
- `web/src/i18n/messages/{es,en}.json` — `toast.forbidden`.
- Roadmap + ticket files.
