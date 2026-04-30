# Review — Ticket 0013 (keycloak-and-edge-auth)

## Self-review (agent)

### What changed
- New `platform/config/keycloak/realm-iot.json` — realm with 4 roles
  (`viewer`, `operator`, `maintenance_manager`, `admin`), 2 clients
  (`iot-web` confidential w/ dev secret, `iot-api` bearer-only), 4 seed
  users (`viewer/operator/manager/admin`, password
  `change-me-<role>`).
- `platform/compose/docker-compose.base.yml` — added 3 services
  (`keycloak-db`, `keycloak`, `oauth2-proxy`) and the
  `keycloak_db_data` volume. All bound to `127.0.0.1` only.
- `platform/.env.example` + local `platform/.env` — new
  Keycloak/oauth2-proxy variables. Cookie secret generated for the
  local `.env` only (gitignored).
- `Makefile` — `secrets-keycloak`, `logs-keycloak`,
  `logs-oauth2-proxy` targets.

### Why these changes meet the acceptance criteria
- AC compose services / make targets → confirmed by
  `docker compose ... config | grep` listing the three services and
  `make help` listing the new targets.
- AC realm import → `make up` brings Keycloak healthy on first try;
  `curl http://localhost:8081/realms/iot-platform/.well-known/openid-configuration`
  returns issuer `http://localhost:8081/realms/iot-platform`.
- AC oauth2-proxy redirect → `curl -I http://localhost:4180/devices`
  returns `302` to the Keycloak `auth` endpoint with
  `client_id=iot-web` and the redirect URI pre-filled.
- AC bare `:3000` still open → unchanged; documented in journal as
  intentional, locking it down is 0014/0015 scope.
- AC quality gates → `make test` 80/80 green; `cd web && npm test` 2/2
  green; `npx tsc --noEmit` clean; `npx next build` 7/7 routes.

### Known limitations / debt introduced
- The dev-only client secrets (`dev-iot-web-secret`,
  `dev-iot-api-secret`) live in `realm-iot.json` in the repo. Acceptable
  for local dev; production must rotate these or use a different
  provisioning path.
- `KEYCLOAK_ADMIN_PASSWORD=change-me-admin` and seed user passwords
  live in `.env.example`. Local-only. No prod hardening here.
- `OAUTH2_PROXY_COOKIE_SECURE=false` because dev has no TLS.
- The bare `:3000` Next.js port is still open. Locking it down (or
  Dockerising the web app behind oauth2-proxy) is deferred — 0015
  will revisit.
- `KC_HOSTNAME_STRICT=false` is permissive. Production should use
  `start` (not `start-dev`) and tighten this.

### Suggested follow-up tickets
- 0014 backend-jwt-rbac (already in roadmap).
- 0015 web-role-aware-ui (already in roadmap).
- A hardening ticket later: rotate dev secrets, switch to Keycloak
  `start`, set `KC_HOSTNAME_STRICT=true`, TLS at the edge.

## External review

<paste here output from Codex, another model, or a human reviewer>

## Resolution

- [ ] All review comments addressed or filed as new tickets
- [ ] Lessons propagated to `agent-workflow/memory/`
