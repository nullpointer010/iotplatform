# Tasks — Ticket 0013 (keycloak-and-edge-auth)

- [x] T1 Add Keycloak / oauth2-proxy variables to
  `platform/.env.example` (KEYCLOAK_ADMIN, KEYCLOAK_ADMIN_PASSWORD,
  KEYCLOAK_DB_USER, KEYCLOAK_DB_PASSWORD, KEYCLOAK_DB_NAME,
  KEYCLOAK_HTTP_PORT=8081, OAUTH2_PROXY_PORT=4180,
  OAUTH2_PROXY_CLIENT_ID=iot-web, OAUTH2_PROXY_CLIENT_SECRET (dev),
  OAUTH2_PROXY_COOKIE_SECRET (empty placeholder),
  OAUTH2_PROXY_UPSTREAM=http://host.docker.internal:3000). Update local
  `platform/.env` with concrete dev values. Verify:
  `grep -c KEYCLOAK platform/.env.example` ≥ 5.
- [x] T2 Author `platform/config/keycloak/realm-iot.json` with realm
  `iot-platform`, 4 realm roles (`viewer`, `operator`,
  `maintenance_manager`, `admin`), confidential client `iot-web`
  (secret = `dev-iot-web-secret`, redirect `http://localhost:4180/oauth2/callback`,
  web origin `http://localhost:4180`), confidential client `iot-api`
  (secret = `dev-iot-api-secret`, reserved for 0014), 4 seed users
  (`viewer/operator/manager/admin`) each with email-verified +
  password `change-me-<role>` + matching realm role.
  Verify: `jq '.realm,.clients|length,.users|length' realm-iot.json`
  prints `iot-platform 2 4`.
- [x] T3 Extend `platform/compose/docker-compose.base.yml` with three
  services: `keycloak-db` (`postgres:17-alpine`, internal-only, named
  volume `keycloak_db_data`, healthcheck), `keycloak`
  (`quay.io/keycloak/keycloak:24.0.4`, `start-dev --import-realm`,
  mounts `../config/keycloak:/opt/keycloak/data/import:ro`,
  KC_HOSTNAME_URL=http://localhost:${KEYCLOAK_HTTP_PORT},
  KC_HTTP_ENABLED=true, port `127.0.0.1:${KEYCLOAK_HTTP_PORT}:8080`,
  healthcheck on `/realms/master`), and `oauth2-proxy`
  (`quay.io/oauth2-proxy/oauth2-proxy:v7.6.0`, env-driven config,
  `extra_hosts: ["host.docker.internal:host-gateway"]`, port
  `127.0.0.1:${OAUTH2_PROXY_PORT}:4180`, depends on keycloak healthy).
  Verify: `docker compose --env-file platform/.env -f
  platform/compose/docker-compose.base.yml -f
  platform/compose/docker-compose.api.yml config | grep -E
  "keycloak|oauth2-proxy"` lists all three services.
- [x] T4 Add Make targets: `secrets-keycloak` (prints the openssl
  command for `OAUTH2_PROXY_COOKIE_SECRET`), `logs-keycloak`,
  `logs-oauth2-proxy`. Verify: `make help` lists the three new
  targets.
- [x] T5 Bring stack up (`make down -v && make up`) and wait for
  Keycloak. Verify:
  `curl -fsS http://localhost:8081/realms/iot-platform/.well-known/openid-configuration | jq -r .issuer`
  prints `http://localhost:8081/realms/iot-platform`.
- [x] T6 Smoke OIDC flow: in a fresh browser session navigate to
  `http://localhost:4180/devices` (with `npm run dev` running);
  expect a redirect to Keycloak; log in as `admin/change-me-admin`;
  expect the existing devices page. Then
  `http://localhost:4180/oauth2/sign_out` clears the session.
  Verify: `curl -sI http://localhost:4180/devices` returns 302 with a
  `Location` to `localhost:8081/realms/iot-platform/...`.
- [x] T7 Run all existing automated suites unchanged: `make test`,
  `cd web && npm test`, `cd web && npx tsc --noEmit`,
  `cd web && npx next build`. Verify: all exit 0.
- [x] T8 Update `journal.md` (decisions taken, gotchas hit — at minimum
  the issuer-URL pitfall and the cookie-secret length).
- [x] T9 Fill `review.md` self-review section.
