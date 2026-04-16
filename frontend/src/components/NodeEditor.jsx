// frontend/src/components/NodeEditor.jsx
import React, { useState } from 'react'
import { X, Save } from 'lucide-react'
import {
  COMPETENCY_LEVEL_OPTIONS,
  normalizeTargetLevel,
  normalizeWeight,
} from '../domain/competencyGraph'
import './NodeEditor.css'

const buildInitialForm = (sub) => ({
  name: sub?.sub_competency_name || '',
  target_level: sub?.target_level ?? 2,
  description: sub?.sub_competency_description || '',
  weight: sub?.weight ?? 1.0,
})

export default function NodeEditor({ sub, onSave, onClose }) {
  const [form, setForm] = useState(() => buildInitialForm(sub))

  const handleSave = () => {
    if (!form.name.trim()) return
    onSave({
      ...sub,
      sub_competency_name: form.name.trim(),
      target_level: normalizeTargetLevel(form.target_level),
      sub_competency_description: form.description.trim(),
      weight: normalizeWeight(form.weight),
    })
  }

  return (
    <div className="editor-overlay" onClick={onClose}>
      <div className="editor" onClick={e => e.stopPropagation()}>
        <div className="editor__header">
          <h3>✏️ Редактирование подкомпетенции</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="editor__body">
          <label>
            Название
            <input
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              autoFocus
            />
          </label>

          <label>
            Уровень
            <select
              value={form.target_level}
              onChange={e => setForm({ ...form, target_level: parseInt(e.target.value) })}
            >
              {COMPETENCY_LEVEL_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>

          <label>
            Описание
            <textarea
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              rows={3}
            />
          </label>

          <label>
            Вес (0.0 — 1.0)
            <input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={form.weight}
              onChange={e => setForm({ ...form, weight: e.target.value })}
            />
          </label>
        </div>

        <div className="editor__footer">
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
