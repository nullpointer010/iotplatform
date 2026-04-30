# Journal — Ticket 0002 Data model decision

## Decisions

- **Strategy (c) adopted:** flat schema, attribute names aligned with
  FIWARE Smart Data Models, no full SDM adoption (no `@context`, no SDM
  JSON-Schema validation). Future federation can adopt full SDM without
  field renames.
- **Entity id form:** URN `urn:ngsi-ld:Device:<uuid>`. API accepts a bare
  UUID and normalises before talking to Orion.
- **FIWARE service / servicepath:** `iot` / `/`.
- **Telemetry separated** from device entity into `DeviceMeasurement`
  entities (one per `(device, controlledProperty)`) — keeps Device record
  stable and matches SDM.
- **CrateDB scaling:** monthly partitioning fixed now
  (`PARTITIONED BY date_trunc('month', time_index)`). Retention automation
  deferred to an operational ticket.
- **API query path for telemetry:** always through QuantumLeap REST,
  never raw CrateDB on hot endpoints.
- **Allowed-value enums** pinned for `category`, `supportedProtocol`,
  `deviceState`.
- **HTTP error contract** standardised across all later tickets
  (200/201/400/404/409/422; 415/413 reserved for upload tickets only).

## Lessons

- The first attempt at ticket 0002 was a PDF-upload feature — not in
  `backend.md`. Skipping the data-model decision and jumping to a feature
  produced a slice that would have been thrown away. Doc tickets up
  front are cheap; out-of-spec features are expensive.
- `backend.md`'s `admin_data.maintenance_history` and full
  `technical_specs` are intentionally **not** carried into the device
  entity — maintenance is a separate Postgres subsystem; the rest is YAGNI
  until a ticket needs it.
