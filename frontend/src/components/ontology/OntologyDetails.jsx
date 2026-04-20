import React from 'react';
import AsyncState from '../AsyncState';

const LEVEL_LABELS = {
  0: 'No level',
  1: 'Beginner',
  2: 'Intermediate',
  3: 'Upper-Intermediate',
  4: 'Advanced',
  5: 'Expert',
}

function DetailRow({ label, value }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div className="ontology__details-item">
      <span className="ontology__details-key">{label}</span>
      <span className="ontology__details-value">{value}</span>
    </div>
  )
}

function CategoryDetails({ details }) {
  return (
    <>
      <DetailRow label="Название" value={details.name} />
      <DetailRow label="Эмодзи" value={details.emoji} />
      <DetailRow label="Описание" value={details.description} />
      <div className="ontology__details-item">
        <span className="ontology__details-key">Компетенции</span>
        <div className="ontology__details-list">
          {(details.competencies || []).length === 0 ? (
            <span className="ontology__details-empty">Нет компетенций</span>
          ) : (
            (details.competencies || []).map(comp => (
              <span key={comp.id} className="ontology__details-tag">
                {comp.name}
              </span>
            ))
          )}
        </div>
      </div>
    </>
  )
}

function CompetencyDetails({ details }) {
  return (
    <>
      <DetailRow label="Название" value={details.name} />
      <DetailRow label="Описание" value={details.description} />
      <div className="ontology__details-item">
        <span className="ontology__details-key">Подкомпетенции</span>
        <div className="ontology__details-list">
          {(details.sub_competencies || []).length === 0 ? (
            <span className="ontology__details-empty">Нет подкомпетенций</span>
          ) : (
            (details.sub_competencies || []).map(sub => (
              <span key={sub.id} className="ontology__details-tag">
                {sub.name}
              </span>
            ))
          )}
        </div>
      </div>
    </>
  )
}

function SubCompetencyDetails({ details }) {
  return (
    <>
      <DetailRow label="Название" value={details.name} />
      <DetailRow label="Описание" value={details.description} />
      <DetailRow
        label="Целевой уровень"
        value={LEVEL_LABELS[details.target_level] ?? details.target_level}
      />
      <DetailRow label="Вес" value={details.weight} />
    </>
  )
}

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

  const titleMap = {
    [entityType.CATEGORY]: 'Категория',
    [entityType.COMPETENCY]: 'Компетенция',
    [entityType.SUB_COMPETENCY]: 'Подкомпетенция',
  }

  return (
    <section className="ontology__details">
      <div className="ontology__details-card">
        <h3>{titleMap[selected.type]}</h3>

        <div className="ontology__details-grid">
          {selected.type === entityType.CATEGORY && (
            <CategoryDetails details={selectedDetails} />
          )}
          {selected.type === entityType.COMPETENCY && (
            <CompetencyDetails details={selectedDetails} />
          )}
          {selected.type === entityType.SUB_COMPETENCY && (
            <SubCompetencyDetails details={selectedDetails} />
          )}
        </div>
      </div>
    </section>
  )
}