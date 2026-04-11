// frontend/src/components/SuggestionsPanel.jsx
import React, { useState, useEffect } from 'react'
import { Check, X, CheckCheck, Loader2, ChevronDown, ChevronRight } from 'lucide-react'
import { getSuggestions, decideSuggestion } from '../api/client'
import './SuggestionsPanel.css'

const STAGE_LABELS = {
  category: '📁 Категория',
  competency: '🎯 Компетенция',
  sub_competency: '🔹 Подкомпетенция',
}

const STAGE_ORDER = ['category', 'competency', 'sub_competency']

export default function SuggestionsPanel({ vacancyId, onApplied, notify }) {
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [deciding, setDeciding] = useState({}) // id -> true
  const [expanded, setExpanded] = useState(true)

  const fetchSuggestions = async () => {
    try {
      const { data } = await getSuggestions(vacancyId)
      // Показываем только pending
      setSuggestions(data.filter(s => s.status === 'pending'))
    } catch {
      notify('Ошибка загрузки предложений', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSuggestions()
  }, [vacancyId])

  const decide = async (suggestionId, status) => {
    setDeciding(prev => ({ ...prev, [suggestionId]: true }))
    try {
      await decideSuggestion(vacancyId, suggestionId, status)
      setSuggestions(prev => prev.filter(s => s.id !== suggestionId))
      if (status === 'approved') {
        // После одобрения обновляем граф
        onApplied()
      }
    } catch {
      notify('Ошибка при обработке предложения', 'error')
    } finally {
      setDeciding(prev => ({ ...prev, [suggestionId]: false }))
    }
  }

  const approveAll = async () => {
    const pending = suggestions.filter(s => s.status === 'pending')
    for (const s of pending) {
      await decide(s.id, 'approved')
    }
    notify('✅ Все предложения одобрены')
  }

  const rejectAll = async () => {
    const pending = suggestions.filter(s => s.status === 'pending')
    for (const s of pending) {
      await decide(s.id, 'rejected')
    }
    notify('❌ Все предложения отклонены')
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

  // Группируем по stage
  const grouped = STAGE_ORDER.reduce((acc, stage) => {
    const items = suggestions.filter(s => s.stage === stage)
    if (items.length > 0) acc[stage] = items
    return acc
  }, {})

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
        </div>
        <div
          className="suggestions-panel__header-actions"
          onClick={e => e.stopPropagation()}
        >
          <button
            className="suggestions-panel__btn suggestions-panel__btn--approve"
            onClick={approveAll}
            title="Одобрить все"
          >
            <CheckCheck size={14} /> Одобрить все
          </button>
          <button
            className="suggestions-panel__btn suggestions-panel__btn--reject"
            onClick={rejectAll}
            title="Отклонить все"
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
              {items.map(s => (
                <div key={s.id} className="suggestions-panel__item">
                  <div className="suggestions-panel__item-info">
                    <span className="suggestions-panel__item-name">{s.name}</span>
                    {s.description && (
                      <span className="suggestions-panel__item-desc">
                        {s.description}
                      </span>
                    )}
                    {s.reason && (
                      <span className="suggestions-panel__item-reason">
                        💡 {s.reason}
                      </span>
                    )}
                  </div>
                  <div className="suggestions-panel__item-actions">
                    {deciding[s.id] ? (
                      <Loader2 size={16} className="spin" />
                    ) : (
                      <>
                        <button
                          className="suggestions-panel__btn suggestions-panel__btn--approve"
                          onClick={() => decide(s.id, 'approved')}
                          title="Одобрить"
                        >
                          <Check size={14} />
                        </button>
                        <button
                          className="suggestions-panel__btn suggestions-panel__btn--reject"
                          onClick={() => decide(s.id, 'rejected')}
                          title="Отклонить"
                        >
                          <X size={14} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}