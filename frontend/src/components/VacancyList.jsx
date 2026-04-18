// frontend/src/components/VacancyList.jsx
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Plus,
  Loader2,
  CheckCircle,
  ExternalLink,
  AlertCircle,
  LogOut,
  FileEdit,
  Trash2,
  RotateCcw,
  ShieldAlert,
} from 'lucide-react'
import {
  listVacancies,
  listVacanciesForReview,
  createVacancy,
  updateVacancyStatus,
  deleteVacancy,
  restoreVacancy,
  hardDeleteVacancy,
} from '../api/vacancies'
import { extractItems } from '../api/adapters'
import { getErrorMessage } from '../api/errors'
import {
  canAccessAdminUsers,
  canAccessCandidates,
  canAccessOntology,
  canAccessRanking,
  canAccessReviewQueue,
  canAccessTasks,
  canAccessVacancies,
  canCreateVacancy,
} from '../api/roles'
import CreateVacancyDialog from './CreateVacancyDialog'
import RankingTab from './RankingTab'
import TasksTab from './TasksTab'
import AsyncState from './AsyncState'
import OntologyTab from './OntologyTab'
import SectionStub from './SectionStub'
import ConfirmDialog from './ConfirmDialog'
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
    label: 'Граф финализирован',
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
  const [vacancyMode, setVacancyMode] = useState('all')
  const [updatingStatusId, setUpdatingStatusId] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)
  const [recentlyDeleted, setRecentlyDeleted] = useState([])
  const pollCycleRef = useRef(0)
  const canSeeVacancies = canAccessVacancies(role)
  const canSeeTasks = canAccessTasks(role)
  const canSeeRanking = canAccessRanking(role)
  const canSeeOntology = canAccessOntology(role)
  const canSeeCandidates = canAccessCandidates(role)
  const canSeeAdminUsers = canAccessAdminUsers(role)
  const canSeeReviewQueue = canAccessReviewQueue(role)
  const canCreate = canCreateVacancy(role)
  const tabs = useMemo(() => ([
    ...(canSeeVacancies ? [{ id: 'vacancies', label: '📋 Вакансии' }] : []),
    ...(canSeeTasks ? [{ id: 'tasks', label: '📝 Задания' }] : []),
    ...(canSeeRanking ? [{ id: 'ranking', label: '🏆 Ранжирование' }] : []),
    ...(canSeeOntology ? [{ id: 'ontology', label: '🧩 Онтология' }] : []),
    ...(canSeeCandidates ? [{ id: 'candidates', label: '👤 Кандидаты' }] : []),
    ...(canSeeAdminUsers ? [{ id: 'admin-users', label: '🛡️ Пользователи' }] : []),
  ]), [
    canSeeVacancies,
    canSeeTasks,
    canSeeRanking,
    canSeeOntology,
    canSeeCandidates,
    canSeeAdminUsers,
  ])

  useEffect(() => {
    if (!tabs.some(tab => tab.id === activeTab)) {
      setActiveTab(tabs[0]?.id || 'vacancies')
    }
  }, [tabs, activeTab])

  useEffect(() => {
    if (!canSeeReviewQueue && vacancyMode === 'review') {
      setVacancyMode('all')
    }
  }, [canSeeReviewQueue, vacancyMode])

  const fetchVacancies = useCallback(async (options = {}) => {
    const { silent = false } = options
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
      }
    } catch (error) {
      setVacancies([])
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки вакансий' }), 'error')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [notify, vacancyMode])

  useEffect(() => {
    if (!canSeeVacancies) {
      setVacancies([])
      setLoading(false)
      return
    }
    fetchVacancies()
  }, [fetchVacancies, canSeeVacancies])

  useEffect(() => {
    if (!canSeeVacancies) return
    fetchVacancies()
  }, [location.key, canSeeVacancies]) // eslint-disable-line react-hooks/exhaustive-deps

  // Умный polling: только когда есть pending, вкладка видима и пользователь в табе вакансий.
  useEffect(() => {
    const hasPending = vacancies.some(v => v.status === 'pending')
    if (
      !canSeeVacancies
      || vacancyMode !== 'all'
      || !hasPending
      || activeTab !== 'vacancies'
    ) {
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
  }, [vacancies, fetchVacancies, activeTab, canSeeVacancies, vacancyMode])

  const handleCreate = async (data) => {
    try {
      if (!canCreate) {
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

  const handleStatusChange = async (vacancyId, nextStatus) => {
    setUpdatingStatusId(vacancyId)
    try {
      await updateVacancyStatus(vacancyId, nextStatus)
      notify('Статус вакансии обновлен')
      await fetchVacancies({ silent: true })
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка обновления статуса' }), 'error')
    } finally {
      setUpdatingStatusId(null)
    }
  }

  const openDeleteConfirm = (vacancy) => {
    setConfirmAction({
      type: 'delete',
      vacancy,
      title: 'Удаление вакансии',
      message: `Удалить вакансию "${vacancy.name}"? Вакансию можно будет восстановить из панели удаленных.`,
      confirmLabel: 'Удалить',
    })
  }

  const openHardDeleteConfirm = (vacancy) => {
    setConfirmAction({
      type: 'hard-delete',
      vacancy,
      title: 'Полное удаление вакансии',
      message: `Полностью удалить "${vacancy.name}" без возможности восстановления?`,
      confirmLabel: 'Удалить навсегда',
      requireText: vacancy.name,
      requireHint: `Для подтверждения введите точное название: ${vacancy.name}`,
    })
  }

  const handleConfirmAction = async () => {
    if (!confirmAction?.vacancy) return

    const { type, vacancy } = confirmAction
    try {
      if (type === 'delete') {
        await deleteVacancy(vacancy.id)
        setRecentlyDeleted((prev) => [
          { id: vacancy.id, name: vacancy.name, deletedAt: new Date().toISOString() },
          ...prev.filter((item) => item.id !== vacancy.id),
        ].slice(0, 5))
        notify('Вакансия удалена')
      } else if (type === 'hard-delete') {
        await hardDeleteVacancy(vacancy.id)
        setRecentlyDeleted((prev) => prev.filter((item) => item.id !== vacancy.id))
        notify('Вакансия удалена без возможности восстановления')
      }
      setConfirmAction(null)
      await fetchVacancies({ silent: true })
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка выполнения операции' }), 'error')
    }
  }

  const handleRestore = async (vacancy) => {
    try {
      await restoreVacancy(vacancy.id)
      notify(`Вакансия "${vacancy.name}" восстановлена`)
      setRecentlyDeleted((prev) => prev.filter((item) => item.id !== vacancy.id))
      await fetchVacancies({ silent: true })
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка восстановления вакансии' }), 'error')
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
          {activeTab === 'vacancies' && canCreate && (
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
            <>
              <div className="vacancy-list__mode">
                <button
                  className={`vacancy-list__mode-btn ${vacancyMode === 'all' ? 'is-active' : ''}`}
                  onClick={() => setVacancyMode('all')}
                >
                  Все вакансии
                </button>
                {canSeeReviewQueue && (
                  <button
                    className={`vacancy-list__mode-btn ${vacancyMode === 'review' ? 'is-active' : ''}`}
                    onClick={() => setVacancyMode('review')}
                  >
                    Review queue
                  </button>
                )}
              </div>

              {loading ? (
                <AsyncState kind="loading" title="Загрузка вакансий..." />
              ) : vacancies.length === 0 ? (
                <AsyncState
                  kind="empty"
                  title="📋 Вакансий пока нет"
                  hint={canCreate
                    ? 'Создайте первую вакансию для формирования профиля компетенций'
                    : 'Вакансий пока нет'}
                  actionLabel={canCreate ? 'Создать вакансию' : undefined}
                  onAction={canCreate ? () => setCreating(true) : undefined}
                />
              ) : (
                <>
                  {recentlyDeleted.length > 0 && (
                <div className="vacancy-list__deleted-panel">
                  <h4>
                    <RotateCcw size={16} /> Недавно удаленные
                  </h4>
                  <div className="vacancy-list__deleted-list">
                    {recentlyDeleted.map((item) => (
                      <div key={item.id} className="vacancy-list__deleted-item">
                        <span>{item.name}</span>
                        <div className="vacancy-list__deleted-actions">
                          <button className="btn-secondary" onClick={() => handleRestore(item)}>
                            Восстановить
                          </button>
                          <button
                            className="btn-danger"
                            onClick={() => openHardDeleteConfirm(item)}
                            title="Полное удаление без восстановления"
                          >
                            <ShieldAlert size={14} /> Hard delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                  )}

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
                            <div className="vacancy-card__actions" onClick={(event) => event.stopPropagation()}>
                              <button
                                title="Удалить вакансию"
                                onClick={() => openDeleteConfirm(vac)}
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
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
                            <div className="vacancy-card__controls" onClick={(event) => event.stopPropagation()}>
                              <select
                                value={vac.status}
                                onChange={(event) => handleStatusChange(vac.id, event.target.value)}
                                disabled={updatingStatusId === vac.id}
                              >
                                {Object.keys(STATUS_CONFIG).map((statusKey) => (
                                  <option key={statusKey} value={statusKey}>
                                    {statusKey}
                                  </option>
                                ))}
                              </select>
                              {clickable && (
                                <span className="vacancy-card__open">
                                  Открыть <ExternalLink size={14} />
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </>
              )}
            </>
        )}

        {activeTab === 'vacancies' && confirmAction && (
          <ConfirmDialog
            title={confirmAction.title}
            message={confirmAction.message}
            confirmLabel={confirmAction.confirmLabel}
            requireText={confirmAction.requireText}
            requireHint={confirmAction.requireHint}
            onConfirm={handleConfirmAction}
            onCancel={() => setConfirmAction(null)}
          />
        )}

        {/* ЗАДАНИЯ */}
        {activeTab === 'tasks' && (
          <TasksTab notify={notify} />
        )}

        {/* РАНЖИРОВАНИЕ */}
        {activeTab === 'ranking' && (
          <RankingTab vacancies={readyVacancies} notify={notify} />
        )}

        {/* ОНТОЛОГИЯ */}
        {activeTab === 'ontology' && (
          <OntologyTab notify={notify} />
        )}

        {/* КАНДИДАТЫ */}
        {activeTab === 'candidates' && (
          <SectionStub
            title="👤 Кандидаты"
            hint="Каркас раздела создан в итерации 1. Список, профили и операции будут добавлены далее."
          />
        )}

        {/* ADMIN USERS */}
        {activeTab === 'admin-users' && (
          <SectionStub
            title="🛡️ Управление пользователями"
            hint="Каркас раздела создан в итерации 1. Полноценный user-management будет реализован далее."
          />
        )}
      </div>

      {creating && canCreate && (
        <CreateVacancyDialog
          onClose={() => setCreating(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  )
}
