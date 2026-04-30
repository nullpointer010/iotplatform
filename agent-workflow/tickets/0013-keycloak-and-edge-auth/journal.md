# Journal — Ticket 0013 (keycloak-and-edge-auth)

## 2026-04-30
- Decision: single compose file (`docker-compose.base.yml` extension)
  rather than a separate `docker-compose.auth.yml`. One stack, one
  command.
- Decision: `iot-web` is a **confidential** OIDC client with a dev-only
  secret (`dev-iot-web-secret`) committed to `realm-iot.json`.
  oauth2-proxy refuses empty client secrets even for public clients.
- Decision: `iot-api` client also created in this ticket as
  `bearerOnly` so 0014 can land without re-importing the realm.
- Decision: Keycloak host port `127.0.0.1:8081` (8080 frequently busy).
- Decision: oauth2-proxy uses the canonical issuer-URL split: browser-
  facing `OAUTH2_PROXY_OIDC_ISSUER_URL=http://localhost:8081/...` paired
  with `OAUTH2_PROXY_REDEEM_URL` and `OAUTH2_PROXY_OIDC_JWKS_URL`
  pointing at the in-network `http://keycloak:8080/...`. Required
  `OAUTH2_PROXY_SKIP_OIDC_DISCOVERY=true` so the proxy does not try to
  re-discover the issuer at startup (otherwise the in-network Keycloak
  serves an issuer claim of `http://keycloak:8080`, which fails the
  validation against the browser-facing one).
- Decision: `KC_HOSTNAME_URL=http://localhost:8081` so issued tokens
  carry the externally-visible issuer.
- Decision: `--reverse-proxy=true` on oauth2-proxy + `--cookie-secure=
  false` for local dev (no TLS).
- Surprise: Keycloak 24's healthcheck has no curl/wget in the image.
  Used a bash `/dev/tcp` probe against `/realms/master` instead. Works.
- Surprise: `make up` recreated `iot-api` because the compose file
  changed; this is harmless (no schema migration) but worth noting.

## Lessons (to propagate on close)
- → `memory/patterns.md`: For oauth2-proxy + Keycloak in Docker,
  always set the **browser-facing** issuer URL on the proxy AND the
  **in-network** redeem/JWKS URLs separately, with
  `--skip-oidc-discovery=true`. Without this the issuer claim
  validation fails because the in-network discovery doc reports a
  different issuer than the one the browser sees.
- → `memory/patterns.md`: Use `KC_HOSTNAME_URL=http://localhost:<port>`
  on Keycloak so the realm OIDC discovery reports the externally
  reachable issuer, even when the proxy talks to it on its in-network
  hostname.
- → `memory/gotchas.md`: Keycloak 24 image has no `curl` or `wget`;
  use bash `exec 3<>/dev/tcp/...` for the healthcheck.
- → `memory/gotchas.md`: oauth2-proxy refuses empty client secrets
  even when the OIDC client is "public" — register the client as
  confidential with a dev-only secret.
- → `memory/glossary.md`: "edge auth" = oauth2-proxy in front of the
  app, terminating the OIDC dance and forwarding identity headers.
