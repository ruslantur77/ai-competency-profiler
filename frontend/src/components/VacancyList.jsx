// frontend/src/components/VacancyList.jsx
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Plus, Loader2, CheckCircle, ExternalLink, AlertCircle, LogOut, FileEdit } from 'lucide-react'
import { listVacancies, createVacancy } from '../api/vacancies'
import { extractItems } from '../api/adapters'
import { getErrorMessage } from '../api/errors'
import { canAccessTasks, canEditGraph } from '../api/roles'
import CreateVacancyDialog from './CreateVacancyDialog'
import RankingTab from './RankingTab'
import TasksTab from './TasksTab'
import AsyncState from './AsyncState'
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

export default function VacancyList({ notify, onLogout, role }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [activeTab, setActiveTab] = useState('vacancies')
  const [vacancies, setVacancies] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const pollCycleRef = useRef(0)
  const canEdit = canEditGraph(role)
  const tabs = useMemo(() => ([
    { id: 'vacancies', label: '📋 Вакансии' },
    ...(canAccessTasks(role) ? [{ id: 'tasks', label: '📝 Задания' }] : []),
    { id: 'ranking', label: '🏆 Ранжирование' },
  ]), [role])

  useEffect(() => {
    if (!tabs.some(tab => tab.id === activeTab)) {
      setActiveTab('vacancies')
    }
  }, [tabs, activeTab])

  const fetchVacancies = useCallback(async (options = {}) => {
    const { silent = false } = options
    if (!silent) setLoading(true)
    try {
      const responses = await Promise.allSettled(
        ALL_STATUSES.map(status => listVacancies(status))
      )
      const fulfilled = responses.filter(result => result.status === 'fulfilled')
      const all = fulfilled
        .flatMap(result => extractItems(result.value.data))
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      setVacancies(all)

      if (fulfilled.length === 0) {
        notify('Ошибка загрузки вакансий', 'error')
      } else if (fulfilled.length < ALL_STATUSES.length) {
        notify('Часть вакансий не загрузилась, повторите позже', 'error')
      }
    } catch (error) {
      setVacancies([])
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки вакансий' }), 'error')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [notify])

  useEffect(() => {
    fetchVacancies()
  }, [fetchVacancies])

  useEffect(() => {
    fetchVacancies()
  }, [location.key]) // eslint-disable-line react-hooks/exhaustive-deps

  // Умный polling: только когда есть pending, вкладка видима и пользователь в табе вакансий.
  useEffect(() => {
    const hasPending = vacancies.some(v => v.status === 'pending')
    if (!hasPending || activeTab !== 'vacancies') {
      pollCycleRef.current = 0
      return
    }

    if (document.hidden) return

    const cycle = pollCycleRef.current + 1
    pollCycleRef.current = cycle
    const delayMs = Math.min(15000, 3000 + cycle * 1000)
    if (cycle > 40) return

    const timer = setTimeout(() => {
      fetchVacancies({ silent: true })
    }, delayMs)
    return () => clearTimeout(timer)
  }, [vacancies, fetchVacancies, activeTab])

  const handleCreate = async (data) => {
    try {
      if (!canEdit) {
        notify('Недостаточно прав для создания вакансии', 'error')
        return
      }
      await createVacancy(data)
      setCreating(false)
      await fetchVacancies()
      notify(`✅ Вакансия "${data.name}" создана, запущено извлечение компетенций`)
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка создания вакансии' }), 'error')
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
      // logout имеет централизованный fallback в App; здесь не дублируем уведомление
    }
  }

  const isClickable = (status) => status === 'ready' || status === 'draft'

  // Только ready вакансии для ранжирования
  const readyVacancies = vacancies.filter(v => v.status === 'ready')

  return (
    <div className="vacancy-list">
      {/* ===== HEADER ===== */}
      <div className="vacancy-list__header">
        <div className="vacancy-list__title">
          <h1>🎯 Competency Profiler</h1>
          <p>Формирование компетентностного профиля специалиста</p>
        </div>
        <div className="vacancy-list__header-actions">
          {activeTab === 'vacancies' && canEdit && (
            <button className="btn-primary" onClick={() => setCreating(true)}>
              <Plus size={18} /> Создать вакансию
            </button>
          )}
          <button className="btn-secondary vacancy-list__logout" onClick={handleLogout}>
            <LogOut size={18} />
          </button>
        </div>
      </div>

      {/* ===== ТАБЫ ===== */}
      <div className="vacancy-list__tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`vacancy-list__tab ${activeTab === tab.id ? 'vacancy-list__tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ===== КОНТЕНТ ===== */}
      <div className="vacancy-list__content">

        {/* ВАКАНСИИ */}
        {activeTab === 'vacancies' && (
          loading ? (
            <AsyncState kind="loading" title="Загрузка вакансий..." />
          ) : vacancies.length === 0 ? (
            <AsyncState
              kind="empty"
              title="📋 Вакансий пока нет"
              hint={canEdit
                ? 'Создайте первую вакансию для формирования профиля компетенций'
                : 'Вакансий пока нет'}
              actionLabel={canEdit ? 'Создать вакансию' : undefined}
              onAction={canEdit ? () => setCreating(true) : undefined}
            />
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
          )
        )}

        {/* ЗАДАНИЯ */}
        {activeTab === 'tasks' && (
          <TasksTab notify={notify} />
        )}

        {/* РАНЖИРОВАНИЕ */}
        {activeTab === 'ranking' && (
          <RankingTab vacancies={readyVacancies} notify={notify} />
        )}
      </div>

      {creating && canEdit && (
        <CreateVacancyDialog
          onClose={() => setCreating(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  )
}
