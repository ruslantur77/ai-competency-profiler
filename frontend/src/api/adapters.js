export const normalizePageResponse = (payload) => {
  if (Array.isArray(payload)) {
    return {
      items: payload,
      total: payload.length,
      limit: payload.length,
      offset: 0,
    }
  }

  return {
    items: Array.isArray(payload?.items) ? payload.items : [],
    total: Number.isFinite(payload?.total) ? payload.total : 0,
    limit: Number.isFinite(payload?.limit) ? payload.limit : 0,
    offset: Number.isFinite(payload?.offset) ? payload.offset : 0,
  }
}

export const extractItems = (payload) => normalizePageResponse(payload).items
