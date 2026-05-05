/**
 * Pure classifier for floorplan markers (ticket 0021).
 * Decides the visual state of a marker from the device's reported
 * deviceState plus the freshness of its latest sample.
 */

export type MarkerState =
  | "fresh-active"
  | "fresh-maintenance"
  | "inactive"
  | "stale"
  | "no-data";

export const STALE_AFTER_MS = 5 * 60_000;

export function classifyMarker(input: {
  deviceState: string | null | undefined;
  lastSampleIso: string | null | undefined;
  staleAfterMs?: number;
  now?: number;
}): MarkerState {
  const { deviceState, lastSampleIso } = input;
  const staleAfterMs = input.staleAfterMs ?? STALE_AFTER_MS;
  const now = input.now ?? Date.now();
  if (!lastSampleIso) return "no-data";
  const ts = new Date(lastSampleIso).getTime();
  if (Number.isNaN(ts)) return "no-data";
  if (now - ts > staleAfterMs) return "stale";
  if (deviceState === "maintenance") return "fresh-maintenance";
  if (deviceState === "active") return "fresh-active";
  return "inactive";
}
