import React from 'react';
import { Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react';

export default function OntologyToolbar({
  selected,
  refreshing,
  onRefresh,
  onCreateCategory,
  onCreateForSelection,
  onEditSelected,
  onDeleteSelected,
  entityType,
}) {
  const addLabel = selected.type === entityType.CATEGORY
    ? 'Добавить компетенцию'
    : selected.type === entityType.COMPETENCY
      ? 'Добавить подкомпетенцию'
      : 'Добавить'

  const canAdd = selected.type === entityType.CATEGORY || selected.type === entityType.COMPETENCY

  return (
    <div className="ontology__toolbar">
      <div className="ontology__toolbar-left">
        <h2>🧩 Онтология</h2>
      </div>
      <div className="ontology__toolbar-actions">
        <button className="btn-secondary" onClick={onRefresh}>
          <RefreshCw size={16} className={refreshing ? 'spin' : ''} /> Обновить
        </button>
        <button className="btn-primary" onClick={onCreateCategory}>
          <Plus size={16} /> Категория
        </button>
        <button
          className="btn-secondary"
          onClick={onCreateForSelection}
          disabled={!canAdd}
        >
          <Plus size={16} /> {addLabel}
        </button>
        <button
          className="btn-secondary"
          onClick={onEditSelected}
          disabled={!selected.type}
        >
          <Pencil size={16} /> Изменить
        </button>
        <button
          className="btn-danger"
          onClick={onDeleteSelected}
          disabled={!selected.type}
        >
          <Trash2 size={16} /> Удалить
        </button>
      </div>
    </div>
  )
}