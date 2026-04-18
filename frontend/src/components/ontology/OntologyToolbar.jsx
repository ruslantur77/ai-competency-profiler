import React from 'react'
import { Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react'
import SelectionBadge from './SelectionBadge'

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
  return (
    <div className="ontology__toolbar">
      <div className="ontology__toolbar-left">
        <h2>🧩 Онтология</h2>
        <SelectionBadge selected={selected} />
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
          disabled={selected.type !== entityType.CATEGORY && selected.type !== entityType.COMPETENCY}
        >
          <Plus size={16} /> Добавить в выбранное
        </button>
        <button className="btn-secondary" onClick={onEditSelected} disabled={!selected.type}>
          <Pencil size={16} /> Изменить
        </button>
        <button className="btn-danger" onClick={onDeleteSelected} disabled={!selected.type}>
          <Trash2 size={16} /> Удалить
        </button>
      </div>
    </div>
  )
}
