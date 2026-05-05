export type Freshness = "fresh" | "stale" | "no-data";

/**
 * Classify a server-reported timestamp relative to the polling interval.
 * - `no-data` if the timestamp is missing.
 * - `fresh`   if it is younger than 4 × pollSeconds.
 * - `stale`   otherwise.
 *
 * The 4× factor leaves room for one missed tick plus normal drift.
 */
export function freshnessOf(
  iso: string | undefined | null,
  pollSeconds = 15,
  now: number = Date.now(),
): Freshness {
  if (!iso) return "no-data";
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "no-data";
  const ageS = (now - ts) / 1000;
  if (ageS < pollSeconds * 4) return "fresh";
  return "stale";
}
