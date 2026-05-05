# Tasks — Ticket 0019b

- [x] T1 Add `simulator_enabled` / `simulator_interval_seconds` /
      `simulator_api_base_url` to `app/config.py`.
- [x] T2 Implement `app/simulator.py` (LiveSimulator with bootstrap +
      tick loop + key ownership + bridge.refresh hook).
- [x] T3 Wire simulator into `app/main.py` lifespan after MqttBridge.
- [x] T4 Add `SIMULATOR_ENABLED=true` etc. to compose api env.
- [x] T5 `make test` — 182 passed, 1 pre-existing flake. No regressions.
- [x] T6 Manual smoke: 5 demo devices live; MQTT path through bridge
      writes Device + DeviceMeasurement; HTTP path through the real
      /telemetry route writes the same. QuantumLeap returns history.
- [x] T7 Close ticket.
