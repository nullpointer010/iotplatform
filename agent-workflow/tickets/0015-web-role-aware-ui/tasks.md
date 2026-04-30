# 0015 — Tasks

- [x] T1. Add `app/routes/me.py` returning `{username, sub, roles}`; wire in `main.py`.
- [x] T2. Extend `tests/test_rbac.py` with `/me` test for each seed user.
- [x] T3. Add `web/src/lib/auth.ts` (`useMe`, `useHasRole`, `assertRole`).
- [x] T4. Add `api.me()` in `web/src/lib/api.ts`; on 401, redirect to `/oauth2/sign_in?rd=...`.
- [x] T5. Add `web/src/components/gate.tsx`.
- [x] T6. Add `web/src/components/role-badge.tsx`.
- [x] T7. Update `top-nav.tsx` (gate `opTypes` link).
- [x] T8. Update `user-menu.tsx` (real username + role badge).
- [x] T9. Gate buttons in `devices/page.tsx` (create / edit / delete).
- [x] T10. Gate "Edit" button in `devices/[id]/page.tsx`.
- [x] T11. Gate maintenance log form + delete in `devices/[id]/maintenance-tab.tsx`.
- [x] T12. Add route-guard redirect to `maintenance/operation-types/page.tsx`.
- [x] T13. Add `toast.forbidden` keys to `es.json` and `en.json`.
- [x] T14. Wire `mutate.ts` to use `toast.forbidden` on 403.
- [x] T15. `web/src/lib/auth.test.tsx` — `useHasRole`, `<Gate>` tests.
- [x] T16. Run `make test`, `cd web && npm test && npx tsc --noEmit && npx next build`.
- [x] T17. Manual smoke with all 4 seed users; journal + review; commit.
