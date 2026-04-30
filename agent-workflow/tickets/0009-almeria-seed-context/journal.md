# Journal — Ticket 0009

## 2026-04-30 — Implementation

### What changed
Three edits in `platform/scripts/add_test_data.py`:

1. **`SITES`** — replaced the 8-row Madrid/Valencia/Barcelona/Sevilla/Alicante list with 8 rows pinned to IFAPA La Cañada + Universidad de Almería (city ∈ `{"Almería", "La Cañada"}`, lat 36.827–36.835, lon −2.406–−2.401).
2. **`OWNERS`** — added IFAPA/UAL affiliation as a hyphen-suffix (e.g. `"Juan Pérez - IFAPA"`). Five names: 2 IFAPA, 2 UAL, 1 untagged.
3. **`_slug(value)`** helper + use in `mqttTopicRoot` — strips diacritics and replaces non-alnum with `-`, lowercased. Without this, `f"crop/{site['city'].lower()}/dev{n:03d}"` produces `"crop/la cañada/dev001"`, which the API rejects with 422 (MQTT topic regex).

### Course corrections
The original design (approved before observability worked) said affiliation should be tagged with parentheses, e.g. `"Juan Pérez (IFAPA)"`. First seed run produced 48/50 → 500. With the new global `Exception` handler from 0010 in place, the traceback was:

```
app.orion.OrionError: create_entity 400:
{"error":"BadRequest","description":"Invalid characters in attribute value"}
```

Root cause: **Orion NGSI v2 forbids `< > " ' = ; ( )` in attribute values**.
4 of 5 owners and 1 of 8 sites contained `()`, and `random.sample(OWNERS, k=1|2)` almost always picked a tagged owner, so almost every device failed.

Fix: replaced `(IFAPA)` with `- IFAPA` (and the one site `(Lab IoT)` with `Lab IoT`). Re-ran `make seed`: 50/50 devices, 1872 telemetry points.

### Validation of 0010's payoff
Before 0010, this same failure produced *empty 500 responses with no body and no traceback* and the seed script just printed `! device 26 skipped: 500`. After 0010 it produced `request_id=06c77a6a11b3` in the body and a full traceback in `docker logs iot-api`, naming `app.orion.create_entity` and quoting Orion's exact error message. Diagnosis took one log grep instead of guesswork.

### Lessons
- Orion forbids `< > " ' = ; ( )` in attribute values; never embed user-display strings with punctuation in NGSI payloads. → distilled into `agent-workflow/memory/gotchas.md`.
- The MQTT `mqttTopicRoot` slug bug was a latent issue from 0008 (the old seed used single-word cities like `"madrid"`); only surfaced when a multi-word city was added. The slug helper is the right defensive fix even if the seed script were the only caller.

### Out of scope (deferred)
Map UI, owner-list overhaul, vendor narrowing, internal greenhouse map, role-aware seed users.
