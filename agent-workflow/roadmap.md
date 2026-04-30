# Roadmap

Tickets are processed in order unless re-prioritized. Only one ticket is
`in-progress` at any time. Stubs below are intentionally short until promoted
to active.

## Phase 1 — Foundation

- [ ] **0001 platform-skeleton-audit** — *(active, planning)*
  Decide canonical repo layout for `platform/`, stand up a minimal Compose
  stack that boots, expose it through a top-level `Makefile`. Keep
  `context/platform/` as historical reference.

- [ ] **0002 device-document-upload** — *(TODO)*
  Vertical slice: a minimal device entity plus the ability to upload, list
  and download a PDF manual attached to a sensor. This is intentionally a
  thin end-to-end feature (no full device CRUD yet), chosen to exercise:
  - the API layer (FastAPI route, multipart upload),
  - persistence of the device record,
  - object storage for the file (decision deferred to design: filesystem
    volume vs. early MinIO),
  - basic acceptance test.
  Acts as the seed on which 0003 (testing) and the rest of the device API
  will grow.

- [ ] **0003 testing-infrastructure** — *(TODO)*
  Hard-gate testing setup. Goals:
  - All tests must pass for the build/image to be considered valid; failing
    tests must break `make build` / CI.
  - Tests run against ephemeral Docker dependencies (Postgres, CrateDB,
    Orion+MongoDB) spun up per test session via `testcontainers-python`,
    in the spirit of `crop-edc/connector`'s `PostgresTestcontainer` pattern.
  - Seed a minimal fake-data dataset (devices, telemetry samples, one PDF
    manual) and exercise the endpoints created up to 0002 against it.
  - Pre-commit hook + `make test` target.
  Tickets 0001 and 0002 will be retroactively brought under this gate.

- [ ] **0004 web-ui-skeleton** — *(TODO)*
  Minimal frontend application under a top-level `web/` folder.
  - Stack aligned with `/home/maru/crop-edc/frontend`: Next.js 14+,
    TypeScript, Tailwind, Radix UI, react-hook-form, Zod.
  - Visual identity aligned with `/home/maru/cropweb` palette
    (`--color-crop-dark #2E5945`, `--color-crop-olive #394022`,
    `--color-crop-lime #D0D98F`, `--color-crop-light #F2F2F2`).
  - First screen: list of devices and "upload manual" action backed by 0002.
  - Test setup mirrors 0003: Jest unit tests + at least one integration test
    that boots the API against ephemeral Docker dependencies, similar to the
    testcontainers pattern used by `crop-edc/connector`.

## Phase 1 — Backend completion (tentative, after the slice above)

- [ ] **0005 devices-crud-api** — full `GET/POST/GET-by-id/PATCH /api/v1/devices`
  against Orion Context Broker. *(TODO)*
- [ ] **0006 telemetry-query-api** — `GET /api/v1/devices/{id}/telemetry` via
  QuantumLeap + CrateDB. *(TODO)*
- [ ] **0007 maintenance-log-api** — maintenance endpoints against Postgres.
  *(TODO)*
- [ ] **0008 keycloak-integration** — Keycloak service + JWT middleware +
  RBAC on existing endpoints. *(TODO)*

## Phase 2+ — Later

Phase 2 (MQTT ingestion, realtime), Phase 3 (Superset, H2O, Node-RED, NiFi,
Airflow, MinIO at scale, Prometheus/Grafana) and operations (Kubernetes) are
out of scope for now and will be expanded once Phase 1 is closed.
