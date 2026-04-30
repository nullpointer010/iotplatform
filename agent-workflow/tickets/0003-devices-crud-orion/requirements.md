# Ticket 0003 — Devices CRUD against Orion

## Problem
Ticket 0002 pinned the data model. The API still only exposes `/healthz`.
We need the first real surface: a thin `/api/v1/devices` CRUD that proxies
to Orion using the pinned schema, plus a pytest suite covering happy and
unhappy paths so future tickets can build on a verified foundation.

## Goal
Implement `POST/GET/GET-by-id/PATCH /api/v1/devices` end-to-end against
Orion Context Broker, validated against `agent-workflow/data-model.md`,
with an integration test suite runnable via a single `make test` against
the live `make up` stack.

## User stories
- As an integrator, I want to create, read, list and partially update
  device metadata through a stable HTTP API so I can onboard sensors.
- As a developer, I want `make test` to fail fast when any device route
  regresses.

## Acceptance criteria (verifiable)
- [ ] `POST /api/v1/devices` with a valid body returns 201 and the
      created entity (URN id, all sent attributes).
- [ ] `POST` with an existing id returns 409.
- [ ] `POST` with missing required field, wrong type, unknown enum
      value, or missing protocol-required attribute returns 422.
- [ ] `GET /api/v1/devices` returns 200 with a JSON array; supports
      `limit` (1–1000, default 100) and `offset` (≥0, default 0).
- [ ] `GET /api/v1/devices?limit=…&offset=…` with bad pagination → 400.
- [ ] `GET /api/v1/devices/{id}` accepts bare UUID or URN; returns 200
      or 404.
- [ ] `PATCH /api/v1/devices/{id}` with partial body returns 200 and
      reflects updated attributes; unknown id → 404; bad payload → 422.
- [ ] All requests use `fiware-service: iot`, `fiware-servicepath: /`
      (configurable via env).
- [ ] `make test` runs a pytest suite against the running stack and
      exits non-zero on any failure.
- [ ] Tests cover, at minimum: create-good, create-bad-payload,
      create-bad-enum, create-missing-protocol-field, create-duplicate,
      get-by-uuid, get-by-urn, get-unknown, list-empty, list-paginated,
      list-bad-pagination, patch-partial, patch-unknown.
- [ ] Tests clean up entities they create (Orion direct DELETE in
      teardown) so the suite is rerunnable.

## Out of scope
- DELETE endpoint on the API (not in `backend.md`; tests delete via
  Orion directly).
- Telemetry, state, maintenance — separate tickets.
- Authentication — ticket 0009.
- Frontend — ticket 0007.

## Open questions
None blocking — recommendations from `data-model.md` are followed verbatim.