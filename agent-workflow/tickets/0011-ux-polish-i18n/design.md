# Ticket 0011 — Design

## Approach
Three independent, layered concerns under one ticket:
1. **i18n foundation** (`next-intl`) — wires the catalogs that everything else reads from.
2. **Reusable primitives** — `<Tooltip>`, `<FieldLabel>`, `<EmptyState>`, `useMutateWithToast`, `noOrionUnsafeChars`, `optimisticListDelete`. Each is small (~30–80 LOC), one responsibility, no cross-coupling.
3. **Per-page wiring** — devices list, device detail, operation types, three forms, top nav. Pages don't grow new structure; they swap labels/strings through the new primitives.

We do **not** restructure the app, do not add SSR locale segments, do not add a new component library, do not touch the API.

## File-level plan

### New dependencies
- `next-intl@^3.x`
- `@radix-ui/react-tooltip@^1.x`
- `vitest@^2.x`, `@vitejs/plugin-react`, `jsdom` (devDeps, for one focused test)

`lucide-react` is already a dep — use `Info` for the field-help icon (open Q5 → B).

### New files
| Path | Purpose |
|---|---|
| `web/src/components/ui/tooltip.tsx` | Radix Tooltip primitive re-exports + content wrapper styled with `bg-popover text-popover-foreground` and `max-w-xs`. |
| `web/src/components/forms/field-label.tsx` | `<FieldLabel htmlFor label tooltip? required?>` — label text + `Info` icon (`h-4 w-4`) + Radix Tooltip. |
| `web/src/components/ui/empty-state.tsx` | `<EmptyState icon? title description? action?>` — centered, muted, optional CTA button. |
| `web/src/lib/orion-chars.ts` | `ORION_FORBIDDEN = /[<>"'=;()]/`, `findForbiddenChar(s)`, `ORION_FORBIDDEN_HUMAN`. |
| `web/src/lib/orion-chars.test.ts` | One vitest file: 2 cases. |
| `web/src/lib/mutate.ts` | `useMutateWithToast(opts)` — thin wrapper over `useMutation`, derives toast titles from i18n keys, surfaces `ApiError.message` on error. |
| `web/src/lib/optimistic.ts` | `optimisticListDelete(qc, queryKey, predicate)` — snapshot, filter, return `rollback()` thunk. |
| `web/src/i18n/index.ts` | `getLocaleFromCookie()`, `loadMessages(locale)`, `locales = ['es','en'] as const`. |
| `web/src/i18n/messages/es.json` | Spanish catalog (default). |
| `web/src/i18n/messages/en.json` | English mirror. |
| `web/vitest.config.ts` | Minimal config, `jsdom` env. |

### Modified files
| Path | Change |
|---|---|
| `web/package.json` | add deps + `"test": "vitest run"`. |
| `web/src/app/layout.tsx` | wrap children in `<NextIntlClientProvider locale messages>` and `<TooltipProvider delayDuration={150}>`. Read cookie server-side via `cookies()`. |
| `web/src/app/providers.tsx` | unchanged. |
| `web/src/components/top-nav.tsx` + `user-menu.tsx` | add `ES \| EN` toggle inside the user menu (open Q1 → A). Writes `NEXT_LOCALE` cookie + `router.refresh()`. |
| `web/src/components/forms/device-form.tsx` | swap inline `<Label>`/local `Field` for `<FieldLabel label tooltip required>`. Replace hard-coded English with `t('device.field.<name>.label')`. Remove ad-hoc helper text from labels (e.g. "Latitude (-90..90)") — semantics move into tooltip. |
| `web/src/components/forms/operation-type-form.tsx` | same FieldLabel + i18n swap. |
| `web/src/components/forms/maintenance-log-form.tsx` | same. |
| `web/src/lib/zod.ts` | add `noOrionUnsafeChars` (`.superRefine` emitting `orionForbidden:{char}` token). Apply to listed fields; CSV fields validated per item. Localized rendering: form components translate the token via `t('zod.orionForbidden', { char })`. |
| `web/src/app/devices/page.tsx` | reduce to 6 columns: Name / Category / Protocol / State / Site area / Owner. Empty branch → `<EmptyState>` with CTA. Delete uses `useMutateWithToast` + `optimisticListDelete`. |
| `web/src/app/devices/[id]/overview-tab.tsx` | tighten typography (no inline `style=`, consistent `text-xs uppercase tracking-wide` labels, `text-sm` values, 2-col responsive grid). Empty branches → `<EmptyState>`. |
| `web/src/app/devices/[id]/maintenance-tab.tsx` | empty → `<EmptyState>` with "Add maintenance" CTA. Delete optimistic. |
| `web/src/app/devices/[id]/telemetry-tab.tsx` | empty → `<EmptyState>`. |
| `web/src/app/maintenance/operation-types/page.tsx` | empty state + optimistic delete + i18n strings. |
| `web/src/app/devices/[id]/edit/page.tsx`, `devices/new/page.tsx`, `devices/page.tsx` | uniform header pattern (Tailwind row, no new component): `flex items-start justify-between` → `<h1 + p text-muted-foreground>` left, primary action right. |

