// frontend/src/components/vacancy-list/VacancyModeSwitch.jsx
import React from 'react';

const MODES = [
  { id: 'all',     label: 'Все вакансии' },
  { id: 'pending', label: 'Обрабатывается' },
  { id: 'draft',   label: 'Ожидают проверки' },
  { id: 'ready',   label: 'Финализированы' },
  { id: 'failed',  label: 'Ошибка обработки' },
]

export default function VacancyModeSwitch({ vacancyMode, canSeeReviewQueue, onModeChange }) {
  const visibleModes = canSeeReviewQueue
    ? [...MODES, { id: 'review', label: 'Очередь проверки' }]
    : MODES

  return (
    <div className="vacancy-list__mode">
      {visibleModes.map(mode => (
        <button
          key={mode.id}
          className={`vacancy-list__mode-btn ${vacancyMode === mode.id ? 'is-active' : ''}`}
          onClick={() => onModeChange(mode.id)}
        >
          {mode.label}
        </button>
      ))}
    </div>
  )
}