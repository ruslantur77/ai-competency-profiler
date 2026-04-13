// frontend/src/components/VacancyList.jsx
import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'  // ← добавили useLocation
import { Plus, Loader2, CheckCircle, ExternalLink, AlertCircle, LogOut, FileEdit } from 'lucide-react'
import { listVacancies, createVacancy } from '../api/client'
import CreateVacancyDialog from './CreateVacancyDialog'
import './VacancyList.css'

const ALL_STATUSES = ['pending', 'draft', 'ready', 'failed']

const STATUS_CONFIG = {
  pending: {
    label: 'Извлечение компетенций...',
    badge: 'extracting',
    icon: (size) => <Loader2 size={size} className="spin" />,
  },
  draft: {
    label: 'Ожидает валидации',
    badge: 'draft',
    icon: (size) => <FileEdit size={size} />,
  },
  ready: {
    label: 'Готово к редактированию',
    badge: 'ready',
    icon: (size) => <CheckCircle size={size} />,
  },
  failed: {
    label: 'Ошибка обработки, попробуйте позже',
    badge: 'failed',
    icon: (size) => <AlertCircle size={size} />,
  },
}

export default function VacancyList({ notify, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()  // ← добавили
  const [vacancies, setVacancies] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  const fetchVacancies = useCallback(async () => {
    try {
      const results = await Promise.all(
        ALL_STATUSES.map(status => listVacancies(status).then(r => r.data))
      )
      const all = results
        .flat()
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      setVacancies(all)
    } catch {
      notify('Ошибка загрузки вакансий', 'error')
    } finally {
      setLoading(false)
    }
  }, [notify])

  // Первичная загрузка
  useEffect(() => {
    fetchVacancies()
  }, [fetchVacancies])

  // ← Перезагружаем список каждый раз когда возвращаемся на "/"
  // location.key меняется при каждой навигации, даже если pathname тот же
  useEffect(() => {
    fetchVacancies()
  }, [location.key])  // eslint-disable-line react-hooks/exhaustive-deps

  // Поллинг пока есть pending
  useEffect(() => {
    const hasPending = vacancies.some(v => v.status === 'pending')
    if (!hasPending) return
    const interval = setInterval(fetchVacancies, 3000)
    return () => clearInterval(interval)
  }, [vacancies, fetchVacancies])

  const handleCreate = async (data) => {
    try {
      await createVacancy(data)
      setCreating(false)
      await fetchVacancies()
      notify(`✅ Вакансия "${data.name}" создана, запущено извлечение компетенций`)
    } catch {
      notify('Ошибка создания вакансии', 'error')
    }
  }

  const handleOpen = (vacancy) => {
    if (vacancy.status === 'ready' || vacancy.status === 'draft') {
      navigate(`/vacancy/${vacancy.id}`)
    }
  }

  const handleLogout = async () => {
    try {
      await onLogout()
    } catch {
      // игнорируем
    }
  }

  const isClickable = (status) => status === 'ready' || status === 'draft'

  return (
    <div className="vacancy-list">
      <div className="vacancy-list__header">
        <div className="vacancy-list__title">
          <h1>🎯 Competency Profiler</h1>
          <p>Формирование компетентностного профиля специалиста</p>
        </div>
        <div className="vacancy-list__header-actions">
          <button className="btn-primary" onClick={() => setCreating(true)}>
            <Plus size={18} /> Создать вакансию
          </button>
          <button className="btn-secondary vacancy-list__logout" onClick={handleLogout}>
            <LogOut size={18} />
          </button>
        </div>
      </div>

      <div className="vacancy-list__content">
        {loading ? (
          <div className="vacancy-list__loading">
            <div className="spinner" />
            <p>Загрузка...</p>
          </div>
        ) : vacancies.length === 0 ? (
          <div className="vacancy-list__empty">
            <p>📋 Вакансий пока нет</p>
            <p>Создайте первую вакансию для формирования профиля компетенций</p>
            <button className="btn-primary" onClick={() => setCreating(true)}>
              <Plus size={18} /> Создать вакансию
            </button>
          </div>
        ) : (
          <div className="vacancy-list__grid">
            {vacancies.map(vac => {
              const config = STATUS_CONFIG[vac.status] || STATUS_CONFIG.pending
              const clickable = isClickable(vac.status)

              return (
                <div
                  key={vac.id}
                  className={`vacancy-card vacancy-card--${vac.status} ${clickable ? 'vacancy-card--clickable' : ''}`}
                  onClick={() => handleOpen(vac)}
                >
                  <div className="vacancy-card__header">
                    <h3>{vac.name}</h3>
                  </div>

                  <div className="vacancy-card__status">
                    <span className={`vacancy-card__badge vacancy-card__badge--${config.badge}`}>
                      {config.icon(14)}
                      {config.label}
                    </span>
                  </div>

                  <div className="vacancy-card__footer">
                    <span className="vacancy-card__date">
                      {new Date(vac.created_at).toLocaleDateString('ru-RU')}
                    </span>
                    {clickable && (
                      <span className="vacancy-card__open">
                        Открыть <ExternalLink size={14} />
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {creating && (
        <CreateVacancyDialog
          onClose={() => setCreating(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  )
}