import React from 'react'
import AsyncState from '../AsyncState'

export default function OntologyDetails({ selected, selectedDetails, entityType }) {
  if (!selected.type) {
    return (
      <section className="ontology__details">
        <AsyncState
          kind="empty"
          title="Выберите узел онтологии"
          hint="Слева выберите категорию, компетенцию или подкомпетенцию для просмотра деталей."
        />
      </section>
    )
  }

  if (!selectedDetails) {
    return (
      <section className="ontology__details">
        <AsyncState kind="loading" title="Загрузка деталей..." />
      </section>
    )
  }

  return (
    <section className="ontology__details">
      <div className="ontology__details-card">
        <h3>
          {selected.type === entityType.CATEGORY && 'Категория'}
          {selected.type === entityType.COMPETENCY && 'Компетенция'}
          {selected.type === entityType.SUB_COMPETENCY && 'Подкомпетенция'}
        </h3>

        <div className="ontology__details-grid">
          {Object.entries(selectedDetails).map(([key, value]) => (
            <div key={key} className="ontology__details-item">
              <span className="ontology__details-key">{key}</span>
              <pre className="ontology__details-value">
                {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
              </pre>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
