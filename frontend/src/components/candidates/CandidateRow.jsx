import React from 'react'
import { getCandidateStatusMeta } from '../../domain/statusMeta'
import { formatDateTime } from '../../utils/formatters'

export default function CandidateRow({ candidate, selected, onSelect }) {
  const statusMeta = getCandidateStatusMeta(candidate.status)
  return (
    <button
      className={`candidates-tab__row ${selected ? 'is-selected' : ''}`}
      onClick={() => onSelect(candidate.id)}
    >
      <div className="candidates-tab__row-main">
        <span className="candidates-tab__candidate-id">{candidate.external_id}</span>
        <span className={`candidates-tab__status candidates-tab__status--${statusMeta.badge}`}>
          {statusMeta.label}
        </span>
      </div>
      <div className="candidates-tab__row-meta">
        <span>{formatDateTime(candidate.last_assessment_at)}</span>
      </div>
    </button>
  )
}
