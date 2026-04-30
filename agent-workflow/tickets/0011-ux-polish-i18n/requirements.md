# Ticket 0011 — ux-polish-i18n

## Problem
The 0007/0008 web UI works but feels heavy: dense forms, walls of small grey text, repetitive Spanish/English mix, no toast feedback on success, deletes flash a confirmation dialog and then "freeze" while the list refetches, and empty lists show a bare table header with no call to action. There is also no centralised i18n: copy is hard-coded inline in every component.

A second concrete pain point: forms that submit to Orion (Device create / Device edit) accept characters Orion forbids (`< > " ' = ; ( )`), then the API returns a 400 the user reads as "something went wrong". The seed-data work in 0009 burnt through this exact issue.

## Goal
Make the web app feel calmer, more consistent, and translatable, and keep users out of avoidable backend errors. No new pages, no bulk actions, no new component library.

## User stories
- As an operator, I want the device list and detail pages to look airy and scannable so I can locate a device at a glance instead of reading every row.
- As an operator, I want every create/update/delete to give me an immediate toast (success or failure) so I don't wonder whether the action took effect.
- As an operator, I want deletes to disappear from the list instantly (and roll back on failure) so the UI feels responsive.
- As an operator, when the list is empty I want a clear next-step button (e.g. "Create your first device") instead of a blank table.
- As an operator, I want the UI in Spanish by default and switchable to English so I can hand it to non-Spanish reviewers without renaming labels.
- As an operator, when I type a `(` or a `;` in a name / owner / site_area / model field, the form rejects it inline before I submit, with a Spanish message naming the offending character — so I never see Orion's 400.

## Acceptance criteria (verifiable)

### Visual polish
- [ ] Devices list, device detail (overview tab), maintenance tab and operation-types page render with a tightened typographic scale: at most two text sizes per card, consistent `text-muted-foreground` for secondary metadata, no inline `style={...}` density overrides.
- [ ] Devices list table shows fewer columns by default (Name, Category, Protocol, State, Site area, Owner). Other attributes move into a collapsible "More info" row or remain only on the detail page. Visual diff: a screenshot at 1440px shows ≤ 6 visible columns.
- [ ] Page-level header pattern is uniform across `devices`, `devices/[id]`, `devices/new`, `devices/[id]/edit`, `maintenance/operation-types`: `<title> + <subtitle?> + <primary action on the right>`.
- [ ] At least the four main pages (`/`, `/devices`, `/devices/[id]`, `/maintenance/operation-types`) pass an axe-core accessibility scan with zero `serious` or `critical` violations (run via `npm run a11y` script that pipes against the running dev server, or document the manual run).

### Toasts + optimistic delete
- [ ] Every mutation (`POST`, `PATCH`, `DELETE` in `lib/api.ts`) goes through a small wrapper (`mutateWithToast`) that fires an idiomatic toast on success and on error. Error toast surfaces the API's `detail` field if present, else a generic "No se pudo …" message.
- [ ] All three list-style delete flows (devices list, operation types page, maintenance log entries on the device maintenance tab) update the cached list immediately on confirm via `queryClient.setQueryData` and roll back on failure.

### Empty states
- [ ] A reusable `<EmptyState />` component exists under `components/ui/empty-state.tsx` with `title`, `description?`, `action?` props and is used by:
  - devices list (no devices)
  - device detail / maintenance tab (no maintenance entries)
  - device detail / telemetry tab (no series)
  - operation types page (no types)

### i18n (next-intl)
- [ ] `next-intl` is wired (root provider, `messages/es.json`, `messages/en.json`, locale switch in the user menu). Default locale is `es`. The locale persists in a cookie.
- [ ] Every visible string on the four main pages above and on the three forms (device, operation type, maintenance log) reads from a message catalog. Grep for hard-coded Spanish/English on `app/**` and `components/forms/**` returns no human-language sentences (constants like `urn:ngsi-ld:` are fine).
- [ ] Switching to `en` translates all four main pages without leftover Spanish.
- [ ] Toast messages and error envelopes also resolve from the catalog.

### Forbidden-character guard
- [ ] A shared Zod refinement `noOrionUnsafeChars` lives in `web/src/lib/zod.ts` and rejects any of `< > " ' = ; ( )`.
- [ ] It is applied to every device-form free-text field that becomes an Orion attribute value: `name`, `manufacturerName`, `modelName`, `serialNumber`, `firmwareVersion`, every `owner` entry, `location.site_area`, `address.city`, `address.country`, `mqttClientId`. (For `mqttTopicRoot` the existing topic regex already excludes them; no change needed.)
- [ ] The error message is localized in both catalogs and names the offending character (e.g. `Carácter no permitido: «(»`). Two pytest-style or vitest-style unit tests on `noOrionUnsafeChars` cover one happy path and one failing path; if vitest is not yet wired, a single `lib/zod.test.ts` may be added with a minimal vitest config — otherwise a runtime smoke test in the form's submit handler is acceptable.

