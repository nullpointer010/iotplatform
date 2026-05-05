# Journal — Ticket 0018a

## 2026-05-05
- Opened after audit revealed: 0018 closed with empty `tasks.md`,
  roadmap still listing it as TODO, `architecture.md` frozen at
  ticket 0001, and the MQTT bridge writing to `Device` while
  `/telemetry` reads `DeviceMeasurement`.
- User said "Default" to all three open questions:
  - 0018b is MQTT-only; 0019 reuses the canonical writer.
  - 0020 uses Recharts; uPlot deferred.
  - 0022 alert evaluator runs in-process inside `iot-api` for v1.
- Added a fourth resolved item: PDF embed → new ticket **0029b**
  (independent from 0029 onboarding).
- Discovered 0018's `journal.md` and `review.md` *were* filled at
  close-time — only `tasks.md` and `roadmap.md`/`architecture.md`
  were left out of date. Updated journal/review with a 2026-05-05
  reconciliation note rather than rewriting them.
- Roadmap rewrite: kept all existing numbers (0019–0029); only
  expanded bullets and inserted 0018b after 0018, 0029b after 0029,
  plus a new "Phase 2 stretch — creative" subsection.
- Architecture rewrite: full repo layout from `main`, full service
  stack table including mosquitto/keycloak/keycloak-db/oauth2-proxy,
  new "Auth" and "Ingestion (current)" subsections that explicitly
  flag the `Device` vs `DeviceMeasurement` debt and link to 0018b.

## Lessons (to propagate on close)
- → `memory/gotchas.md`: `/telemetry` reads `DeviceMeasurement`,
  not `Device` attrs. Any new ingestion path must upsert the
  matching `DeviceMeasurement` entity. *(Added.)*
- → `memory/gotchas.md`: closing a ticket without ticking its
  `tasks.md` and updating `roadmap.md`/`architecture.md` desyncs
  the workflow even if `journal.md`/`review.md` are written.
  *(Added.)*
