import { useCallback, useState } from 'react'
import { normalizePageResponse } from '../api/adapters'

export default function usePaginatedResource({
  fetchPage,
  initialLimit = 20,
  initialOffset = 0,
  onError = null,
}) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [limit, setLimit] = useState(initialLimit)
  const [offset, setOffset] = useState(initialOffset)
  const [loading, setLoading] = useState(true)

  const loadPage = useCallback(async ({
    offset: nextOffset = initialOffset,
    limit: nextLimit = initialLimit,
    silent = false,
  } = {}) => {
    if (!silent) setLoading(true)
    try {
      const payload = await fetchPage({ offset: nextOffset, limit: nextLimit })
      const page = normalizePageResponse(payload)
      setItems(page.items)
      setTotal(page.total)
      setOffset(Number.isFinite(page.offset) ? page.offset : nextOffset)
      setLimit(page.limit > 0 ? page.limit : nextLimit)
      return page
    } catch (error) {
      setItems([])
      setTotal(0)
      if (onError) onError(error)
      throw error
    } finally {
      if (!silent) setLoading(false)
    }
  }, [fetchPage, initialLimit, initialOffset, onError])

  return {
    items,
    total,
    limit,
    offset,
    loading,
    loadPage,
  }
}
