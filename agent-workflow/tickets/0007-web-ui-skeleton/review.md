# Self-review

| AC | Description | Status |
|----|-------------|--------|
| 1  | `web/` builds with `npm run build` (Next.js production build, no TS errors) | PASS |
| 2  | Backend regression: `make test` 75/75 | PASS (after 1 retry on known telemetry flake) |
| 3  | Crop palette wired (HSL tokens + Tailwind crop colors) | PASS |
| 4  | Top-nav with logo + user menu (logout placeholder) | PASS |
| 5  | Dashboard with device/op-type counts | PASS |
| 6  | Devices: list / create / view / edit / delete with confirmation | PASS |
| 7  | Device detail tabs: overview, telemetry (lastN), maintenance log CRUD | PASS |
| 8  | Operation types: list / create / edit / delete | PASS |
| 9  | Form validation via Zod with friendly error messages | PASS |
| 10 | Toast feedback on success/error | PASS |
| 11 | API errors surface FastAPI 422 detail strings | PASS |

## Scope deviations

- Added `DELETE /devices/{id}` and `OrionClient.delete_entity` to make
  the UI delete button functional. Cascades the device's
  `maintenance_log` rows. Documented in `tasks.md` and `journal.md`.
- Added `cors_allow_origins` setting and `CORSMiddleware`. Default
  `http://localhost:3000` only — no credentials.

## Known gaps / follow-ups

- No automated test coverage for the new DELETE route or CORS config.
  Pick up with 0009 (auth) since both endpoints need to be authorized
  there anyway.
- No e2e tests for the UI (Playwright was not in scope). Future ticket.
- Real auth is intentionally absent — handled by 0009.

## External review
