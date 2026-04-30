# Tasks — 0014 backend JWT + RBAC

- [x] T1. Add `pyjwt[crypto]` to `platform/api/requirements.txt`.
- [x] T2. Create `platform/api/app/auth.py` with `Principal`, `get_principal`, `require_roles`.
- [x] T3. Extend `app/config.py` with `keycloak_issuer`, `keycloak_jwks_url`, `keycloak_client_id`, `auth_disabled` (default false).
- [x] T4. Inject the three KEYCLOAK_* env vars into `iot-api` (compose) and add `depends_on: keycloak (healthy)`.
- [x] T5. Apply `Depends(require_roles(...))` to every route in `devices.py`, `telemetry.py`, `maintenance.py` per the matrix.
- [x] T6. Realm: flip `iot-web.directAccessGrantsEnabled` to `true`.
- [x] T7. Add `tests/_tokens.py` helper. Update `conftest.py` so the `api` fixture carries an admin token.
- [x] T8. Write `tests/test_rbac.py`: 401/403/200 on devices, telemetry, state, operation-types, maintenance/log.
- [x] T9. `make down` + drop `compose_keycloak_db_data` + `make up`.
- [x] T10. `make test` green; web smoke (login → /devices renders); `npx tsc --noEmit`; `npx next build`.
- [x] T11. Journal + review + flip status to done + tick roadmap + commit.
