# Tasks — Ticket 0018a

Each task ends with a **verify** clause. No runtime code is touched
in this ticket; verification is `grep`/file inspection.

## 1. Reconcile ticket 0018
- [x] T1 Tick the boxes in
      `tickets/0018-mqtt-broker-and-bridge/tasks.md` whose code is in
      `main`; leave the telemetry round-trip task unticked and
      annotate `→ moved to 0018b` — verify:
      `grep -c '\[x\]' agent-workflow/tickets/0018-mqtt-broker-and-bridge/tasks.md`
      ≥ 15 and `grep -n 'moved to 0018b' agent-workflow/tickets/0018-mqtt-broker-and-bridge/tasks.md`
      ≥ 1 hit.
- [x] T2 Add a `2026-05-05` reconciliation entry to
      `tickets/0018-mqtt-broker-and-bridge/journal.md` summarising
      what shipped, what did not, and the
      `Device` vs `DeviceMeasurement` gap — verify:
      `grep -n '2026-05-05' agent-workflow/tickets/0018-mqtt-broker-and-bridge/journal.md`
      ≥ 1 hit.
- [x] T3 Fill the self-review in
      `tickets/0018-mqtt-broker-and-bridge/review.md` (what changed,
      partial-AC reality, debt, follow-up = 0018b) — verify:
      `grep -n '0018b' agent-workflow/tickets/0018-mqtt-broker-and-bridge/review.md`
      ≥ 1 hit.

## 2. Rewrite `roadmap.md`
- [x] T4 Flip 0018 to `[x] (done 2026-05-01)` with a "what shipped /
      what did not" paragraph naming the `DeviceMeasurement` gap —
      verify: `grep -nE '^\- \[x\] \*\*0018 ' agent-workflow/roadmap.md`
      ≥ 1 hit and
      `grep -nE '^\- \[ \] \*\*0018 ' agent-workflow/roadmap.md` = 0.
- [x] T5 Insert **0018b telemetry-ingest-canonicalization** right
      after 0018 as the Phase 2 blocker — verify:
      `grep -n '0018b telemetry-ingest-canonicalization' agent-workflow/roadmap.md`
      ≥ 1 hit.
- [x] T6 Expand 0020 to require Estado tab (freshness +
      sparkline + 5–30 s polling), Recharts charts (24 h / 7 d / 30 d
      + attribute selector + units + CSV export), and dataTypes
      editor in the device form's MQTT section — verify:
      `grep -n -E 'dataTypes|Recharts|sparkline|CSV' agent-workflow/roadmap.md`
      hits all four keywords.
- [x] T7 Expand 0022 to state Postgres-as-truth + optional
      `alertStatus`/`activeAlertCount` mirror in Orion, and list the
      catalog (no-data, threshold, delta, stuck, battery, RSSI,
      payload errors, overdue maintenance) — verify:
      `grep -n -E 'alertStatus|stuck|RSSI|overdue' agent-workflow/roadmap.md`
      hits all four.
- [x] T8 Reframe 0029 as sensor onboarding (credentials, topic,
      sample `mosquitto_pub`, payload-test) plus operator docs —
      verify: `grep -n 'mosquitto_pub' agent-workflow/roadmap.md` ≥ 1.
- [x] T9 Add **0029b embedded-pdf-viewer** — verify:
      `grep -n '0029b embedded-pdf-viewer' agent-workflow/roadmap.md`
      ≥ 1 hit.
- [x] T10 Add "Phase 2 stretch — creative" subsection with the four
      creative ideas — verify:
      `grep -n -E 'replay|health score|annotation|live-coloured' agent-workflow/roadmap.md`
      hits all four.
- [x] T11 Append a `2026-05-05` sub-block to the Phase 1 "Re-plan"
      section pointing at 0018a — verify:
      `grep -n '2026-05-05' agent-workflow/roadmap.md` ≥ 1 hit.

## 3. Rewrite `architecture.md`
- [x] T12 Replace ticket-0001-era repo layout, service stack table
      and "API runtime" section with the real ones; add Auth and
      Ingestion (current) subsections — verify:
      `grep -n 'Single endpoint so far' agent-workflow/architecture.md`
      = 0 and
      `grep -n -E 'mosquitto|keycloak|oauth2-proxy|DeviceMeasurement|0018b' agent-workflow/architecture.md`
      hits all five.

## 4. Memory
- [x] T13 Append two new bullets to
      `agent-workflow/memory/gotchas.md` (DeviceMeasurement trap +
      do-not-close-without-reconciliation) — verify:
      `grep -n -E 'DeviceMeasurement|reconciliation' agent-workflow/memory/gotchas.md`
      hits both.

## 5. Close 0018a
- [x] T14 Fill `journal.md` with decisions/lessons.
- [x] T15 Fill `review.md` self-review section.
- [x] T16 Flip `status.md` to `done` and set `closed:` date —
      verify: `head -1 agent-workflow/tickets/0018a-workflow-docs-reconciliation/status.md`
      shows `status: done`.