### Field help tooltips (mirror crop-edc pattern)
The CropDataSpace frontend at `/home/maru/crop-edc/frontend` ships a small
helper component `FormLabelContent` (`src/components/form/form-label-content.tsx`)
that renders a Radix `Tooltip` triggered by a `QuestionMarkCircleIcon` next
to each form label, fed by an optional `tooltip` prop on `InputField`. We
copy that pattern for our IoT forms.

- [ ] Add a Radix Tooltip primitive at `web/src/components/ui/tooltip.tsx` (Radix `@radix-ui/react-tooltip`, already on the same Radix family the project uses) wrapping `Tooltip / TooltipTrigger / TooltipContent / TooltipProvider`.
- [ ] Add `web/src/components/forms/field-label.tsx` exporting `<FieldLabel htmlFor label tooltip? required? />`. When `tooltip` is set, render a small `Info` (or `HelpCircle`) icon (`lucide-react`, already a project dep) sized `h-4 w-4` next to the text, with `text-muted-foreground` resting and `text-foreground` on hover. Hover/focus shows the Radix Tooltip with `tooltip` text.
- [ ] Every label inside `components/forms/device-form.tsx`, `components/forms/operation-type-form.tsx` and `components/forms/maintenance-log-form.tsx` is rendered through `<FieldLabel ... />`. No raw `<Label>` left in those three files.
- [ ] Tooltip strings come from the i18n catalogs (`device.tooltip.<field>`, `opType.tooltip.<field>`, `maintLog.tooltip.<field>`). Catalog completeness check: each labeled field whose semantics are non-obvious (e.g. `mqttTopicRoot`, `mqttQos`, `mqttSecurity`, `controlledProperty`, `serialNumberType`, `firmwareVersion`, `plcConnectionMethod`, `plcReadFrequency`, `plcTagsMapping`, `loraDevEUI`, `loraAppEUI`, `loraAppKey`, `dateInstalled`, `deviceState`, `category`, `supportedProtocol`, `site_area`, `address.country`, `owner`, `mqttSecurity.type`) carries a tooltip string in both `es.json` and `en.json`. Trivial fields (`name`, `id`) may omit the tooltip.
- [ ] The Orion-forbidden-character rule is mentioned in the relevant tooltips (e.g. `name`, `owner`, `manufacturerName`, `modelName`, `site_area`) so users see it before submitting. Single shared Spanish/English string referenced by these tooltips: `No usar: < > " ' = ; ( )`.
- [ ] Visual: tooltip background uses the existing `--popover` token, max-width ~`w-72`, body text `text-sm`, icon trigger `h-4 w-4 text-muted-foreground hover:text-foreground`. Matches crop-edc weight, not heavier.

## Out of scope
- Bulk delete / multi-select on lists.
- Replacing Radix or Tailwind, adding shadcn registry, adding a chart library beyond what 0007/0008 already use.
- Map view (deferred to 0012).
- Auth / role-aware visibility (deferred to 0013–0015).
- Server-side rendering of locales (a single client-side `<NextIntlClientProvider>` at the root is fine for this iteration).
- Backend error-message translation. Backend stays English; the web layer maps known `detail` strings to localized toasts.

## Open questions
1. **Locale switch placement.** Option A: in the top-right user menu (consistent with the 0015 plan). Option B: a dedicated `EN | ES` toggle in the top-nav. Recommendation: A.
2. **`next-intl` integration depth.** Option A: minimal — single `<NextIntlClientProvider>` at the root, locale read from cookie, no per-route segments. Option B: route-segmented (`/[locale]/devices`). A is cheaper and reversible; B is the official long-term pattern. Recommendation: A for this ticket, plan B for a later one if the team wants per-locale URLs.
3. **Forbidden-char enforcement layer.** Option A: client-side only (Zod). Option B: also add a FastAPI-side validator on `Device` payloads. A keeps the change scoped to the web ticket; B duplicates the check across two ticket scopes. Recommendation: A here, surface B as a follow-up backend ticket if desired.
4. **English copy quality.** Option A: agent writes the catalog. Option B: catalog stub with TODOs and human review. Recommendation: A, keep messages short and idiomatic; user can edit in review.
5. **Tooltip icon.** Option A: `HelpCircle` from lucide-react (matches crop-edc's `QuestionMarkCircleIcon` semantics). Option B: `Info` from lucide-react (literal "(i)" circle). Recommendation: B per the user's request ("little circle with (i)").
