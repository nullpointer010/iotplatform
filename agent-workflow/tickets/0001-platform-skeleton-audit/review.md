# Review — Ticket 0001

## Self-review against acceptance criteria

| AC                                              | Status | Evidence                                                  |
|-------------------------------------------------|--------|-----------------------------------------------------------|
| Top-level `platform/` skeleton                  | done   | `platform/{api,compose,config,scripts}/` + `.env.example` |
| Root `Makefile` with `up/down/logs/ps`          | done   | `Makefile` (also: restart, bootstrap, clean)              |
| `make up` boots full stack                      | done   | 6 services Up, healthchecks green                         |
| API health endpoint returns 200                 | done   | `curl /healthz` → `{"status":"ok"}` (replaced `/dummy`)   |
| `context/platform/` frozen, untouched           | done   | only added `context/platform/README.md` frozen note       |
| Image versions documented                       | done   | journal.md table + architecture.md                        |
| Bootstrap idempotent                            | done   | second `make bootstrap` reports "skipping"                |

## Deviations from requirements

- Replaced `/dummy` with `/healthz` (already noted in design.md). `/dummy`
  was a placeholder; healthz is the standard probe name and avoids a
  follow-up rename ticket.
- Dropped the demo `test_sensor_001` entity + 5-update loop from the
  original `bootstrap.sh`. Skeleton ticket only; data flow will be
  exercised by the next ticket(s) that add real sensors.

## Risks / follow-ups

- No automated tests yet — only manual verification. A near-future ticket
  should add a smoke test (pytest hitting `/healthz` plus `make up && make down`).
- SQLAlchemy + cratedb driver dropped from `requirements.txt`; reintroduce
  when the first DB-backed route lands.
- Compose `depends_on` does not wait for healthcheck readiness; switch to
  `condition: service_healthy` if ordering becomes a problem.

## External review

_Open for Codex / human review._
