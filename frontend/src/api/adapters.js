export const normalizePageResponse = (payload) => {
  const source = payload?.data && !Array.isArray(payload?.data) ? payload.data : payload

  if (Array.isArray(payload)) {
    return {
      items: payload,
      total: payload.length,
      limit: payload.length,
      offset: 0,
    }
  }

  const items = Array.isArray(source?.items)
    ? source.items
    : Array.isArray(source?.results)
      ? source.results
      : []
  const total = Number.isFinite(source?.total)
    ? source.total
    : Number.isFinite(source?.count)
      ? source.count
      : items.length
  const limit = Number.isFinite(source?.limit)
    ? source.limit
    : Number.isFinite(source?.page_size)
      ? source.page_size
      : items.length
  const offset = Number.isFinite(source?.offset)
    ? source.offset
    : Number.isFinite(source?.skip)
      ? source.skip
      : 0

  return {
    items,
    total,
    limit,
    offset,
  }
}

export const extractItems = (payload) => normalizePageResponse(payload).items
