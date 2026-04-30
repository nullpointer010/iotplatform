# Project Charter — CropDataSpace IoT Platform

## Vision
A modular IoT platform to ingest, store, query and analyze agricultural sensor
data. The platform must support multiple device protocols (MQTT, PLC, LoRaWAN),
provide a REST API for clients, persist historical telemetry, and integrate
visualization, ML, automation, storage, monitoring and authentication services.

The authoritative product specification lives in `context/doc/`. In particular,
`context/doc/backend.md` defines the v1 backend in detail.

## In scope (v1 — backend foundation)
- FastAPI REST API at `/api/v1`
- Orion Context Broker for device context
- QuantumLeap + CrateDB for historical telemetry
- PostgreSQL for relational data (maintenance log, operation types)
- MongoDB as Orion's backing store
- Device CRUD, telemetry query, maintenance log, device state
- Keycloak-based RBAC (roles: `viewer`, `operator`, `maintenance_manager`, `admin`)
- Docker Compose deployment for development

## Out of scope (deferred to later phases)
- Apache Superset (visualization)
- H2O.ai (ML)
- Node-RED, Apache NiFi, Apache Airflow (automation / no-code workflows)
- MinIO (object storage)
- MQTT broker (Eclipse Mosquitto) and ingestion pipeline
- Prometheus / Grafana (monitoring)
- Kubernetes deployment

These appear as later phases in `roadmap.md`.

## Stakeholders
- TODO — to be filled.

## Source of truth
- Product requirements: `context/doc/backend.md` (and the rest of `context/doc/`).
- Development workflow and decisions: `agent-workflow/`.
- Existing draft code under `context/platform/` is a **reference draft, not a
  contract**. Ticket 0001 decides whether to promote, refactor or replace it.
