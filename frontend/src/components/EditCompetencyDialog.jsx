// frontend/src/components/EditCompetencyDialog.jsx
import React, { useState, useEffect } from 'react'
import { X, Save } from 'lucide-react'
import './EditCompetencyDialog.css'

export default function EditCompetencyDialog({ competency, onSave, onClose }) {
  const [skill, setSkill] = useState('')

  useEffect(() => {
    if (competency) {
      setSkill(competency.skill || '')
    }
  }, [competency])

  const handleSave = () => {
    if (!skill.trim()) return
    onSave({ ...competency, skill: skill.trim() })
  }

  return (
    <div className="edit-comp-overlay" onClick={onClose}>
      <div className="edit-comp" onClick={e => e.stopPropagation()}>
        <div className="edit-comp__header">
          <h3>✏️ Редактирование компетенции</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="edit-comp__body">
          <label>
            Название компетенции
            <textarea
              value={skill}
              onChange={e => setSkill(e.target.value)}
              rows={3}
              autoFocus
            />
          </label>
        </div>

        <div className="edit-comp__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn-primary" onClick={handleSave} disabled={!skill.trim()}>
            <Save size={16} /> Сохранить
          </button>
        </div>
      </div>
    </div>
  )
}