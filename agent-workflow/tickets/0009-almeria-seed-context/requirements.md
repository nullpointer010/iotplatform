# Ticket 0009 — almeria-seed-context

## Problem
`platform/scripts/add_test_data.py` (added in 0008) seeds the platform
with eight generic Spanish sites scattered across Madrid, Valencia,
Barcelona, Sevilla and Alicante. The real CropDataSpace context is
agricultural research around Almería — IFAPA Centro La Cañada and the
Universidad de Almería. With the current seed, anything that visualises
location (telemetry tab, future map ticket 0011) lands far from any
actual greenhouse, which makes demos confusing.

## Goal
The seed batch represents a realistic IFAPA La Cañada + UAL deployment:
all devices live within ~3 km of `36.834138, −2.402108` (the IFAPA La
Cañada invernadero pinned in Google Maps) and their `site_area` /
`address.city` strings name the facilities a Spanish stakeholder would
recognise.

## User stories
- As an agent demoing the platform, I want seeded devices to cluster
  around the actual IFAPA La Cañada / UAL facilities so the upcoming
  external-map view (0011) shows them inside the right invernaderos.
- As a stakeholder reading the device list, I want `site_area` values
  in Spanish that match real CropDataSpace facilities (IFAPA, UAL),
  not synthetic "Finca Norte / Finca Sur" placeholders.

## Acceptance criteria (verifiable)
- [ ] `platform/scripts/add_test_data.py` defines a `SITES` list with
      exactly the IFAPA La Cañada and UAL sub-areas listed in
      [Sites](#sites) below — no Madrid / Valencia / Barcelona /
      Sevilla / Alicante entries remain.
- [ ] Every site has `latitude` within `[36.81, 36.86]` and `longitude`
      within `[−2.42, −2.38]` (a ~5 km box around La Cañada).
- [ ] `address.city` is one of `"Almería"` or `"La Cañada"`; `country`
      stays `"ES"`.
- [ ] `OWNERS` reflects plausible IFAPA / UAL roles (e.g. técnico
      IFAPA, investigador UAL). At least one owner string contains
      "IFAPA" and at least one contains "UAL".
- [ ] `make seed` runs end-to-end against `make up` with no errors and
      creates ~50 devices, 8 op-types and ~150 maintenance entries
      (same counts as 0008).
- [ ] `GET /api/v1/devices?limit=1000` after seeding shows every device
      with `location.site_area` matching one of the new entries.
- [ ] No other file is modified — change is confined to
      `platform/scripts/add_test_data.py`.

## Sites

Coordinates anchored on the Google Maps pin you provided
(`36.834138, −2.402108`, IFAPA La Cañada). Per-site offsets are small
(<2 km) and intentionally distinct so they spread across the campus
when rendered on a map.

| `site_area` | lat | lon | city |
|---|---|---|---|
| IFAPA La Cañada — Invernadero 1 | 36.83414 | −2.40211 | La Cañada |
| IFAPA La Cañada — Invernadero 2 | 36.83470 | −2.40165 | La Cañada |
| IFAPA La Cañada — Cabezal de Riego | 36.83380 | −2.40250 | La Cañada |
| IFAPA La Cañada — Sala Técnica | 36.83440 | −2.40190 | La Cañada |
| IFAPA La Cañada — Estación Meteo | 36.83505 | −2.40130 | La Cañada |
| UAL — Finca Experimental Anasol | 36.82750 | −2.40470 | Almería |
| UAL — Edificio CITE II (Lab IoT) | 36.82690 | −2.40580 | Almería |
| UAL — Invernadero Investigación | 36.82820 | −2.40400 | Almería |

The existing per-device jitter (`±0.01`) is kept, which is ~1 km — small
enough to stay around the campus, large enough to avoid all devices
stacking on the same pixel.

## Out of scope
- The external map view itself (ticket **0011**).
- Internal floor-plan / drag-place / AI-generated plan (ticket **0016**).
- Changing the device categories, protocols, owners pool size, or any
  business logic in the seed script.
- Renaming the `SEED_DEVICE_NAME_PREFIX` / `SEED_OPTYPE_PREFIX` markers
  used to wipe previous seed batches.
- i18n of the `OPERATION_TYPES` / detail-notes strings (already Spanish
  enough; revisit in 0010).

## Open questions
- Owner names: keep the current 5 generic Spanish names and just add
  IFAPA/UAL role suffixes (e.g. `"Juan Pérez (IFAPA)"`), or replace the
  list with role-only strings (e.g. `"Técnico IFAPA"`,
  `"Investigador UAL"`)? **Default: suffix the existing names**, since
  it preserves person-like values that the maintenance-log UI already
  expects.
- Should `MANUFACTURERS` / `MODELS` be narrowed to vendors actually used
  at IFAPA/UAL? **Default: no** — that's vendor-specific knowledge we
  don't have on hand and it has no map impact.
