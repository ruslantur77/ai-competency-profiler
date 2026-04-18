import { useCallback, useState } from 'react'
import { listVacancies, listVacanciesForReview } from '../api/vacancies'
import { extractItems } from '../api/adapters'
import { getErrorMessage } from '../api/errors'

const ALL_STATUSES = ['pending', 'draft', 'ready', 'failed']

export default function useVacanciesData({ notify, vacancyMode }) {
  const [vacancies, setVacancies] = useState([])
  const [allVacancies, setAllVacancies] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchVacancies = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    try {
      if (vacancyMode === 'review') {
        const { data } = await listVacanciesForReview()
        const reviewItems = extractItems(data).sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at)
        )
        setVacancies(reviewItems)
      } else {
        const responses = await Promise.allSettled(
          ALL_STATUSES.map((status) => listVacancies(status))
        )
        const fulfilled = responses.filter((result) => result.status === 'fulfilled')
        const all = fulfilled
          .flatMap((result) => extractItems(result.value.data))
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

        setVacancies(all)
        setAllVacancies(all)

        if (fulfilled.length === 0) {
          notify('Ошибка загрузки вакансий', 'error')
        } else if (fulfilled.length < ALL_STATUSES.length) {
          notify('Часть вакансий не загрузилась, повторите позже', 'error')
        }
      }
    } catch (error) {
      setVacancies([])
      if (vacancyMode !== 'review') {
        setAllVacancies([])
      }
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки вакансий' }), 'error')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [notify, vacancyMode])

  return {
    vacancies,
    allVacancies,
    loading,
    fetchVacancies,
    setLoading,
    setVacancies,
  }
}
