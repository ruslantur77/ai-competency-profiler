// frontend/src/components/TasksTab.jsx
import React, { useState, useEffect, useCallback } from 'react'
import { Loader2, CheckCircle, XCircle, Clock, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
import { listTasks, rebuildTaskMapping, validateTaskMapping } from '../api/client'
import './TasksTab.css'

const MAPPING_STATUS_CONFIG = {
  pending: {
    label: 'Ожидает маппинга',
    icon: (size) => <Clock size={size} />,
    badge: 'pending',
  },
  completed: {
    label: 'Маппинг готов',
    icon: (size) => <CheckCircle size={size} />,
    badge: 'completed',
  },
  failed: {
    label: 'Ошибка маппинга',
    icon: (size) => <XCircle size={size} />,
    badge: 'failed',
  },
}

const TASK_TYPE_LABELS = {
  code: '💻 Код',
  test: '📝 Тест',
}

function TaskCard({ task, onRebuild, onValidate, rebuilding, validating }) {
  const [expanded, setExpanded] = useState(false)
  const statusConfig = MAPPING_STATUS_CONFIG[task.mapping_status] || MAPPING_STATUS_CONFIG.pending

  return (
    <div className={`task-card task-card--${task.mapping_status}`}>
      <div className="task-card__header" onClick={() => setExpanded(e => !e)}>
        <div className="task-card__header-left">
          <button className="task-card__expand">
            {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
          <div className="task-card__info">
            <span className="task-card__title">{task.title}</span>
            <span className="task-card__type">{TASK_TYPE_LABELS[task.type] || task.type}</span>
          </div>
        </div>
        <div className="task-card__header-right" onClick={e => e.stopPropagation()}>
          <span className={`task-card__badge task-card__badge--${statusConfig.badge}`}>
            {statusConfig.icon(13)}
            {statusConfig.label}
          </span>
          {task.mapping_validated && (
            <span className="task-card__validated">✅ Валидировано</span>
          )}
          <button
            className="task-card__btn task-card__btn--rebuild"
            onClick={() => onRebuild(task.id)}
            disabled={rebuilding}
            title="Перестроить маппинг"
          >
            {rebuilding ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}
          </button>
          {task.mapping_status === 'completed' && !task.mapping_validated && (
            <button
              className="task-card__btn task-card__btn--validate"
              onClick={() => onValidate(task.id)}
              disabled={validating}
              title="Валидировать маппинг"
            >
              {validating ? <Loader2 size={14} className="spin" /> : <CheckCircle size={14} />}
              Валидировать
            </button>
          )}
        </div>
      </div>

      {expanded && (
        <div className="task-card__body">
          {task.description && (
            <p className="task-card__description">{task.description}</p>
          )}

          {task.mapping_error_message && (
            <div className="task-card__error">
              ⚠️ {task.mapping_error_message}
            </div>
          )}

          {task.competency_mappings.length > 0 ? (
            <div className="task-card__mappings">
              <span className="task-card__mappings-label">Маппинг компетенций:</span>
              {task.competency_mappings.map(m => (
                <div key={m.sub_competency_id} className="task-card__mapping-item">
                  <span className="task-card__mapping-id">
                    {m.sub_competency_id}
                  </span>
                  <span className="task-card__mapping-weight">
                    вес: {m.weight.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="task-card__no-mappings">Маппинг компетенций не задан</p>
          )}
        </div>
      )}
    </div>
  )
}

export default function TasksTab({ notify }) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [rebuildingId, setRebuildingId] = useState(null)
  const [validatingId, setValidatingId] = useState(null)

  const fetchTasks = useCallback(async () => {
    try {
      const { data } = await listTasks()
      setTasks(data)
    } catch {
      notify('Ошибка загрузки заданий', 'error')
    } finally {
      setLoading(false)
    }
  }, [notify])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  const handleRebuild = async (taskId) => {
    setRebuildingId(taskId)
    try {
      const { data } = await rebuildTaskMapping(taskId)
      setTasks(prev => prev.map(t => t.id === taskId ? data : t))
      notify('🔄 Маппинг перестроен')
    } catch {
      notify('Ошибка перестройки маппинга', 'error')
    } finally {
      setRebuildingId(null)
    }
  }

  const handleValidate = async (taskId) => {
    setValidatingId(taskId)
    try {
      const { data } = await validateTaskMapping(taskId)
      setTasks(prev => prev.map(t => t.id === taskId ? data : t))
      notify('✅ Маппинг валидирован')
    } catch {
      notify('Ошибка валидации маппинга', 'error')
    } finally {
      setValidatingId(null)
    }
  }

  if (loading) {
    return (
      <div className="tasks-tab__loading">
        <Loader2 size={24} className="spin" />
        <p>Загрузка заданий...</p>
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="tasks-tab__empty">
        <p>📝 Заданий пока нет</p>
        <p className="tasks-tab__empty-hint">
          Задания появятся после синхронизации с тестирующей системой
        </p>
      </div>
    )
  }

  const pending = tasks.filter(t => t.mapping_status === 'pending')
  const completed = tasks.filter(t => t.mapping_status === 'completed')
  const failed = tasks.filter(t => t.mapping_status === 'failed')

  return (
    <div className="tasks-tab">
      <div className="tasks-tab__stats">
        <div className="tasks-tab__stat">
          <span className="tasks-tab__stat-value">{tasks.length}</span>
          <span className="tasks-tab__stat-label">Всего</span>
        </div>
        <div className="tasks-tab__stat tasks-tab__stat--completed">
          <span className="tasks-tab__stat-value">{completed.length}</span>
          <span className="tasks-tab__stat-label">Готово</span>
        </div>
        <div className="tasks-tab__stat tasks-tab__stat--pending">
          <span className="tasks-tab__stat-value">{pending.length}</span>
          <span className="tasks-tab__stat-label">Ожидает</span>
        </div>
        <div className="tasks-tab__stat tasks-tab__stat--failed">
          <span className="tasks-tab__stat-value">{failed.length}</span>
          <span className="tasks-tab__stat-label">Ошибка</span>
        </div>
      </div>

      <div className="tasks-tab__list">
        {tasks.map(task => (
          <TaskCard
            key={task.id}
            task={task}
            onRebuild={handleRebuild}
            onValidate={handleValidate}
            rebuilding={rebuildingId === task.id}
            validating={validatingId === task.id}
          />
        ))}
      </div>
    </div>
  )
}