### Deleted files
None.

## Catalog shape
A single nested JSON per locale, namespaced by feature:

```jsonc
// es.json (excerpt — full catalog written during implementation)
{
  "common":   { "save":"Guardar","cancel":"Cancelar","delete":"Eliminar","edit":"Editar","loading":"Cargando…","empty":"Sin datos" },
  "nav":      { "dashboard":"Panel","devices":"Dispositivos","opTypes":"Tipos de operación","language":"Idioma" },
  "device":   {
    "title":"Dispositivos","new":"Nuevo dispositivo",
    "emptyTitle":"Aún no hay dispositivos",
    "emptyHint":"Crea tu primer dispositivo para empezar a registrar telemetría.",
    "section": { "identity":{"title":"Identidad"},"hardware":{"title":"Hardware"},"location":{"title":"Ubicación"},"admin":{"title":"Administrativo"},"mqtt":{"title":"MQTT"},"plc":{"title":"PLC"},"lora":{"title":"LoRaWAN"} },
    "field": {
      "name":            { "label":"Nombre" },
      "category":        { "label":"Categoría", "tooltip":"Tipo funcional. Ej.: sensor, gateway, plc." },
      "supportedProtocol":{ "label":"Protocolo", "tooltip":"Protocolo principal de comunicación." },
      "deviceState":     { "label":"Estado", "tooltip":"Estado operativo declarado por el operador." },
      "controlledProperty":{ "label":"Propiedades", "tooltip":"Variables que mide o controla. Ej.: temperature, humidity. Separar con comas." },
      "manufacturerName":{ "label":"Fabricante", "tooltip":"Texto libre. {orionRule}" },
      "modelName":       { "label":"Modelo", "tooltip":"Texto libre. {orionRule}" },
      "serialNumber":    { "label":"Nº de serie", "tooltip":"Identificador del fabricante. {orionRule}" },
      "serialNumberType":{ "label":"Tipo de serie", "tooltip":"MAC, IMEI, Internal…" },
      "firmwareVersion": { "label":"Firmware", "tooltip":"Versión instalada. Ej.: 1.4.2. {orionRule}" },
      "owner":           { "label":"Propietarios", "tooltip":"Personas o entidades responsables. Separar con comas. {orionRule}" },
      "ipAddress":       { "label":"Direcciones IP", "tooltip":"IPv4 separadas por comas." },
      "dateInstalled":   { "label":"Fecha de instalación" },
      "latitude":        { "label":"Latitud", "tooltip":"Decimal entre -90 y 90." },
      "longitude":       { "label":"Longitud", "tooltip":"Decimal entre -180 y 180." },
      "siteArea":        { "label":"Zona / Área", "tooltip":"Etiqueta del emplazamiento dentro del sitio. {orionRule}" },
      "address":         { "label":"Dirección (JSON)", "tooltip":"Objeto JSON con claves: street, city, postalCode, country." },
      "mqttTopicRoot":   { "label":"Topic raíz MQTT", "tooltip":"Sin espacios, sin comodines (+ #). Ej.: crop/almeria/dev001." },
      "mqttClientId":    { "label":"Client ID MQTT", "tooltip":"Identificador único en el broker. {orionRule}" },
      "mqttQos":         { "label":"QoS", "tooltip":"0, 1 o 2. 1 es el equilibrio habitual." },
      "mqttSecurity":    { "label":"Seguridad MQTT (JSON)", "tooltip":"{ \"type\":\"TLS\"|\"none\", \"username\"?, \"password\"? }." },
      "plcIpAddress":    { "label":"IP del PLC", "tooltip":"IPv4 alcanzable desde la pasarela." },
      "plcPort":         { "label":"Puerto", "tooltip":"1–65535. 502 (Modbus TCP), 4840 (OPC UA)." },
      "plcConnectionMethod":{ "label":"Método", "tooltip":"Modbus TCP, OPC UA, Siemens S7…" },
      "plcReadFrequency":{ "label":"Frecuencia (s)", "tooltip":"Intervalo de lectura en segundos." },
      "plcTagsMapping":  { "label":"Mapeo de tags (JSON)", "tooltip":"Objeto: { \"DB1.DW0\":\"alias\" }." },
      "plcCredentials":  { "label":"Credenciales (JSON)", "tooltip":"{ \"username\":\"…\", \"password\":\"…\" }." },
      "loraDevEui":      { "label":"DevEUI", "tooltip":"16 caracteres hexadecimales." },
      "loraAppEui":      { "label":"AppEUI", "tooltip":"16 caracteres hexadecimales." },
      "loraAppKey":      { "label":"AppKey", "tooltip":"32 caracteres hexadecimales." },
      "loraNetworkServer":{ "label":"LNS", "tooltip":"URL del Network Server." },
      "loraPayloadDecoder":{ "label":"Decodificador", "tooltip":"Nombre o referencia del decoder." }
    }
  },
  "opType":   { "title":"Tipos de operación","new":"Nuevo tipo","emptyTitle":"Sin tipos definidos","emptyHint":"Crea un tipo de operación para registrar mantenimientos.","field":{ "name":{"label":"Nombre"},"description":{"label":"Descripción"},"requiresComponent":{"label":"Requiere componente","tooltip":"Marcar si la operación afecta a un componente concreto del dispositivo."} } },
  "maintLog": { "field":{ "operationType":{"label":"Tipo de operación"},"startTime":{"label":"Inicio"},"endTime":{"label":"Fin","tooltip":"Debe ser igual o posterior al inicio."},"componentPath":{"label":"Componente","tooltip":"Ruta libre. Ej.: sensor.temperature."},"performedBy":{"label":"Ejecutado por","tooltip":"UUID del operador. Opcional."},"detailsNotes":{"label":"Notas"} } },
  "zod":      { "required":"Campo obligatorio","orionForbidden":"Carácter no permitido: «{char}». No usar < > \" ' = ; ( )." },
  "toast":    { "saved":"Cambios guardados","saveFailed":"No se pudo guardar","deleted":"Elemento eliminado","deleteFailed":"No se pudo eliminar","created":"Creado correctamente" },
  "_meta":    { "orionRule":"No usar: < > \" ' = ; ( )" }
}
```

