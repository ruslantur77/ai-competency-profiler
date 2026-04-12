// frontend/src/components/SuggestionsPanel.jsx
import React, { useState, useEffect } from 'react'
import { Check, X, CheckCheck, XCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react'
import { getSuggestions } from '../api/client'
import './SuggestionsPanel.css'

// ===== ПОЛНАЯ ОНТОЛОГИЯ ИЗ БД =====
const ONTOLOGY = {
  categories: {
    '11111111-1111-1111-1111-111111111111': { name: 'Backend Development', emoji: '🧩' },
    '22222222-2222-2222-2222-222222222222': { name: 'Data Storage', emoji: '🗄️' },
    '33333333-3333-3333-3333-333333333333': { name: 'Infrastructure', emoji: '🚀' },
  },
  competencies: {
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1': { name: 'API Design',              categoryId: '11111111-1111-1111-1111-111111111111' },
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2': { name: 'Python Backend',          categoryId: '11111111-1111-1111-1111-111111111111' },
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3': { name: 'SQL Modeling',            categoryId: '22222222-2222-2222-2222-222222222222' },
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4': { name: 'Containers and Delivery', categoryId: '33333333-3333-3333-3333-333333333333' },
  },
  subCompetencies: {
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1': { name: 'REST principles',         competencyId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1' },
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2': { name: 'API security',            competencyId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1' },
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3': { name: 'Async programming',       competencyId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2' },
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb4': { name: 'Typing and architecture', competencyId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2' },
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb5': { name: 'Indexes',                 competencyId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3' },
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb6': { name: 'Join optimization',       competencyId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3' },
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb7': { name: 'Docker',                  competencyId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4' },
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb8': { name: 'CI/CD',                   competencyId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4' },
  },
}

// Обогащаем suggestion данными из онтологии
const enrichSuggestion = (s) => {
  if (s.stage === 'competency' && s.parent_category_id) {
    const cat = ONTOLOGY.categories[s.parent_category_id]
    if (cat) {
      return {
        ...s,
        parent_category_name: cat.name,
        parent_category_emoji: cat.emoji,
      }
    }
  }
  if (s.stage === 'sub_competency' && s.parent_competency_id) {
    const comp = ONTOLOGY.competencies[s.parent_competency_id]
    if (comp) {
      const cat = ONTOLOGY.categories[comp.categoryId]
      return {
        ...s,
        parent_competency_name: comp.name,
        parent_category_id: comp.categoryId,
        parent_category_name: cat?.name || '',
        parent_category_emoji: cat?.emoji || '',
      }
    }
  }
  return s
}

const STAGE_LABELS = {
  category: '📁 Категория',
  competency: '🎯 Компетенция',
  sub_competency: '🔹 Подкомпетенция',
}

const STAGE_ORDER = ['category', 'competency', 'sub_competency']

export default function SuggestionsPanel({
  vacancyId,
  onApprove,
  onReject,
  onDecisionsChange,
  notify,
}) {
  const [suggestions, setSuggestions] = useState([])
  const [decisions, setDecisions] = useState({})
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await getSuggestions(vacancyId)
        const pending = data
          .filter(s => s.status === 'pending')
          .map(enrichSuggestion)
        setSuggestions(pending)
        setDecisions({})
        onDecisionsChange([])
      } catch {
        notify('Ошибка загрузки предложений', 'error')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [vacancyId])

  const updateDecisions = (newDecisions) => {
    setDecisions(newDecisions)
    onDecisionsChange(
      Object.entries(newDecisions).map(([id, status]) => ({
        suggestion_id: id,
        status,
      }))
    )
  }

  const approve = (suggestion) => {
    const current = decisions[suggestion.id]
    if (current === 'approved') {
      const newDecisions = { ...decisions }
      delete newDecisions[suggestion.id]
      updateDecisions(newDecisions)
      onReject(suggestion)
    } else {
      updateDecisions({ ...decisions, [suggestion.id]: 'approved' })
      onApprove(suggestion)
    }
  }

  const reject = (suggestion) => {
    const current = decisions[suggestion.id]
    if (current === 'rejected') {
      const newDecisions = { ...decisions }
      delete newDecisions[suggestion.id]
      updateDecisions(newDecisions)
    } else {
      if (current === 'approved') onReject(suggestion)
      updateDecisions({ ...decisions, [suggestion.id]: 'rejected' })
    }
  }

  const approveAll = () => {
    const newDecisions = {}
    suggestions.forEach(s => {
      newDecisions[s.id] = 'approved'
      if (decisions[s.id] !== 'approved') onApprove(s)
    })
    updateDecisions(newDecisions)
  }

  const rejectAll = () => {
    const newDecisions = {}
    suggestions.forEach(s => {
      newDecisions[s.id] = 'rejected'
      if (decisions[s.id] === 'approved') onReject(s)
    })
    updateDecisions(newDecisions)
  }

  if (loading) {
    return (
      <div className="suggestions-panel">
        <div className="suggestions-panel__loading">
          <Loader2 size={16} className="spin" /> Загрузка предложений...
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
            <CheckCheck size={14} /> Добавить все в граф
          </button>
          <button
            className="suggestions-panel__btn suggestions-panel__btn--reject"
            onClick={rejectAll}
          >
            <XCircle size={14} /> Отклонить все
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
                      {/* Показываем хлебные крошки: куда попадёт узел */}
                      {s.stage === 'competency' && s.parent_category_name && (
                        <span className="suggestions-panel__item-meta">
                          {s.parent_category_emoji} {s.parent_category_name}
                        </span>
                      )}
                      {s.stage === 'sub_competency' && s.parent_competency_name && (
                        <span className="suggestions-panel__item-meta">
                          {s.parent_category_emoji} {s.parent_category_name}
                          {' → '}
                          🎯 {s.parent_competency_name}
                        </span>
                      )}
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
                        onClick={() => approve(s)}
                        title={decision === 'approved' ? 'Убрать из графа' : 'Добавить в граф'}
                      >
                        <Check size={14} />
                      </button>
                      <button
                        className={`suggestions-panel__btn ${
                          decision === 'rejected'
                            ? 'suggestions-panel__btn--reject-active'
                            : 'suggestions-panel__btn--reject'
                        }`}
                        onClick={() => reject(s)}
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