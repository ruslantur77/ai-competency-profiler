// frontend/src/components/SuggestionsPanel.jsx
import React, { useState, useEffect } from 'react'
import { Check, X, CheckCheck, Loader2, ChevronDown, ChevronRight } from 'lucide-react'
import { getSuggestions } from '../api/client'
import './SuggestionsPanel.css'

const STAGE_LABELS = {
  category: '📁 Категория',
  competency: '🎯 Компетенция',
  sub_competency: '🔹 Подкомпетенция',
}

const STAGE_ORDER = ['category', 'competency', 'sub_competency']

export default function SuggestionsPanel({ vacancyId, onDecisionsChange, notify }) {
  const [suggestions, setSuggestions] = useState([])
  const [decisions, setDecisions] = useState({}) // id -> 'approved' | 'rejected'
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data } = await getSuggestions(vacancyId)
        // Только pending
        const pending = data.filter(s => s.status === 'pending')
        setSuggestions(pending)
        // Инициализируем decisions пустым
        setDecisions({})
        onDecisionsChange([])
      } catch {
        notify('Ошибка загрузки предложений', 'error')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [vacancyId])

  const decide = (suggestionId, status) => {
    const newDecisions = { ...decisions, [suggestionId]: status }
    setDecisions(newDecisions)
    // Передаём наверх массив для PATCH /graph
    const decisionsArray = Object.entries(newDecisions).map(([id, st]) => ({
      suggestion_id: id,
      status: st,
    }))
    onDecisionsChange(decisionsArray)
  }

  const approveAll = () => {
    const newDecisions = {}
    suggestions.forEach(s => { newDecisions[s.id] = 'approved' })
    setDecisions(newDecisions)
    onDecisionsChange(suggestions.map(s => ({ suggestion_id: s.id, status: 'approved' })))
  }

  const rejectAll = () => {
    const newDecisions = {}
    suggestions.forEach(s => { newDecisions[s.id] = 'rejected' })
    setDecisions(newDecisions)
    onDecisionsChange(suggestions.map(s => ({ suggestion_id: s.id, status: 'rejected' })))
  }

  if (loading) {
    return (
      <div className="suggestions-panel">
        <div className="suggestions-panel__loading">
          <Loader2 size={16} className="spin" />
          Загрузка предложений...
        </div>
      </div>
    )
  }

  if (suggestions.length === 0) return null

  const grouped = STAGE_ORDER.reduce((acc, stage) => {
    const items = suggestions.filter(s => s.stage === stage)
    if (items.length > 0) acc[stage] = items
    return acc
  }, {})

  const decidedCount = Object.keys(decisions).length

  return (
    <div className="suggestions-panel">
      <div
        className="suggestions-panel__header"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="suggestions-panel__header-left">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span>✨ Предложения AI</span>
          <span className="suggestions-panel__count">{suggestions.length}</span>
          {decidedCount > 0 && (
            <span className="suggestions-panel__decided">
              {decidedCount} отмечено — нажмите Сохранить
            </span>
          )}
        </div>
        <div
          className="suggestions-panel__header-actions"
          onClick={e => e.stopPropagation()}
        >
          <button
            className="suggestions-panel__btn suggestions-panel__btn--approve"
            onClick={approveAll}
          >
            <CheckCheck size={14} /> Одобрить все
          </button>
          <button
            className="suggestions-panel__btn suggestions-panel__btn--reject"
            onClick={rejectAll}
          >
            <X size={14} /> Отклонить все
          </button>
        </div>
      </div>

      {expanded && (
        <div className="suggestions-panel__body">
          {Object.entries(grouped).map(([stage, items]) => (
            <div key={stage} className="suggestions-panel__group">
              <div className="suggestions-panel__group-label">
                {STAGE_LABELS[stage]}
              </div>
              {items.map(s => {
                const decision = decisions[s.id]
                return (
                  <div
                    key={s.id}
                    className={`suggestions-panel__item ${
                      decision === 'approved' ? 'suggestions-panel__item--approved' :
                      decision === 'rejected' ? 'suggestions-panel__item--rejected' : ''
                    }`}
                  >
                    <div className="suggestions-panel__item-info">
                      <span className="suggestions-panel__item-name">{s.name}</span>
                      {s.description && (
                        <span className="suggestions-panel__item-desc">{s.description}</span>
                      )}
                      {s.reason && (
                        <span className="suggestions-panel__item-reason">💡 {s.reason}</span>
                      )}
                    </div>
                    <div className="suggestions-panel__item-actions">
                      <button
                        className={`suggestions-panel__btn ${
                          decision === 'approved'
                            ? 'suggestions-panel__btn--approve-active'
                            : 'suggestions-panel__btn--approve'
                        }`}
                        onClick={() => decide(s.id, decision === 'approved' ? null : 'approved')}
                        title="Одобрить"
                      >
                        <Check size={14} />
                      </button>
                      <button
                        className={`suggestions-panel__btn ${
                          decision === 'rejected'
                            ? 'suggestions-panel__btn--reject-active'
                            : 'suggestions-panel__btn--reject'
                        }`}
                        onClick={() => decide(s.id, decision === 'rejected' ? null : 'rejected')}
                        title="Отклонить"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}