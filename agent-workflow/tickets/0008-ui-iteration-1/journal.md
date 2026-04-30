# Journal

## Decisions

- **`location` switched from `geo:point` to `StructuredValue`.** Adding
  `site_area` to the location group meant the value can no longer be the
  Orion `"lat,lon"` string. We now persist the whole dict as
  `StructuredValue`. `_parse_value` retains a back-compat branch that
  splits a legacy `"lat,lon"` string into `{latitude, longitude}` on read,
  so devices written by the previous data model still round-trip cleanly
  through `GET`.
- **JSON textareas instead of structured editors** for `address`,
  `mqttSecurity`, `plcCredentials`, `plcTagsMapping`, `controlledProperty`.
  Keeps this ticket surgical: no new field-level UI primitives. Server-side
  validation already produces precise 422 messages, which the form
  surfaces unchanged.
- **Sentinel `"__all__"` for filter Selects.** Radix Select rejects empty
  string values, so `"__all__"` is the local "no filter" marker; mapping
  back to `undefined` happens in the client filter step.
- **Deterministic seed IDs.** `uuid.uuid5(SEED_NS, f"device-{n}")` so
  `make seed` is idempotent. The wipe step finds previous batches by
  matching on the `Seed Device ` name prefix (the URN suffix has to be a
  plain UUID because `to_urn` validates it).
- **Telemetry pushed straight to Orion.** The seed script POSTs
  `DeviceMeasurement` entities to `/v2/entities`; the existing
  `setup_orion_subscription.sh` notification carries them into
  QuantumLeap → CrateDB, exercising the live ingestion path.

## Lessons

- Orion v2 forbids parentheses (and a handful of other characters) in
  plain Text attribute values. The seed initially used
  `"Seed Device 001 (sensor/mqtt)"` and got `400 Invalid characters in
  attribute value` for every device. Dash-separated form is fine.
  StructuredValue payloads are exempt because their string contents are
  JSON-encoded.
- `iot-api`'s `docker logs` only captured uvicorn lifecycle warnings,
  not request-level tracebacks, while reproducing the seed failure. The
  productive move was to import `to_ngsi` and POST directly to Orion
  inside the container to surface the real 400 message — much faster
  than bisecting the payload field by field.
- Final live run produced 50 devices, 8 operation types, 150 maintenance
  entries and 1824 telemetry points.
