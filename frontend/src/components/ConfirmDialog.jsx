// frontend/src/components/ConfirmDialog.jsx
import React from 'react'
import { AlertTriangle, X } from 'lucide-react'
import './ConfirmDialog.css'

export default function ConfirmDialog({ title, message, onConfirm, onCancel }) {
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm" onClick={e => e.stopPropagation()}>
        <div className="confirm__header">
          <h3>
            <AlertTriangle size={20} />
            {title}
          </h3>
          <button onClick={onCancel}><X size={20} /></button>
        </div>

        <div className="confirm__body">
          <p>{message}</p>
        </div>

        <div className="confirm__footer">
          <button className="btn-secondary" onClick={onCancel}>Отмена</button>
          <button className="btn-danger" onClick={onConfirm}>Удалить</button>
        </div>
      </div>
    </div>
  )
}