// frontend/src/components/NodeEditor.jsx
import React, { useState, useEffect } from 'react'
import { X, Save } from 'lucide-react'
import './NodeEditor.css'

export default function NodeEditor({ sub, onSave, onClose }) {
  const [form, setForm] = useState({
    name: '',
    level: 'intermediate',
    description: '',
    sub_skills: '',
  })

  useEffect(() => {
    if (sub) {
      setForm({
        name: sub.name || '',
        level: sub.level || 'intermediate',
        description: sub.description || '',
        sub_skills: (sub.sub_skills || []).join('; '),
      })
    }
  }, [sub])

  const handleSave = () => {
    onSave({
      ...sub,
      name: form.name,
      level: form.level,
      description: form.description,
      sub_skills: form.sub_skills.split(';').map(s => s.trim()).filter(Boolean),
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
            />
          </label>

          <label>
            Уровень
            <select
              value={form.level}
              onChange={e => setForm({ ...form, level: e.target.value })}
            >
              <option value="beginner">🟢 Beginner</option>
              <option value="intermediate">🟡 Intermediate</option>
              <option value="advanced">🔴 Advanced</option>
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
            Навыки (через ;)
            <textarea
              value={form.sub_skills}
              onChange={e => setForm({ ...form, sub_skills: e.target.value })}
              rows={2}
            />
          </label>
        </div>

        <div className="editor__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn-primary" onClick={handleSave}>
            <Save size={16} /> Сохранить
          </button>
        </div>
      </div>
    </div>
  )
}