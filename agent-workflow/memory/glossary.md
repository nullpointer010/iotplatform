# Glossary

Domain and stack terms used in this project.

- **NGSI / NGSI-LD** — Information model used by Orion Context Broker to
  represent entities and their attributes.
- **Orion Context Broker** — FIWARE component that manages real-time context
  (current state of entities/devices).
- **QuantumLeap** — Component that subscribes to Orion and persists historical
  attribute values in a time-series store (CrateDB).
- **CrateDB** — Distributed columnar SQL database used for telemetry.
- **Entity (NGSI)** — A device or logical object with an `id`, a `type`, and
  attributes.
- **AppEUI / DevEUI / AppKey** — LoRaWAN identifiers and authentication key.
- **QoS (MQTT)** — Quality of Service level (0, 1, 2) for message delivery.
- **RBAC** — Role-Based Access Control. Roles in v1: `viewer`, `operator`,
  `maintenance_manager`, `admin`.
