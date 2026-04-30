# Ticket 0009 — Design

## Approach
A surgical, single-file edit to `platform/scripts/add_test_data.py`. The
script's structure (HTTP helpers, build payloads, wipe / seed flow) is
correct as-is and stays untouched. We only touch two module-level
constants:

1. `SITES` — replaced with the 8-row IFAPA La Cañada + UAL list pinned
   in `requirements.md` (lat/lon and `site_area` strings copied
   verbatim, plus `city` ∈ {`"Almería"`, `"La Cañada"`}).
2. `OWNERS` — keep the existing 5 person names; suffix with `(IFAPA)`
   or `(UAL)` so each downstream device payload still gets a
   person-like value but the affiliation is visible. Two are tagged
   IFAPA, two UAL, one left untagged so we still cover the
   "external contractor" case.

`MANUFACTURERS` and `MODELS` stay generic per the open-question default
in `requirements.md`.

`_build_device(n)` already does `random.choice(SITES)` and applies a
`±0.01` jitter (~1 km). With the new tighter coordinates this means
every device lands inside roughly `[36.81, 36.86] × [−2.42, −2.38]` —
exactly the box the acceptance criteria mandate.

## Why not change anything else
- The `category`, `protocol`, `state`, telemetry, and maintenance flows
  are orthogonal to the seed *context* and were validated in 0008.
  Touching them would violate the "surgical changes" rule.
- `address.country = "ES"` is hard-coded in `_build_device` and stays
  correct for the new sites.
- The `SEED_DEVICE_NAME_PREFIX` / `SEED_OPTYPE_PREFIX` markers used by
  `wipe_seed_data()` are unchanged, so `make seed` still cleans up
  previous batches (including the old Madrid/Valencia/etc. ones)
  before re-seeding.

## Concrete edits

### `SITES`
Replace the existing list literal with:

```python
SITES = [
    {"site_area": "IFAPA La Cañada - Invernadero 1",       "latitude": 36.83414, "longitude": -2.40211, "city": "La Cañada"},
    {"site_area": "IFAPA La Cañada - Invernadero 2",       "latitude": 36.83470, "longitude": -2.40165, "city": "La Cañada"},
    {"site_area": "IFAPA La Cañada - Cabezal de Riego",    "latitude": 36.83380, "longitude": -2.40250, "city": "La Cañada"},
    {"site_area": "IFAPA La Cañada - Sala Técnica",        "latitude": 36.83440, "longitude": -2.40190, "city": "La Cañada"},
    {"site_area": "IFAPA La Cañada - Estación Meteo",      "latitude": 36.83505, "longitude": -2.40130, "city": "La Cañada"},
    {"site_area": "UAL - Finca Experimental Anasol",       "latitude": 36.82750, "longitude": -2.40470, "city": "Almería"},
    {"site_area": "UAL - Edificio CITE II (Lab IoT)",      "latitude": 36.82690, "longitude": -2.40580, "city": "Almería"},
    {"site_area": "UAL - Invernadero Investigación",       "latitude": 36.82820, "longitude": -2.40400, "city": "Almería"},
]
```

Notes:
- `Cañada` / `Técnica` / `Estación` / `Almería` / `Investigación` keep
  their accents — the file already uses non-ASCII strings (e.g.
  `"Calibración"`) so the source is UTF-8 and JSON encoding handles it.
- ASCII hyphen `-` (not em dash) keeps copy/paste & terminal output safe.

### `OWNERS`
Replace the existing list literal with:

```python
OWNERS = [
    "Juan Pérez (IFAPA)",
    "María García (UAL)",
    "Carlos Ruiz (IFAPA)",
    "Ana Sánchez (UAL)",
    "Luis Fernández",
]
```

Satisfies the `requirements.md` clause: at least one owner contains
`IFAPA`, at least one contains `UAL`. `Luis Fernández` stays untagged
to keep coverage of "third-party / external" personnel.

## Risks
- **Re-seeding does not delete devices created with the old Madrid/etc.
  sites.** It does — `wipe_seed_data()` filters by name prefix
  (`"Seed Device "`) which is preserved by this change, so the next
  `make seed` will wipe the Madrid batch and replace it with Almería.
- **API rejects accented `site_area`.** Already proven false in 0008
  (the original list contained `"Almacén"`, `"Técnica"`); JSON encoding
  + Orion accept UTF-8.
- **Map jitter pulls devices off-campus.** `±0.01°` is ~1.1 km. La Cañada
  IFAPA and UAL are ~1.2 km apart, so a worst-case jittered IFAPA point
  could land on the UAL side of the road. Acceptable: still inside the
  acceptance-box, still recognisable on the future map, and the
  `site_area` label stays correct.

## Verification plan
Mapped 1:1 to the acceptance criteria in `requirements.md`:

1. Visual diff: `git diff platform/scripts/add_test_data.py` shows
   only the two constants change.
2. Lint sanity: `python -m py_compile platform/scripts/add_test_data.py`.
3. `make up && make seed` against a clean stack runs to completion and
   prints the same `~50 devices / 8 op-types / ~150 maintenance / N
   telemetry points` summary as 0008.
4. Spot-check via API: `curl -s localhost/api/v1/devices?limit=1000 | jq '[.[].location.site_area] | unique'`
   returns a subset of the 8 new `site_area` strings, no leftover
   `"Finca Norte"` / `"Estación Meteorológica Central"` / etc.
5. Spot-check coords: same query with `[.[].location | {lat:.latitude, lon:.longitude}]`
   — every entry within the acceptance box.
6. Spot-check owners: `jq '[.[].owner[]] | unique'` contains at least
   one `(IFAPA)` and one `(UAL)` value.

Tests: no pytest suite is added — the seed script has none today and
adding one for an 8-row data table would be over-engineering. The
`make seed` end-to-end run is the verification, as it was in 0008.

## Out of scope (re-stated)
External map (0011), internal map (0016), bulk delete, owner-list
overhaul, vendor-list narrowing, pytest for the seed script.
