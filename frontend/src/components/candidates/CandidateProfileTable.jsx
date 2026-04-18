import React from 'react'
import { formatPercent } from '../../utils/formatters'

export default function CandidateProfileTable({ profile }) {
  if (!profile) return null

  return (
    <div className="candidates-tab__profile">
      <div className="candidates-tab__profile-score">
        <span className="candidates-tab__profile-score-label">Итоговый score</span>
        <strong>{formatPercent(profile.total_score, { normalized: false })}</strong>
      </div>
      <div className="candidates-tab__profile-table">
        <div className="candidates-tab__profile-header">
          <span>Категория</span>
          <span>Компетенция</span>
          <span>Описание</span>
          <span>Уровень</span>
          <span>Confidence</span>
        </div>
        {profile.competency_scores.length === 0 ? (
          <div className="candidates-tab__profile-empty">Нет оцененных компетенций</div>
        ) : (
          profile.competency_scores.map((item) => (
            <div key={item.competency_id} className="candidates-tab__profile-row">
              <span>{item.category_name || item.category_id || '—'}</span>
              <span>{item.competency_name || item.competency_id}</span>
              <span className="candidates-tab__profile-description">
                {item.competency_description || '—'}
              </span>
              <span>{item.level}</span>
              <span>{formatPercent(item.confidence)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
