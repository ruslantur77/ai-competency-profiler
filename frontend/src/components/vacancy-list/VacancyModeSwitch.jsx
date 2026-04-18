import React from 'react'

export default function VacancyModeSwitch({
  vacancyMode,
  canSeeReviewQueue,
  onModeChange,
}) {
  return (
    <div className="vacancy-list__mode">
      <button
        className={`vacancy-list__mode-btn ${vacancyMode === 'all' ? 'is-active' : ''}`}
        onClick={() => onModeChange('all')}
      >
        Все вакансии
      </button>
      {canSeeReviewQueue && (
        <button
          className={`vacancy-list__mode-btn ${vacancyMode === 'review' ? 'is-active' : ''}`}
          onClick={() => onModeChange('review')}
        >
          Review queue
        </button>
      )}
    </div>
  )
}
