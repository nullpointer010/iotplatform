# Journal — 0003

## Decisions

- **PATCH semantics.** Orion's `PATCH /v2/entities/{id}/attrs` returns 422 `PartialUpdate` when an attribute does not exist on the entity yet (e.g. setting `deviceState` for the first time). Switched to `POST /v2/entities/{id}/attrs` which has append-or-update semantics: missing attrs are created, existing ones overwritten. Behaviour from the API client perspective is unchanged.
- **Malformed id → 404, not 400.** Treating non-UUID path segments as not-found keeps the API surface uniform: any id Orion does not know about returns 404. Avoids leaking the URN format to clients.
- **`extra = "forbid"` on Pydantic models.** Catches typos and out-of-spec keys early with a 422.
- **Protocol-specific required fields enforced via `model_validator`.** Keeps `DeviceIn` flat instead of using a discriminated union.
- **Tests run in-container against the live stack.** `make test` execs `pytest` inside `iot-api`. Cleanup is best-effort `DELETE /v2/entities/{id}` per created entity. No mocking: catches real serialization issues against Orion.

## Issues hit

1. PATCH happy-path failed first run with `PartialUpdate` from Orion — fixed by switching to POST attrs (see above).
2. Unknown-entity PATCH bubbled up as 500 (`OrionError`) instead of 404. The fix above also resolves this: `POST /v2/entities/{id}/attrs` returns 404 for unknown ids, which `OrionClient.patch_entity` already maps to `False` → route returns 404.

## Numbers

- 19 tests, 0.45s wall.
