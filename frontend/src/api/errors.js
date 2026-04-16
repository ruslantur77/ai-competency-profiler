const STATUS_MESSAGES = {
  400: 'Некорректный запрос',
  401: 'Сессия истекла. Войдите снова',
  403: 'Недостаточно прав для выполнения операции',
  404: 'Ресурс не найден',
  409: 'Конфликт данных. Обновите страницу и повторите',
  422: 'Ошибка валидации данных',
  429: 'Слишком много запросов. Попробуйте позже',
  500: 'Внутренняя ошибка сервера',
  502: 'Сервер временно недоступен',
  503: 'Сервис временно недоступен',
  504: 'Сервер не ответил вовремя',
}

const normalizeDetail = (detail) => {
  if (!detail) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        const path = Array.isArray(item?.loc) ? item.loc.join('.') : null
        return path && item?.msg ? `${path}: ${item.msg}` : item?.msg
      })
      .filter(Boolean)
      .join('; ')
  }
  return null
}

export const getErrorMessage = (error, options = {}) => {
  const { fallback = 'Ошибка запроса', overrides = {} } = options
  const status = error?.response?.status
  const localMessage = typeof error?.message === 'string' ? error.message.trim() : ''

  if (status && overrides[status]) {
    return overrides[status]
  }

  if (status === 422) {
    const detail422 = normalizeDetail(error?.response?.data?.detail)
    return detail422 || overrides[422] || STATUS_MESSAGES[422]
  }

  const detail = normalizeDetail(error?.response?.data?.detail)
  if (detail && status && status < 500) {
    return detail
  }

  if (status && STATUS_MESSAGES[status]) {
    return STATUS_MESSAGES[status]
  }

  if (error?.code === 'ECONNABORTED') {
    return 'Превышено время ожидания ответа сервера'
  }

  if (!status && localMessage) {
    return localMessage
  }

  if (!status) {
    return 'Ошибка сети. Проверьте подключение и повторите'
  }

  return fallback
}
