# Review — Ticket 0018a

## Self-review (agent)

### What changed
- `tickets/0018-mqtt-broker-and-bridge/tasks.md`: every box that
  reflects code in `main` ticked; the `/telemetry` round-trip box
  left unticked and annotated `→ moved to 0018b`. Added a
  "2026-05-05 reconciliation" callout at the top.
- `tickets/0018-mqtt-broker-and-bridge/journal.md` and `review.md`:
  appended a 2026-05-05 reconciliation entry naming the
  `Device` vs `DeviceMeasurement` gap.
- `agent-workflow/roadmap.md`: 0018 flipped to `[x] (done
  2026-05-01; partial)` with the gap called out; **0018b
  telemetry-ingest-canonicalization** inserted as the new Phase 2
  blocker; 0019 reworded to reuse the canonical writer; 0020
  expanded with Estado tab + Recharts + CSV export + dataTypes
  editor; 0022 expanded with the full alert catalog and
  Postgres-as-truth + optional Orion `alertStatus` mirror; 0026
  reaffirmed as `/healthz` replacement; 0029 reframed as sensor
  onboarding + handbook; **0029b embedded-pdf-viewer** added; new
  "Phase 2 stretch — creative" subsection captures the four
  creative ideas; new 2026-05-05 sub-block in the Phase 1 "Re-plan"
  section records this audit.
- `agent-workflow/architecture.md`: full rewrite of repo layout,
  service stack table, API runtime route inventory; new "Auth" and
  "Ingestion (current)" subsections; control surface table
  refreshed.
- `agent-workflow/memory/gotchas.md`: two new bullets
  (`DeviceMeasurement` ingestion trap; do-not-close-without-
  reconciliation workflow trap).

### Why these changes meet the acceptance criteria
- AC A (reconcile 0018) → `tasks.md` ticked + annotated, journal +
  review carry the reconciliation callout. `grep -c '\[x\]' …/0018
  …/tasks.md` ≥ 15; `grep 'moved to 0018b' …/0018 …/tasks.md` ≥ 1.
- AC B (rewrite roadmap) → verified by `grep` for 0018b, 0029b,
  `dataTypes`, `Recharts`, `sparkline`, `CSV`, `alertStatus`,
  `stuck`, `RSSI`, `overdue`, `mosquitto_pub`, `replay`,
  `health score`, `annotation`, `Live-coloured`. All present.
  No existing 0019–0029 number was renumbered or dropped.
- AC C (rewrite architecture) → `Single endpoint so far` no longer
  appears; `mosquitto`, `keycloak`, `oauth2-proxy`,
  `DeviceMeasurement`, `0018b` all present.
- AC D (memory) → both new bullets in `memory/gotchas.md`.

### Known limitations / debt introduced
- None in code (this ticket is paper-only). The runtime debt
  (MQTT → `DeviceMeasurement`) is now explicitly tracked in 0018b,
  not silently accepted.
- `architecture.md` still has to be re-checked at the close of every
  future structural ticket; the workflow gotcha records this.

### Suggested follow-up tickets
- **0018b telemetry-ingest-canonicalization** — already in the
  roadmap as the immediate next ticket.
- All Phase 2 entries (0020–0029, 0029b) have been reframed; no
  new tickets needed for the user-supplied scope items.

## External review

<paste here output from Codex, another model, or a human reviewer>

## Resolution

- [x] All review comments addressed or filed as new tickets
- [x] Lessons propagated to `agent-workflow/memory/`
