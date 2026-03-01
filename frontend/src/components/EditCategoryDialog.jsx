// frontend/src/components/EditCategoryDialog.jsx
import React, { useState, useEffect } from 'react'
import { X, Save } from 'lucide-react'
import './EditCategoryDialog.css'

const EMOJI_OPTIONS = ['🔧', '📊', '🏢', '🤝', '💡', '📱', '🎨', '📈', '🔬', '🛠️', '📋', '🎯', '🧠', '💻', '📚', '⚙️']

export default function EditCategoryDialog({ category, onSave, onClose, title }) {
  const [form, setForm] = useState({
    name: '',
    emoji: '📌',
    description: '',
  })

  useEffect(() => {
    if (category) {
      setForm({
        name: category.name || '',
        emoji: category.emoji || '📌',
        description: category.description || '',
      })
    }
  }, [category])

  const handleSave = () => {
    if (!form.name.trim()) return
    onSave({ ...category, ...form })
  }

  return (
    <div className="edit-cat-overlay" onClick={onClose}>
      <div className="edit-cat" onClick={e => e.stopPropagation()}>
        <div className="edit-cat__header">
          <h3>{title || '✏️ Редактирование категории'}</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="edit-cat__body">
          <label>
            Эмодзи
            <div className="edit-cat__emoji-grid">
              {EMOJI_OPTIONS.map(em => (
                <button
                  key={em}
                  type="button"
                  className={`edit-cat__emoji-btn ${form.emoji === em ? 'active' : ''}`}
                  onClick={() => setForm({ ...form, emoji: em })}
                >
                  {em}
                </button>
              ))}
            </div>
          </label>

          <label>
            Название
            <input
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
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
        </div>

        <div className="edit-cat__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn-primary" onClick={handleSave} disabled={!form.name.trim()}>
            <Save size={16} /> Сохранить
          </button>
        </div>
      </div>
    </div>
  )
}