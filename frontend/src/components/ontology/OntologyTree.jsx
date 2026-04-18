import React from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import AsyncState from '../AsyncState'

export default function OntologyTree({
  categories,
  selected,
  entityType,
  expandedCategories,
  expandedCompetencies,
  onSelect,
  onToggleCategory,
  onToggleCompetency,
}) {
  if (categories.length === 0) {
    return (
      <aside className="ontology__tree">
        <AsyncState kind="empty" title="Онтология пока пуста" hint="Создайте первую категорию." />
      </aside>
    )
  }

  return (
    <aside className="ontology__tree">
      {categories.map((category) => {
        const categoryExpanded = expandedCategories.has(category.id)

        return (
          <div key={category.id} className="ontology__category">
            <button
              className={`ontology__node ontology__node--category ${
                selected.type === entityType.CATEGORY && selected.id === category.id ? 'is-selected' : ''
              }`}
              onClick={() => onSelect(entityType.CATEGORY, category.id)}
            >
              <span
                className="ontology__node-expand"
                onClick={(event) => {
                  event.stopPropagation()
                  onToggleCategory(category.id)
                }}
              >
                {categoryExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
              <span>{category.emoji || '📋'} {category.name}</span>
            </button>

            {categoryExpanded && (
              <div className="ontology__children">
                {(category.competencies || []).map((competency) => {
                  const competencyExpanded = expandedCompetencies.has(competency.id)

                  return (
                    <div key={competency.id} className="ontology__competency">
                      <button
                        className={`ontology__node ontology__node--competency ${
                          selected.type === entityType.COMPETENCY && selected.id === competency.id
                            ? 'is-selected'
                            : ''
                        }`}
                        onClick={() => onSelect(entityType.COMPETENCY, competency.id)}
                      >
                        <span
                          className="ontology__node-expand"
                          onClick={(event) => {
                            event.stopPropagation()
                            onToggleCompetency(competency.id)
                          }}
                        >
                          {competencyExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </span>
                        <span>{competency.name}</span>
                      </button>

                      {competencyExpanded && (
                        <div className="ontology__children ontology__children--sub">
                          {(competency.sub_competencies || []).map((sub) => (
                            <button
                              key={sub.id}
                              className={`ontology__node ontology__node--sub ${
                                selected.type === entityType.SUB_COMPETENCY && selected.id === sub.id
                                  ? 'is-selected'
                                  : ''
                              }`}
                              onClick={() => onSelect(entityType.SUB_COMPETENCY, sub.id)}
                            >
                              <span className="ontology__node-dot">•</span>
                              <span>{sub.name}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </aside>
  )
}
