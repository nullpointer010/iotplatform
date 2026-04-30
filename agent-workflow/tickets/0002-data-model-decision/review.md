# Review — Ticket 0002 Data model decision

## Self-review against acceptance criteria

| AC                                                              | Status | Evidence |
|-----------------------------------------------------------------|--------|----------|
| `agent-workflow/data-model.md` exists, linked from architecture | done   | new file + link added in `architecture.md` |
| Strategy stated (flat + SDM-aligned naming, no full SDM)        | done   | data-model.md §Strategy |
| Canonical NGSI entity type `Device` pinned                      | done   | data-model.md §Device |
| Base device attribute table with NGSI type/required/example/SDM | done   | data-model.md §Device |
| Per-protocol extension tables (MQTT, PLC, LoRaWAN)              | done   | data-model.md §Per-protocol extensions |
| Telemetry convention (`DeviceMeasurement`, attributes, mapping) | done   | data-model.md §Telemetry |
| CrateDB monthly partitioning policy                             | done   | data-model.md §Scaling |
| API query path for telemetry (always QL, never raw CrateDB)     | done   | data-model.md §API query path |
| HTTP error contract                                             | done   | data-model.md §HTTP error contract |
| lowerCamelCase field naming                                     | done   | every table |
| FIWARE service / servicepath pinned                             | done   | data-model.md §FIWARE conventions |

## Risks / follow-ups

- `unitCode` uses UN/CEFACT codes (`CEL`, `P1`, ...). The first telemetry
  ticket (0004) needs a small whitelist or it will be hard to validate.
- `plcCredentials` and `loraAppKey` are stored opaque now. Ticket 0009
  must move secrets out of Orion (vault/Keycloak/secret store).
- `DeviceMeasurement` uses NGSI v2 “Relationship-style” Text for
  `refDevice`. NGSI-LD migration would promote this to a real
  Relationship; the field name does not change.
- No support for non-numeric measurements (`textValue`) yet. Add only
  when a real ticket needs it.

## External review

_Open for Codex / human review._
