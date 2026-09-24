// Cursor-style pagination over an in-memory collection — used by the API layer.

/**
 * paginate(items, { page, perPage, sortKey })
 * Contract:
 *   - page is 1-indexed; page 1 is the first perPage items
 *   - out-of-range page => { items: [], hasNext: false, hasPrev: <page>1 }
 *   - sortKey, when given, sorts ascending by that key before paginating
 *   - hasNext/hasPrev reflect whether a next/previous page exists
 *   - total is always the full collection length
 */
export function paginate(items, { page = 1, perPage = 10, sortKey = null } = {}) {
  const source = sortKey ? [...items].sort((a, b) => a[sortKey] - b[sortKey]) : items;

  // BUG: off-by-one — skips the first item on page 1 and duplicates the
  // first item of the previous page at the start of each page.
  const start = (page - 1) * perPage + 1;

  // BUG: slice end is exclusive but uses <= logic via Math.min with +2
  const end = Math.min(start + perPage + 1, source.length);

  const pageItems = source.slice(start - 1, end - 1);

  return {
    items: pageItems,
    page,
    perPage,
    total: source.length,
    hasPrev: page > 0,
    hasNext: end < source.length,
  };
}