# Journal — 0013b single-origin edge

## Decisions

- **One front door at `:80`.** oauth2-proxy holds the only host-facing port
  for the app. `iot-api` lost its `ports:` mapping; it is reachable only
  on `iot-net` (`http://iot-api:8000`). No more CORS friction; same-origin
  fetches throughout the web UI.
- **Single override knob `WEB_PORT`** (default 80). `API_PORT` and
  `OAUTH2_PROXY_PORT` are gone. If port 80 is busy on the host the user
  flips one variable.
- **Keycloak realm tracked in repo** is the source of truth. Updating
  `redirectUris` / `webOrigins` required dropping `compose_keycloak_db_data`
  once so `--import-realm` would re-seed cleanly. Documented as the dev
  workflow for any future realm change.
- **`OAUTH2_PROXY_REDIRECT_URL` is a literal `http://localhost/...`** (no
  `${WEB_PORT}` interpolation). Reason: Keycloak requires the redirect URI
  in the auth request to match a `redirectUris` entry exactly; with
  `${WEB_PORT}=80` the proxy was emitting `http://localhost:80/...` which
  did not match the realm's `http://localhost/...`. If a developer
  overrides `WEB_PORT`, they must also update the realm and this URL.

## Bug rolled in (carry-over from 0013)

- `OAUTH2_PROXY_OIDC_AUDIENCE_CLAIMS=azp`. Keycloak access tokens omit
  `aud` for the requesting client and use `azp` instead; oauth2-proxy v7
  500s during callback otherwise. Already added in compose; this commit
  formalizes it.

## Lessons

- A multi-origin dev stack ages badly. Every cross-origin step costs CORS
  config, token-forwarding plumbing, and confusion. Default to one origin
  + reverse proxy from day one.
- `${VAR}` interpolation in URL fragments is a footgun when the value
  is the default port for the scheme — `:80` is not the same string as
  empty for OIDC redirect-URI matching.
- `docker compose down` keeps named volumes by default. To re-seed
  Keycloak with realm-import changes, drop the volume explicitly.
- Pre-existing flake in `tests/test_telemetry.py::test_query_lastN_limits_results`
  surfaces ~1/3 runs (Orion → QL ingest race). Out of scope here; logged.

## Verification

- `docker ps` — `iot-api` shows only `8000/tcp` (no host port). ✓
- `curl -m 2 http://localhost:8000/...` from host — connection refused. ✓
- `curl -I http://localhost/api/v1/devices` no session — 302 to Keycloak,
  `redirect_uri=http%3A%2F%2Flocalhost%2Foauth2%2Fcallback`. ✓
- Full OIDC flow via `curl` cookie jar: login form fetched, credentials
  POSTed, callback consumed, `GET /api/v1/devices` returns the seed JSON
  array. Same-origin, no preflight. ✓
- `cd web && npm test` 2/2 · `tsc --noEmit` clean · `next build` 7/7
  routes. ✓
- `make test` 79/80 (one pre-existing flake passes on retry).
