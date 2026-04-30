# Patterns

Reusable patterns that have proven to work in this repo. Append one bullet per
pattern. Keep it short — link to the ticket where it was discovered.

<!-- Example entry (delete once real entries exist):
- Pydantic models live in `app/schemas/`, ORM models in `app/models/`. Never mix. (ticket 0002)
-->

- Web mutations go through `useMutateWithToast<T,V>` (`web/src/lib/mutate.ts`): wraps `useMutation`, fires localized success/error toasts via `next-intl`, surfaces `ApiError.message` in the destructive description. Cuts boilerplate to one line per mutation. (ticket 0011)
- List deletes use `optimisticListDelete<I>(qc, queryKey, match)` (`web/src/lib/optimistic.ts`): snapshot, filter, return a `{ rollback }` thunk to call inside the catch block. (ticket 0011)
- Zod refinements that need an i18n parameter encode the parameter into the message as `key:value` (e.g. `orionForbidden:(`). The form component splits the prefix and feeds the rest to `t(key, { ... })`. Keeps Zod sync and pure. (ticket 0011)
- Field labels in forms render through `<FieldLabel htmlFor label tooltip? required? />` (`web/src/components/forms/field-label.tsx`) — Radix tooltip + lucide `Info` trigger. Mirrors crop-edc's `FormLabelContent`. (ticket 0011)
- next-intl is wired without `[locale]` route segments: `web/src/i18n/index.ts` reads the `NEXT_LOCALE` cookie via `next/headers`, layout passes locale + messages into `<NextIntlClientProvider>`. Locale switch = cookie write + `router.refresh()`. (ticket 0011)