`{orionRule}` is interpolated once at provider init via a small post-processor that scans every string value and replaces `{orionRule}` with `_meta.orionRule` for the active locale. Avoids duplicating the literal in every tooltip; cheap (one tree walk on locale load).

## Component contracts (signatures only)

```ts
// components/ui/tooltip.tsx — re-exports Radix
export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider };

// components/forms/field-label.tsx
export function FieldLabel(props: {
  htmlFor: string;
  label: string;
  tooltip?: string;
  required?: boolean;
  className?: string;
}): JSX.Element;
// Renders Label + (required ? '*' : '') + (tooltip ? <Info /> Tooltip : null).
// The Info icon is inside <TooltipTrigger asChild><button type="button" tabIndex={0}>…</button>.

// components/ui/empty-state.tsx
export function EmptyState(props: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: { label: string; href?: string; onClick?: () => void };
}): JSX.Element;

// lib/orion-chars.ts
export const ORION_FORBIDDEN: RegExp;        // /[<>"'=;()]/
export const ORION_FORBIDDEN_HUMAN: string;  // for tooltips/static help
export function findForbiddenChar(s: string): string | null;

// lib/zod.ts (additions)
export const noOrionUnsafeChars: <T extends z.ZodString>(s: T) => T;
// Adds .superRefine that emits message `orionForbidden:${char}`.

// lib/mutate.ts
export function useMutateWithToast<T, V>(opts: {
  mutationFn: (v: V) => Promise<T>;
  successKey?: string;            // default 'toast.saved'
  errorKey?: string;              // default 'toast.saveFailed'
  onSuccess?: (data: T) => void;
}): UseMutationResult<T, ApiError, V>;

// lib/optimistic.ts
export function optimisticListDelete<I>(
  qc: QueryClient,
  queryKey: unknown[],
  match: (item: I) => boolean,
): { rollback: () => void };
```

