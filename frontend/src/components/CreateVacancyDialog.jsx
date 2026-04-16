// frontend/src/components/CreateVacancyDialog.jsx
import React, { useState } from 'react'
import { X, Plus } from 'lucide-react'
import './CreateVacancyDialog.css'

export default function CreateVacancyDialog({ onClose, onCreate }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const handleCreate = () => {
    if (!name.trim()) return
    onCreate({ name: name.trim(), description: description.trim() })
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') onClose()
  }

  return (
    <div className="create-vacancy-overlay" onClick={onClose} onKeyDown={handleKeyDown}>
      <div className="create-vacancy" onClick={e => e.stopPropagation()}>
        <div className="create-vacancy__header">
          <h3>➕ Создать вакансию</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="create-vacancy__body">
          <label>
            Название вакансии *
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Например: Data-аналитик"
              autoFocus
            />
          </label>

          <label>
            Описание вакансии
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Требования, обязанности, условия..."
              rows={10}
            />
          </label>
        </div>

        <div className="create-vacancy__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button
            className="btn-primary"
            onClick={handleCreate}
            disabled={!name.trim()}
          >
            <Plus size={16} /> Создать
          </button>
        </div>
      </div>
    </div>
  )
}