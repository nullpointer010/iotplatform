# Tasks — 0013b single-origin edge

- [x] T1. Drop `ports:` from `iot-api` in `platform/compose/docker-compose.api.yml`.
- [x] T2. Move oauth2-proxy to `${WEB_PORT:-80}:4180` and update `OAUTH2_PROXY_REDIRECT_URL` + `OAUTH2_PROXY_UPSTREAMS` (api first, then Next.js); add `depends_on: api`.
- [x] T3. Update realm `iot-web` `redirectUris` and `webOrigins` to `http://localhost`.
- [x] T4. Update `platform/.env.example` + `platform/.env`: drop `API_PORT` / `OAUTH2_PROXY_PORT`, add `WEB_PORT=80`. Comment block explaining no host port for API.
- [x] T5. Update `web/.env.local.example`: `NEXT_PUBLIC_API_BASE_URL=` (empty). Update `web/src/lib/api.ts` default to `""`.
- [x] T6. Flip API `cors_allow_origins` default to `""`.
- [x] T7. `make down` + delete `keycloak_db_data` volume + `make up`. Verify: API has no host port, `curl -I http://localhost/api/v1/devices` from no-session shell redirects to Keycloak, post-login `/api/v1/devices` returns JSON same-origin.
- [x] T8. Run `make test`, `cd web && npm test`, `npx tsc --noEmit`, `npx next build`.
- [x] T9. Journal + review + flip status to done + tick roadmap + commit.
