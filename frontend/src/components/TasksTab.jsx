import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckCircle, Clock, AlertCircle, ExternalLink, Loader2 } from 'lucide-react'
import { finalizeTaskGraph, listTasks } from '../api/tasks'
import { fetchAllPages } from '../api/pagination'
import { getErrorMessage } from '../api/errors'
import ForbiddenState from './ForbiddenState'
import AsyncState from './AsyncState'
import TaskGraphDialog from './TaskGraphDialog'
import TaskStats from './tasks/TaskStats'
import './TasksTab.css'

const TASK_STATUS_CONFIG = {
  pending: {
    label: 'Ожидает маппинга',
    icon: (size) => <Clock size={size} />,
    badge: 'pending',
  },
  draft: {
    label: 'Черновик графа',
    icon: (size) => <ExternalLink size={size} />,
    badge: 'draft',
  },
  ready: {
    label: 'Граф готов',
    icon: (size) => <CheckCircle size={size} />,
    badge: 'completed',
  },
  failed: {
    label: 'Ошибка обработки',
    icon: (size) => <AlertCircle size={size} />,
    badge: 'failed',
  },
}

const TASK_TYPE_LABELS = {
  code: '💻 Код',
  test: '📝 Тест',
}

function TaskCard({ task, onOpenGraph, onFinalize, finalizing }) {
  const statusConfig = TASK_STATUS_CONFIG[task.status] || TASK_STATUS_CONFIG.pending
  const canFinalize = task.status === 'draft'
  const createdAtLabel = task.created_at
    ? new Date(task.created_at).toLocaleString('ru-RU')
    : '—'

  return (
    <div className={`task-card task-card--${statusConfig.badge}`}>
      <div className="task-card__header task-card__header--static">
        <div className="task-card__header-left">
          <div className="task-card__info">
            <span className="task-card__title">{task.title}</span>
            <span className="task-card__type">{TASK_TYPE_LABELS[task.type] || task.type}</span>
          </div>
        </div>
        <div className="task-card__header-right">
          <span className={`task-card__badge task-card__badge--${statusConfig.badge}`}>
            {statusConfig.icon(13)}
            {statusConfig.label}
          </span>
          <button
            className="task-card__btn"
            onClick={() => onOpenGraph(task.id)}
            title="Открыть граф задачи"
          >
            <ExternalLink size={14} />
            Граф
          </button>
          {canFinalize && (
            <button
              className="task-card__btn task-card__btn--validate"
              onClick={() => onFinalize(task.id)}
              disabled={finalizing}
              title="Finalize task graph"
            >
              {finalizing ? <Loader2 size={14} className="spin" /> : <CheckCircle size={14} />}
              Finalize
            </button>
          )}
        </div>
      </div>

      <div className="task-card__body">
        <p className="task-card__description">{task.description || 'Описание не задано'}</p>
        <div className="task-card__meta">
          <span>ID: {task.external_id}</span>
          <span>Создано: {createdAtLabel}</span>
        </div>
      </div>
    </div>
  )
}

export default function TasksTab({ notify }) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [isForbidden, setIsForbidden] = useState(false)
  const [selectedTaskId, setSelectedTaskId] = useState(null)
  const [finalizingId, setFinalizingId] = useState(null)

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    try {
      const allPages = await fetchAllPages({
        fetchPage: async ({ limit, offset }) => {
          const { data } = await listTasks({ limit, offset })
          return data
        },
      })
      setTasks(allPages.items)
      setIsForbidden(false)
    } catch (error) {
      setTasks([])
      setIsForbidden(error?.response?.status === 403)
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки заданий' }), 'error')
    } finally {
      setLoading(false)
    }
  }, [notify])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  const handleFinalize = async (taskId) => {
    setFinalizingId(taskId)
    try {
      const { data } = await finalizeTaskGraph(taskId)
      setTasks((prev) => prev.map((task) => (task.id === taskId ? { ...task, ...data } : task)))
      notify('Граф задачи финализирован')
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка финализации графа задачи' }), 'error')
    } finally {
      setFinalizingId(null)
    }
  }

  const counters = useMemo(() => {
    const pending = tasks.filter((task) => task.status === 'pending').length
    const draft = tasks.filter((task) => task.status === 'draft').length
    const ready = tasks.filter((task) => task.status === 'ready').length
    const failed = tasks.filter((task) => task.status === 'failed').length
    return { total: tasks.length, pending, draft, ready, failed }
  }, [tasks])

  if (loading) {
    return <AsyncState kind="loading" title="Загрузка заданий..." />
  }

  if (isForbidden) {
    return (
      <ForbiddenState hint="Раздел заданий доступен только ролям EXPERT и ADMIN." />
    )
  }

  if (tasks.length === 0) {
    return (
      <AsyncState
        kind="empty"
        title="📝 Заданий пока нет"
        hint="Задания появятся после синхронизации с тестирующей системой"
      />
    )
  }

  return (
    <div className="tasks-tab">
      <TaskStats counters={counters} />

      <div className="tasks-tab__list">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onOpenGraph={setSelectedTaskId}
            onFinalize={handleFinalize}
            finalizing={finalizingId === task.id}
          />
        ))}
      </div>

      {selectedTaskId && (
        <TaskGraphDialog
          taskId={selectedTaskId}
          notify={notify}
          onClose={() => setSelectedTaskId(null)}
          onUpdated={fetchTasks}
        />
      )}
    </div>
  )
}
