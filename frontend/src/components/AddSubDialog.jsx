// frontend/src/components/AddSubDialog.jsx
import React, { useState } from 'react'
import { X, Plus } from 'lucide-react'
import './AddSubDialog.css'

export default function AddSubDialog({ competencyName, onAdd, onClose }) {
  const [form, setForm] = useState({
    name: '',
    level: 'intermediate',
    description: '',
    sub_skills: '',
  })

  const handleAdd = () => {
    if (!form.name.trim()) return
    onAdd({
      name: form.name,
      level: form.level,
      description: form.description,
      sub_skills: form.sub_skills.split(';').map(s => s.trim()).filter(Boolean),
    })
  }

  return (
    <div className="add-dialog-overlay" onClick={onClose}>
      <div className="add-dialog" onClick={e => e.stopPropagation()}>
        <div className="add-dialog__header">
          <h3>➕ Добавить подкомпетенцию</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="add-dialog__context">
          Компетенция: <strong>{competencyName}</strong>
        </div>

        <div className="add-dialog__body">
          <label>
            Название *
            <input
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              placeholder="Например: Работа с индексами"
              autoFocus
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
              placeholder="Что конкретно нужно уметь..."
              rows={3}
            />
          </label>

          <label>
            Навыки (через ;)
            <textarea
              value={form.sub_skills}
              onChange={e => setForm({ ...form, sub_skills: e.target.value })}
              placeholder="Навык 1; Навык 2; Навык 3"
              rows={2}
            />
          </label>
        </div>

        <div className="add-dialog__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn-primary" onClick={handleAdd} disabled={!form.name.trim()}>
            <Plus size={16} /> Добавить
          </button>
        </div>
      </div>
    </div>
  )
}