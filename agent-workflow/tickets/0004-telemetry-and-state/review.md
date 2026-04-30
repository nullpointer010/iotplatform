# Review — 0004

## Self-review

- All 11 acceptance criteria from `requirements.md` are exercised; full suite (devices + telemetry + state) is 30/30 green via `make test`.
- No code outside ticket scope was touched, except for `setup_orion_subscription.sh` which had a latent idempotency bug surfaced by the new tests — fix is minimal and self-contained.
- Subscription dedupe fix is forward-compatible with 0001 (single-subscription happy path stays the same: "already exists, keeping first" instead of "skipping").

## Follow-ups (out of scope here)

- Multi-property telemetry endpoint (return all `controlledProperty` series for a device in one call) when the dashboard requires it.
- CrateDB monthly partitioning — needs a real migration plan (see journal).
- Non-numeric measurements (`textValue`).
- Push the duplicate-subscription healing logic up into a separate maintenance script if it ever needs to be re-run without `make bootstrap`.

## External review

_(empty — awaiting Codex / human pass)_
