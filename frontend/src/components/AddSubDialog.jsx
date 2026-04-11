// frontend/src/components/AddSubDialog.jsx
import React, { useState } from 'react'
import { X, Plus } from 'lucide-react'
import './AddSubDialog.css'

const LEVEL_OPTIONS = [
  { value: 0, label: '⚪ No level' },
  { value: 1, label: '🟢 Beginner' },
  { value: 2, label: '🟡 Intermediate' },
  { value: 3, label: '🟠 Upper-Intermediate' },
  { value: 4, label: '🔴 Advanced' },
  { value: 5, label: '⭐ Expert' },
]

export default function AddSubDialog({ competencyName, onAdd, onClose }) {
  const [form, setForm] = useState({
    name: '',
    target_level: 2,
    description: '',
    weight: 1.0,
  })

  const handleAdd = () => {
    if (!form.name.trim()) return
    onAdd({
      name: form.name.trim(),
      target_level: form.target_level,
      description: form.description.trim(),
      weight: parseFloat(form.weight) || 1.0,
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
              value={form.target_level}
              onChange={e => setForm({ ...form, target_level: parseInt(e.target.value) })}
            >
              {LEVEL_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
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
            Вес (0.1 — 2.0)
            <input
              type="number"
              min="0.1"
              max="2.0"
              step="0.1"
              value={form.weight}
              onChange={e => setForm({ ...form, weight: e.target.value })}
            />
          </label>
        </div>

        <div className="add-dialog__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button
            className="btn-primary"
            onClick={handleAdd}
            disabled={!form.name.trim()}
          >
            <Plus size={16} /> Добавить
          </button>
        </div>
      </div>
    </div>
  )
}