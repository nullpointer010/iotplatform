# Ticket 0001 — Platform skeleton audit

## Problem
`context/platform/` contains a draft Docker Compose stack (CrateDB, Orion,
MongoDB, QuantumLeap, PostgreSQL) plus a minimal FastAPI app with two dummy
routes. It is a reference draft, not a contract: pinned image versions may be
stale, the layout may not match what later tickets need, and there is no
top-level `platform/` folder yet.

Until we decide whether to (a) promote this draft as-is, (b) restructure it,
or (c) replace it, no other ticket can write code without risk of throwaway
work.

## Goal
Decide and document the canonical repository layout for the platform code,
then create the minimal skeleton at the top level so `docker compose up` boots
a working API container against the documented stack.

## User stories
- As a developer, I want a single `platform/` folder I can `cd` into and run
  `docker compose ... up`, so that I have a reproducible local environment.
- As the agent, I want `agent-workflow/architecture.md` to describe the chosen
  layout, so that subsequent tickets have a stable foundation.

## Acceptance criteria
- [ ] `agent-workflow/architecture.md` describes the chosen repository layout
      and the rationale (kept-as-is / restructured / replaced).
- [ ] The repository has a top-level `platform/` directory containing the
      agreed skeleton (Compose files, `api/` source, `.env.example`).
- [ ] A top-level `Makefile` exposes at minimum: `make up`, `make down`,
      `make logs`, `make ps`. Bootstrap logic that previously lived in
      `bootstrap.sh` is folded into Make targets; the shell script is
      removed from the new `platform/`.
- [ ] `make up` brings up all services without errors on a clean machine
      with Docker installed.
- [ ] `curl http://localhost/dummy` returns HTTP 200 with a JSON body.
- [ ] `context/platform/` is preserved untouched as a historical reference;
      a short note in `context/README.md` (or `context/platform/README.md`)
      states it is frozen and points to `platform/`.
- [ ] All Compose service images are pinned to the latest stable version
      available as of 2026-04 (CrateDB, FIWARE Orion, QuantumLeap, MongoDB,
      PostgreSQL). Chosen versions are recorded in `journal.md`.
- [ ] No business endpoints (devices, telemetry, maintenance) are added —
      those are deferred to later tickets.

## Out of scope
- Real `/api/v1/devices` endpoints (ticket 0003).
- Authentication and Keycloak (ticket 0006).
- Telemetry and maintenance endpoints (tickets 0004, 0005).
- Kubernetes deployment.
- Pinning new image versions beyond what is necessary to make the stack boot.

## Resolved questions (user answers, 2026-04-30)
- **Q1.** Keep `context/platform/` untouched as historical reference. Do not
  delete.
- **Q2.** Bump every image to its latest stable version as of 2026-04.
  Record exact tags in `journal.md` once selected during the design phase.
- **Q3.** Replace `bootstrap.sh` with a top-level `Makefile`. The Makefile is
  the only sanctioned entry point for the dev stack.

## Open questions
- None blocking approval. Any new question discovered during design goes into
  `design.md`.
