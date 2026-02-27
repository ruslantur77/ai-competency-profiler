// frontend/src/components/AddCompetencyDialog.jsx
import React, { useState } from 'react'
import { X, Plus } from 'lucide-react'
import './AddCompetencyDialog.css'

export default function AddCompetencyDialog({ categoryName, onAdd, onClose }) {
  const [skill, setSkill] = useState('')

  const handleAdd = () => {
    if (!skill.trim()) return
    onAdd(skill.trim())
  }

  return (
    <div className="add-comp-overlay" onClick={onClose}>
      <div className="add-comp" onClick={e => e.stopPropagation()}>
        <div className="add-comp__header">
          <h3>➕ Добавить компетенцию</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="add-comp__context">
          Категория: <strong>{categoryName}</strong>
        </div>

        <div className="add-comp__body">
          <label>
            Название компетенции
            <textarea
              value={skill}
              onChange={e => setSkill(e.target.value)}
              placeholder="Например: SQL — аналитические функции, подзапросы"
              rows={3}
              autoFocus
            />
          </label>
        </div>

        <div className="add-comp__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn-primary" onClick={handleAdd} disabled={!skill.trim()}>
            <Plus size={16} /> Добавить
          </button>
        </div>
      </div>
    </div>
  )
}