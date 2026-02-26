// frontend/src/components/AiFixDialog.jsx
import React, { useState } from 'react'
import { X, Sparkles } from 'lucide-react'
import './AiFixDialog.css'

export default function AiFixDialog({ subName, onSubmit, onClose }) {
  const [instruction, setInstruction] = useState('')

  const handleSubmit = () => {
    if (!instruction.trim()) return
    onSubmit(instruction.trim())
  }

  return (
    <div className="aifix-overlay" onClick={onClose}>
      <div className="aifix" onClick={e => e.stopPropagation()}>
        <div className="aifix__header">
          <h3>
            <Sparkles size={20} />
            AI исправление
          </h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="aifix__context">
          Подкомпетенция: <strong>{subName}</strong>
        </div>

        <div className="aifix__body">
          <label>
            Инструкция для AI
            <textarea
              value={instruction}
              onChange={e => setInstruction(e.target.value)}
              placeholder="Опишите, что нужно изменить...&#10;&#10;Например:&#10;• Добавь больше практических навыков&#10;• Измени уровень на advanced&#10;• Раскрой подробнее работу с индексами"
              rows={5}
              autoFocus
            />
          </label>
        </div>

        <div className="aifix__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn-ai" onClick={handleSubmit} disabled={!instruction.trim()}>
            <Sparkles size={16} /> Отправить AI
          </button>
        </div>
      </div>
    </div>
  )
}