import { useCallback, useState } from 'react';
import { listVacancies, listVacanciesForReview } from '../api/vacancies';
import { fetchAllPages } from '../api/pagination';
import { getErrorMessage } from '../api/errors';

const ALL_STATUSES = ['pending', 'draft', 'ready', 'failed'];

export default function useVacanciesData({ notify, vacancyMode }) {
  const [vacancies, setVacancies] = useState([]);
  const [allVacancies, setAllVacancies] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchVacancies = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) setLoading(true)
      try {
        if (vacancyMode === 'review') {
          const reviewPages = await fetchAllPages({
            fetchPage: async ({ limit, offset }) => {
              const { data } = await listVacanciesForReview({ limit, offset })
              return data
            },
          })
          const reviewItems = reviewPages.items.sort(
            (a, b) => new Date(b.created_at) - new Date(a.created_at)
          )
          setVacancies(reviewItems)
        } else {
          // Всегда грузим все статусы
          const responses = await Promise.allSettled(
            ALL_STATUSES.map((status) =>
              fetchAllPages({
                fetchPage: async ({ limit, offset }) => {
                  const { data } = await listVacancies({
                    status_filter: status,
                    limit,
                    offset,
                  })
                  return data
                },
              })
            )
          )
          const fulfilled = responses.filter((r) => r.status === 'fulfilled')
          const all = fulfilled
            .flatMap((r) => r.value.items)
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  
          setAllVacancies(all)
  
          // Фильтруем по выбранному режиму
          const filtered = ['pending', 'draft', 'ready', 'failed'].includes(vacancyMode)
            ? all.filter((v) => v.status === vacancyMode)
            : all
  
          setVacancies(filtered)
  
          if (fulfilled.length === 0) {
            notify('Ошибка загрузки вакансий', 'error')
          } else if (fulfilled.length < ALL_STATUSES.length) {
            notify('Часть вакансий не загрузилась, повторите позже', 'error')
          }
        }
      } catch (error) {
        setVacancies([])
        if (vacancyMode !== 'review') setAllVacancies([])
        notify(getErrorMessage(error, { fallback: 'Ошибка загрузки вакансий' }), 'error')
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [notify, vacancyMode]
  );

  return {
    vacancies,
    allVacancies,
    loading,
    fetchVacancies,
    setLoading,
    setVacancies,
  };
}
