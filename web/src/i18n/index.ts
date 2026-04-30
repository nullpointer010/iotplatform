import "server-only";
import { cookies } from "next/headers";

export const LOCALES = ["es", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "es";
export const LOCALE_COOKIE = "NEXT_LOCALE";

export function getLocale(): Locale {
  const value = cookies().get(LOCALE_COOKIE)?.value as Locale | undefined;
  return value && LOCALES.includes(value) ? value : DEFAULT_LOCALE;
}

export async function loadMessages(locale: Locale) {
  return (await import(`./messages/${locale}.json`)).default as Record<
    string,
    unknown
  >;
}