## i18n integration depth (open Q2 → A)
- Root layout reads cookie `NEXT_LOCALE` (default `es`); passes to `<NextIntlClientProvider locale messages>`.
- Catalog import is dynamic per request: `await import('@/i18n/messages/' + locale + '.json')`. Hot path is fine (Next caches the module).
- Locale switch in user menu writes `document.cookie='NEXT_LOCALE=…; path=/; max-age=31536000'` and `router.refresh()`.
- No `[locale]` route segment. Migration to segmented later is purely additive.

## Tooltip icon (open Q5 → B)
`Info` from lucide-react. `h-4 w-4 text-muted-foreground hover:text-foreground`. Trigger is a real `<button type="button">` so keyboard focus opens the tooltip.

## Forbidden-char enforcement layer (open Q3 → A)
Client-side only. A backend mirror is mentioned in `journal.md` as a future ticket; not opened here.

## Visual tightening rules
- Devices list: 6 columns (Name / Category / Protocol / State / Site area / Owner). Long-form fields visible only on detail.
- Device detail overview: `grid grid-cols-1 md:grid-cols-2 gap-4`. Each cell `<dt class="text-xs uppercase tracking-wide text-muted-foreground">…</dt><dd class="text-sm">…</dd>`. No inline `style=`.
- Forms: each section keeps its card; one-line `text-sm text-muted-foreground` description from `device.section.<id>.title` if set.

## Tests
- `web/src/lib/orion-chars.test.ts` — vitest, two cases. Wires `npm test` for the web workspace for the first time.
- Backend tests untouched; `make test` (80 cases) must still pass.
- Manual verification list lives in `tasks.md` (locale switch, tooltip on hover/focus, optimistic delete + rollback simulation, axe-core scan).

## Out of scope (re-stated)
- Bulk delete, multi-select.
- Map view (0012), auth (0013–0015), file uploads (0016).
- Per-locale URL segments.
- Backend mirror of forbidden-char rule.
- Translating backend error strings.

## Risks & mitigations
| Risk | Mitigation |
|---|---|
| `next-intl` v3 prefers `[locale]` segments. Cookie-only mode is supported but less idiomatic. | Document in journal; revisit only if real perf / SEO need appears. |
| Tooltip awkward on touch. | Radix's default long-press behaviour is acceptable for our desktop-first context. |
| Forbidden-char regex blocks legitimate input in JSON textareas (e.g. `address`). | Refinement only applied to free-text Orion-attribute fields; JSON textareas validated by their existing `JSON.parse` check, not by `noOrionUnsafeChars`. |
| Optimistic delete leaves stale cache on server failure. | Always `rollback()` in `onError` and `qc.invalidateQueries(queryKey)` in `onSettled`. |
| Catalog drift between es and en. | Optional dev-time `node scripts/i18n-check.mjs` compares key sets (added if cheap; not blocking). |
| Adding vitest balloons the web devDeps. | Only one tiny test — but the infra is paid down for future tickets (0015 will benefit). Acceptable. |
