// frontend/src/components/EditCompetencyDialog.jsx
import React, { useState } from 'react'
import { X, Save } from 'lucide-react'
import './EditCompetencyDialog.css'

const buildInitialForm = (competency) => ({
  name: competency?.competency_name || '',
  description: competency?.competency_description || '',
  is_required: competency?.is_required ?? true,
})

export default function EditCompetencyDialog({ competency, onSave, onClose }) {
  const [form, setForm] = useState(() => buildInitialForm(competency))

  const handleSave = () => {
    if (!form.name.trim()) return
    onSave({
      ...competency,
      competency_name: form.name.trim(),
      competency_description: form.description.trim(),
      is_required: form.is_required,
    })
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
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              rows={3}
              autoFocus
            />
          </label>

          <label>
            Описание
            <textarea
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              rows={2}
            />
          </label>

          <label className="edit-comp__checkbox-label">
            <input
              type="checkbox"
              checked={form.is_required}
              onChange={e => setForm({ ...form, is_required: e.target.checked })}
            />
            Обязательная компетенция
          </label>
        </div>

        <div className="edit-comp__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={!form.name.trim()}
          >
            <Save size={16} /> Сохранить
          </button>
        </div>
      </div>
    </div>
  )
}
