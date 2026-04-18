import { normalizePageResponse } from './adapters';

export async function fetchAllPages({ fetchPage, limit = 100, initialOffset = 0, maxPages = 100 }) {
  let offset = initialOffset;
  let pageCount = 0;
  let total = null;
  const items = [];

  while (pageCount < maxPages) {
    const payload = await fetchPage({ limit, offset });
    const page = normalizePageResponse(payload);
    const pageItems = Array.isArray(page.items) ? page.items : [];

    if (Number.isFinite(page.total)) {
      total = page.total;
    }

    items.push(...pageItems);

    if (pageItems.length === 0) break;
    if (total !== null && items.length >= total) break;

    const step = page.limit > 0 ? page.limit : limit;
    if (step <= 0) break;

    offset += step;
    pageCount += 1;
  }

  return {
    items,
    total: total ?? items.length,
    limit,
    offset: initialOffset,
  };
}
