import type { QueryClient } from "@tanstack/react-query";

/**
 * Optimistically remove items matching `match` from the cached list at
 * `queryKey`. Returns a `rollback()` thunk that restores the snapshot.
 *
 * Usage:
 *   const { rollback } = optimisticListDelete<Device>(qc, ["devices"], (d) => d.id === id);
 *   try { await api.delete(id); } catch (e) { rollback(); throw e; }
 */
export function optimisticListDelete<I>(
  qc: QueryClient,
  queryKey: unknown[],
  match: (item: I) => boolean,
): { rollback: () => void } {
  const previous = qc.getQueryData<I[]>(queryKey);
  if (previous) {
    qc.setQueryData<I[]>(
      queryKey,
      previous.filter((item) => !match(item)),
    );
  }
  return {
    rollback: () => {
      if (previous) qc.setQueryData(queryKey, previous);
    },
  };
}
