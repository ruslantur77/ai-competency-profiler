import React from 'react'
import { ExternalLink, Trash2 } from 'lucide-react'

export default function VacancyCardsGrid({
  vacancies,
  statusConfig,
  updatingStatusId,
  onOpen,
  onDelete,
  onStatusChange,
}) {
  const isClickable = (status) => status === 'ready' || status === 'draft'

  return (
    <div className="vacancy-list__grid">
      {vacancies.map((vacancy) => {
        const config = statusConfig[vacancy.status] || statusConfig.pending
        const clickable = isClickable(vacancy.status)
        return (
          <div
            key={vacancy.id}
            className={`vacancy-card vacancy-card--${vacancy.status} ${clickable ? 'vacancy-card--clickable' : ''}`}
            onClick={() => onOpen(vacancy)}
          >
            <div className="vacancy-card__header">
              <h3>{vacancy.name}</h3>
              <div
                className="vacancy-card__actions"
                onClick={(event) => event.stopPropagation()}
              >
                <button
                  title="Удалить вакансию"
                  onClick={() => onDelete(vacancy)}
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
                {new Date(vacancy.created_at).toLocaleDateString('ru-RU')}
              </span>
              <div
                className="vacancy-card__controls"
                onClick={(event) => event.stopPropagation()}
              >
                <select
                  value={vacancy.status}
                  onChange={(event) => onStatusChange(vacancy.id, event.target.value)}
                  disabled={updatingStatusId === vacancy.id}
                >
                  {Object.keys(statusConfig).map((statusKey) => (
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
  )
}
