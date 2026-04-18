export const formatDateTime = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleString('ru-RU')
}

export const formatPercent = (value, { normalized = true } = {}) => {
  const numeric = Number.isFinite(value) ? value : 0
  const base = normalized ? numeric * 100 : numeric
  return `${Math.round(base)}%`
}
