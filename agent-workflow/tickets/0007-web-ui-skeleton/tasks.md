# Tasks

- [x] FastAPI: add CORS middleware (settings + main.py).
- [x] Scaffold `web/` (package.json, tsconfig, tailwind, postcss, next config, .env example, .gitignore).
- [x] Add `globals.css` with crop palette + tailwind layers.
- [x] Build shadcn-style UI primitives (button, input, label, table, dialog, dropdown-menu, select, tabs, toast, badge, card, textarea).
- [x] Build top-nav + user-menu + logo.
- [x] API client + types + zod schemas.
- [x] Pages: dashboard, devices list/new/edit/detail, operation types.
- [x] React Query provider, Toast provider.
- [x] Run `npm install` + `npm run build` smoke check.
- [x] `make test` still 75/75.
- [x] Fill journal/review; flip status=done; update roadmap; commit + push.

Out of scope (added during implementation, surfaced to user):

- [x] Backend `DELETE /devices/{id}` route + `OrionClient.delete_entity` —
  required to wire the UI delete button. Cascade-removes associated
  `maintenance_log` rows. Not covered by automated tests in this ticket;
  manual smoke test only.
