# Ticket 0002 — Data model decision

## Problem
`context/doc/backend.md` describes the platform's domain in prose (devices,
telemetry, maintenance) and gives a JSON shape for device metadata, but it
leaves several engineering decisions open:

- Whether to adopt FIWARE Smart Data Models verbatim, ignore them, or align
  field names while keeping the schema flat.
- Exact NGSI v2 attribute types (`Text`, `Number`, `geo:point`, `DateTime`,
  `StructuredValue`) for each field.
- How telemetry attributes are named so QuantumLeap auto-creates clean
  CrateDB tables.
- How to scale CrateDB to billions of measurement rows (partitioning,
  retention) and which path the API uses to query telemetry (QuantumLeap
  REST vs. raw CrateDB SQL).

If we build endpoints (0003+) before pinning these, every feature ticket
will re-litigate the same decisions and any change will force schema
rewrites in Orion + CrateDB.

## Goal
Produce `agent-workflow/data-model.md` — a single, authoritative document
that pins the data model and storage strategy for the rest of Phase 1.
**No code changes in this ticket.**

## User stories
- As an implementer, I want a single page I can open and copy attribute
  names from when I write the devices CRUD route.
- As a reviewer, I want to verify that any new endpoint uses the pinned
  field names and types before I approve it.

## Acceptance criteria (verifiable)
- [ ] `agent-workflow/data-model.md` exists and is referenced from
      `agent-workflow/architecture.md`.
- [ ] It states the chosen strategy: **flat schema, attribute names
      aligned with FIWARE Smart Data Models naming, no full SDM adoption**.
- [ ] It pins the canonical NGSI entity type for a device (e.g. `Device`).
- [ ] It tabulates every base device attribute with: NGSI name, NGSI type,
      required/optional, example, mapping note (which `backend.md` field it
      came from, which Smart Data Model field it aligns with).
- [ ] It tabulates per-protocol extension attributes (MQTT, PLC, LoRaWAN)
      in the same form.
- [ ] It defines the telemetry convention: NGSI entity type per measurement
      class (e.g. `TemperatureSensor`), attribute naming (`numValue`,
      `unitCode`, `dateObserved`), and how QuantumLeap maps these to CrateDB
      tables (`mtiot.et<entitytype>`).
- [ ] It pins the **CrateDB scaling policy**: monthly partitioning via
      `PARTITIONED BY (date_trunc('month', time_index))`, retention left to
      a future operational ticket but the partitioning shape is fixed now.
- [ ] It pins the **API query path for telemetry**: API → QuantumLeap REST
      (`/v2/entities/{id}` etc.); the API never issues raw CrateDB SQL on
      hot endpoints. Analytics / batch queries against CrateDB are an
      out-of-scope future concern.
- [ ] It states the **HTTP error contract**: 422 for validation errors
      (FastAPI default), 404 for unknown id, 409 for duplicate id, 400 for
      malformed query strings, 415/413 reserved for upload tickets only.
- [ ] All field names are lowerCamelCase to match NGSI conventions
      (`dateInstalled`, `controlledProperty`, `serialNumber`).
- [ ] FIWARE service / servicepath conventions are pinned
      (e.g. `fiware-service: iot`, `fiware-servicepath: /`).

## Out of scope
- Writing endpoints, database migrations, or any code.
- Adopting full Smart Data Models (`@context`, `dataModel.Device`
  validation). Future ticket if federation requires it.
- Authentication / RBAC field mapping. Deferred to ticket 0009 (Keycloak).
- Designing the maintenance-log schema beyond what `backend.md` already
  fixes — that ticket (0005) will adopt those tables verbatim.
- CrateDB retention policy / partition pruning automation. Operational
  ticket later.

## Open questions (block approval)

_Resolved 2026-04-30 by user direction:_
- **Strategy: (c)** flat schema, Smart-Data-Models-aligned naming, no
  full SDM adoption.
- **Test approach (project-wide convention recorded here for visibility):**
  each future code ticket ships its own pytest suite covering happy path +
  bad input. Single `make test` runs the suite against the live `make up`
  stack. No standalone testing-infrastructure ticket.

_Open for this ticket:_

_Resolved 2026-04-30:_
- **Q1.** Default `fiware-service` = `iot`.
- **Q2.** Default `fiware-servicepath` = `/`.
- **Q3.** Stored id is NGSI URN `urn:ngsi-ld:Device:<uuid>`; API accepts a
  bare UUID in requests and normalises it.
- **Q4.** Optional attributes omitted from the NGSI payload when absent.