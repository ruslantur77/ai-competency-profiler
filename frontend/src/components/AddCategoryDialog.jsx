import React, { useMemo, useState } from 'react'
import { Plus, X } from 'lucide-react'
import './AddCategoryDialog.css'

export default function AddCategoryDialog({ onAdd, onClose, existingOptions = [] }) {
  const hasExisting = existingOptions.length > 0
  const [mode, setMode] = useState(hasExisting ? 'existing' : 'new')
  const [selectedId, setSelectedId] = useState(existingOptions[0]?.id || '')
  const [form, setForm] = useState({
    name: '',
    emoji: '📋',
    description: '',
  })

  const selectedExisting = useMemo(
    () => existingOptions.find((option) => option.id === selectedId) || null,
    [existingOptions, selectedId]
  )

  const handleSubmit = () => {
    if (mode === 'existing') {
      if (!selectedExisting) return
      onAdd({
        mode: 'existing',
        id: selectedExisting.id,
        name: selectedExisting.name,
        emoji: selectedExisting.emoji || '',
        description: selectedExisting.description || '',
      })
      return
    }

    if (!form.name.trim()) return
    onAdd({
      mode: 'new',
      name: form.name.trim(),
      emoji: form.emoji || '',
      description: form.description.trim(),
    })
  }

  return (
    <div className="add-category-overlay" onClick={onClose}>
      <div className="add-category" onClick={(event) => event.stopPropagation()}>
        <div className="add-category__header">
          <h3>➕ Добавить категорию</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="add-category__mode">
          <button
            className={`add-category__mode-btn ${mode === 'existing' ? 'active' : ''}`}
            onClick={() => setMode('existing')}
            disabled={!hasExisting}
            type="button"
          >
            Из онтологии
          </button>
          <button
            className={`add-category__mode-btn ${mode === 'new' ? 'active' : ''}`}
            onClick={() => setMode('new')}
            type="button"
          >
            Новая
          </button>
        </div>

        <div className="add-category__body">
          {mode === 'existing' ? (
            <>
              <label>
                Категория из онтологии
                <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
                  {existingOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {(option.emoji || '📋')} {option.name}
                    </option>
                  ))}
                </select>
              </label>
              {!hasExisting && (
                <p className="add-category__hint">В онтологии нет доступных категорий.</p>
              )}
            </>
          ) : (
            <>
              <label>
                Название категории *
                <input
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  autoFocus
                />
              </label>
              <label>
                Emoji
                <input
                  value={form.emoji}
                  onChange={(event) => setForm({ ...form, emoji: event.target.value })}
                />
              </label>
              <label>
                Описание
                <textarea
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                  rows={3}
                />
              </label>
            </>
          )}
        </div>

        <div className="add-category__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={mode === 'existing' ? !selectedExisting : !form.name.trim()}
          >
            <Plus size={16} /> Добавить
          </button>
        </div>
      </div>
    </div>
  )
}
