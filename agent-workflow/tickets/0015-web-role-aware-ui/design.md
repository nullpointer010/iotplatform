# 0015 — Design

## Server side

**New route module** `app/routes/me.py`:

```python
from fastapi import APIRouter, Depends
from app.auth import Principal, get_principal

router = APIRouter()

@router.get("/me")
def me(p: Principal = Depends(get_principal)) -> dict:
    return {"username": p.username, "sub": p.sub, "roles": sorted(p.roles)}
```

Mounted under `settings.api_prefix` in `main.py`. Returns 401 when the
token is missing/invalid (because `get_principal` is the dependency)
— exactly the same trigger as every other v1 route.

No DB access, no extra deps. ~10 LoC.

## Client side

### 1. `useMe()` hook (`web/src/lib/auth.ts`)

```ts
export type Me = { username: string; sub: string; roles: string[] };

export function useMe() {
  return useQuery<Me>({
    queryKey: ["me"],
    queryFn: () => api.me(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useHasRole(...roles: string[]) {
  const { data } = useMe();
  if (!data) return false;
  if (data.roles.includes("admin")) return true; // implicit superuser
  return roles.some((r) => data.roles.includes(r));
}
```

### 2. `<Gate>` component (`web/src/components/gate.tsx`)

```tsx
export function Gate({
  roles,
  children,
  fallback = null,
}: {
  roles: string[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  return useHasRole(...roles) ? <>{children}</> : <>{fallback}</>;
}
```

Used as `<Gate roles={["operator"]}>...</Gate>`. Same matrix as the
API. `admin` is implicitly allowed via `useHasRole`.

### 3. Defence-in-depth runtime guard

`web/src/lib/auth.ts` exports `assertRole(me, ...roles)` that throws an
`Error("forbidden")` if the role is missing. Each destructive
mutation imports it. If the UI ever renders a button it shouldn't, the
mutation aborts client-side **before** hitting the server. The server
still enforces, of course (ticket 0014).

### 4. `api.me()` and the global 401/403 reaction

`web/src/lib/api.ts`:

- Add `me: () => request<Me>("/me")`.
- In `request()`, when the response is 401, do
  `window.location.href = "/oauth2/sign_in?rd=" + encodeURIComponent(window.location.pathname)`
  before throwing. The throw never reaches React because the browser
  navigates first; if it somehow does (test env, no `window`), the
  ApiError still propagates.
- 403 stays a normal `ApiError` — TanStack Query mutation hooks already
  surface it via `useMutateWithToast`, so we just add a Spanish toast
  key for "forbidden" (`toast.forbidden`).

### 5. UI changes

**`top-nav.tsx`**

- Wrap the "Tipos de operación" link in `<Gate roles={["maintenance_manager"]}>`.

**`user-menu.tsx`**

- Replace the hard-coded "Anonymous" line with `me.username` and a
  small role pill (first non-`admin` role, or `admin`).
- Falls back to "Cargando…" while `useMe` is pending.

**`devices/page.tsx`**

- Wrap the "Crear dispositivo" button (header + empty state) in
  `<Gate roles={["operator"]}>`.
- Wrap the row's edit pencil in `<Gate roles={["operator"]}>`.
- Wrap the row's trash icon in `<Gate roles={[]}>` — empty allowed-set
  means **only** admin (because `useHasRole` always returns true for
  admin). Equivalent to the API's `require_roles()` for delete.

**`devices/[id]/page.tsx`**

- Wrap the header "Edit" button in `<Gate roles={["operator"]}>`.

**`devices/[id]/maintenance-tab.tsx`**

- Wrap the `<MaintenanceLogForm>` card in
  `<Gate roles={["operator","maintenance_manager"]}>`.
- Wrap the row trash in `<Gate roles={["maintenance_manager"]}>`.

**`maintenance/operation-types/page.tsx`**

- The whole page redirects to `/devices` if
  `!useHasRole("maintenance_manager")` (after `useMe` settles).
  Implemented with a small `useRouteGuard(...roles)` hook.

### 6. User-menu role pill

A tiny `<RoleBadge role="operator" />` component using the existing
`Badge` UI primitive (variants: `secondary` for viewer, `default` for
operator, `warning` for manager, `success` for admin).

## Test plan

**Web (vitest, `web/src/lib/auth.test.tsx`)**

- `useHasRole("operator")` returns `false` for a viewer, `true` for an
  operator, `true` for an admin (implicit).
- `<Gate roles={["operator"]}>` renders children for an operator,
  hides them for a viewer, shows fallback when provided.
- `useHasRole()` (empty allowed) is `false` for everyone except admin.

We mock `useMe()` by seeding the React Query cache with a `["me"]`
key in a small test wrapper.

**API (existing rbac suite)**

- Add a single test `test_me_returns_username_and_roles` to
  `test_rbac.py` (200 with each seed user, role list matches).

## Non-goals

- Per-resource ownership.
- Tenant scoping.
- Backend logout to Keycloak SSO (separate follow-up).

## Risks

- TanStack Query default retry is already disabled in providers
  (`retry: false`). The 401 redirect happens once and is a hard
  navigation, so React Query's cached state for that page is gone
  before any retry could fire.
- A user whose role is removed in Keycloak mid-session keeps the cached
  `["me"]` for up to 5 minutes. This is acceptable for the IoT
  platform (no destructive blast radius client-side; the API still
  rejects). If needed later, drop staleTime to 30s.
- Defence-in-depth `assertRole` is informational only — the API is the
  source of truth. We do **not** rely on it for security.
