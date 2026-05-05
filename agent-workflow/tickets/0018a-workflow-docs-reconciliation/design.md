# Design — Ticket 0018a

## Approach

Pure documentation/metadata ticket. Five mechanical edits, no runtime
code touched. Order matters only to keep the workspace internally
consistent at every step:

1. **Reconcile ticket 0018** — read the actual code in `main`
   (`mqtt_bridge.py`, `mqtt_payload.py`, `routes/system.py`,
   `compose/docker-compose.base.yml`, `config/mosquitto/`,
   `tests/test_mqtt_*.py`) and tick the corresponding boxes in
   `tickets/0018-mqtt-broker-and-bridge/tasks.md`. Leave the
   `/telemetry` round-trip task unticked, annotated
   `→ moved to 0018b`. Add a journal entry and a self-review
   summarising what shipped, what did not, and the
   `Device` vs `DeviceMeasurement` gap.

2. **Rewrite `roadmap.md`** — flip 0018 to `[x]` with a one-paragraph
   "what shipped / what did not" summary; insert **0018b
   telemetry-ingest-canonicalization** as the new Phase 2 blocker;
   rewrite 0019–0029 in place to absorb every user-supplied item
   (dataTypes editor in 0020, full alert catalog in 0022, sensor
   onboarding flow in 0029, etc.); add **0029b embedded-pdf-viewer**;
   add a "Phase 2 stretch — creative" subsection with the four
   creative ideas; append a `2026-05-05` sub-block to the existing
   "Re-plan" record pointing at 0018a.

3. **Rewrite `architecture.md`** — replace the ticket-0001-era repo
   layout, service stack table and "API runtime" section with what
   actually ships in `main` (Mosquitto, Keycloak, keycloak-db,
   oauth2-proxy, manuals volume, full route list). Add an "Auth"
   subsection and an "Ingestion (current)" subsection that records
   the `Device`-only MQTT bridge as known debt with a link to 0018b.

4. **Append two entries to `memory/gotchas.md`** — the
   `DeviceMeasurement` ingestion trap and the
   "do-not-close-without-reconciliation" workflow trap.

5. **Close 0018a** — fill `journal.md` and `review.md`, flip
   `status.md` to `done`.

The whole ticket is reversible via `git restore` and introduces no
runtime risk. The only judgement call is *what* to write, not *how*
to make it work.

## Alternatives considered

- **A)** Reopen ticket 0018 and amend it in place — rejected because
  the workflow's "one ticket at a time, distill on close" rule would
  be muddied: 0018 already has a `closed:` date. Cleaner to leave
  0018 as a historical record, fix its paper trail, and split the
  runtime fix into 0018b.
- **B)** Skip the doc reconciliation and jump straight to 0018b —
  rejected because the next agent session would still plan from a
  stale roadmap and a stale architecture diagram, and the
  user-supplied scope items would silently drop on the floor.
- **C)** Fold the architecture rewrite into a separate doc-only
  ticket — rejected as overhead; same root cause, same fix window.

## Affected files / new files

- `agent-workflow/tickets/0018-mqtt-broker-and-bridge/tasks.md`
- `agent-workflow/tickets/0018-mqtt-broker-and-bridge/journal.md`
- `agent-workflow/tickets/0018-mqtt-broker-and-bridge/review.md`
- `agent-workflow/roadmap.md`
- `agent-workflow/architecture.md`
- `agent-workflow/memory/gotchas.md`
- `agent-workflow/tickets/0018a-workflow-docs-reconciliation/{journal,review,tasks,status}.md`

No code, no tests, no compose, no `Makefile` changes.

## Data model / API contract changes

None.

## Risks

- **Risk:** roadmap rewrite drops a numbered ticket. **Mitigation:**
  keep all existing numbers; only *expand* their bullet text; add new
  entries (0018b, 0029b) as inserts, never as renumberings.
- **Risk:** architecture drifts again. **Mitigation:** record as a
  gotcha so future tickets remember to update `architecture.md` in
  their own `tasks.md`.
- **Risk:** user disagrees with a resolved default. **Mitigation:**
  defaults are recorded in `requirements.md` for easy revision.

## Test strategy for this ticket

- Unit: none.
- Integration: none.
- Manual verification:
  - `git diff --stat agent-workflow/` shows changes only under
    `agent-workflow/` and only in the listed files.
  - `grep -n '0018b' agent-workflow/roadmap.md` ≥ 1 hit; same for
    `0029b`.
  - `grep -nE '^\- \[ \] \*\*0018 ' agent-workflow/roadmap.md` returns
    nothing.
  - Each user-supplied keyword is searchable in `roadmap.md`:
    `dataTypes`, `Recharts`, `mosquitto_pub`, `alertStatus`,
    `replay`, `health score`, `annotation`, embedded PDF viewer.
  - 0018 `tasks.md` shows ticked boxes for delivered items and the
    `→ moved to 0018b` annotation on the telemetry round-trip task.
