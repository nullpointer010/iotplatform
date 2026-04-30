# Journal — 0004

## Decisions

- **`controlledProperty` is a required query parameter on `/telemetry`.** Multi-property fan-out (one call returns all measurements for a device) is plausible but adds Orion+QL coupling without a current consumer; deferred until the dashboard ticket needs it.
- **404 from QL = empty result, not 404 to client.** A device with no measurements yet still exists; clients that poll telemetry should not have to special-case the cold start.
- **State endpoint is a thin projection over the Device entity, not a QL query.** `deviceState`, `dateLastValueReported`, `batteryLevel` are written into the Device entity by ingest agents (or by `PATCH /devices/{id}` for now). This keeps `/state` cheap (single Orion GET) and answers the operational question "is this device alive and what was its last contact".
- **Capitalisation in measurement URN.** API exposes lowercase `controlledProperty` (`temperature`); the URN segment is title-cased (`Temperature`) to match `data-model.md` and stay aligned with Smart Data Models examples.

## Issues hit

1. **Duplicate Orion → QL subscriptions doubled every ingest.** The previous `setup_orion_subscription.sh` only checked "is the URL present?" — but with two duplicate subscriptions, that check passed and the script silently kept both. The first telemetry test reported six rows per three pushes. Fixed the script to dedupe: keep the first subscription, DELETE the rest. The script remains idempotent and now self-heals if duplicates are ever created (e.g. by manual operator action).
2. **Test flakiness vs QL ingestion latency.** The notification → QL → CrateDB path is asynchronous. Solved with `wait_for_ql` polling at 250ms up to 8s. Stable on local Docker; revisit if CI gets flaky.
3. **CrateDB partitioning DDL is not valid.** `data-model.md` quotes `ALTER TABLE … PARTITION BY (date_trunc(...))`; CrateDB only accepts `PARTITIONED BY` at `CREATE TABLE`. Real partitioning therefore needs a migration or pre-create-and-let-QL-use-it path. Documented in requirements/design as out of scope; should land as a dedicated operations ticket. The functional contract of this ticket does not depend on partitioning.

## Numbers

- 30 tests (19 devices + 11 telemetry/state), 2.36s wall.
