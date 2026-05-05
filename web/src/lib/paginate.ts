export const PAGE_SIZE = 100;

export interface PageResult<T> {
  page: number;
  totalPages: number;
  items: T[];
}

export function paginate<T>(
  items: T[],
  page: number,
  pageSize: number = PAGE_SIZE,
): PageResult<T> {
  const total = items.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const clamped = Math.min(Math.max(1, page), totalPages);
  const start = (clamped - 1) * pageSize;
  return {
    page: clamped,
    totalPages,
    items: items.slice(start, start + pageSize),
  };
}
