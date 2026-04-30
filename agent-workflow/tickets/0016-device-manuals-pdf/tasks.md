# Ticket 0016 — tasks

- [x] T1  Add `python-multipart` to `platform/api/requirements.txt`.
- [x] T2  Add the `iot-manuals` named volume to compose; mount at
       `/var/lib/iot/manuals` in `iot-api`.
- [x] T3  `app/models_manuals.py`: `DeviceManual` ORM model.
- [x] T4  Alembic migration `0002_device_manuals.py`.
- [x] T5  `app/schemas_manuals.py`: pydantic `DeviceManualOut`.
- [x] T6  `app/manuals.py`: `MANUALS_DIR`, `save_streaming(file_id, file, max_bytes)`,
       `delete(file_id)`, `path(file_id)`, magic-byte check helper.
- [x] T7  `app/routes/manuals.py`: 4 endpoints with `require_roles` per design.
- [x] T8  Wire `manuals.router` in `app/main.py`.
- [x] T9  `tests/test_manuals.py` covering happy path + edge cases + RBAC + 401.
- [x] T10 `web/src/lib/types.ts`: `DeviceManual`.
- [x] T11 `web/src/lib/api.ts`: `listManuals`, `uploadManual`, `deleteManual`,
       `manualUrl`.
- [x] T12 `web/src/app/devices/[id]/manuals-tab.tsx`.
- [x] T13 `web/src/app/devices/[id]/page.tsx`: add Manuales tab.
- [x] T14 i18n: `manuals.*` keys in `es.json` and `en.json`.
- [x] T15 Run `make test` (full Docker stack); verify all green.
- [x] T16 Run `npm run test` + `npm run typecheck` in `web/`.
- [x] T17 Update roadmap entry, write journal+review, flip status to done.
