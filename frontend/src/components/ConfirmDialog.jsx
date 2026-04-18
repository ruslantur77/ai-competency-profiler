// frontend/src/components/ConfirmDialog.jsx
import React, { useMemo, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import './ConfirmDialog.css';

export default function ConfirmDialog({
  title,
  message,
  onConfirm,
  onCancel,
  confirmLabel = 'Удалить',
  requireText = null,
  requireHint = '',
}) {
  const [typed, setTyped] = useState('');
  const isGuardSatisfied = useMemo(() => {
    if (!requireText) return true;
    return typed.trim() === requireText;
  }, [typed, requireText]);

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm" onClick={(e) => e.stopPropagation()}>
        <div className="confirm__header">
          <h3>
            <AlertTriangle size={20} />
            {title}
          </h3>
          <button onClick={onCancel}>
            <X size={20} />
          </button>
        </div>

        <div className="confirm__body">
          <p>{message}</p>
          {requireText && (
            <div className="confirm__guard">
              <p className="confirm__guard-hint">
                {requireHint || `Введите "${requireText}" для подтверждения.`}
              </p>
              <input
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                placeholder={requireText}
                autoFocus
              />
            </div>
          )}
        </div>

        <div className="confirm__footer">
          <button className="btn-secondary" onClick={onCancel}>
            Отмена
          </button>
          <button className="btn-danger" onClick={onConfirm} disabled={!isGuardSatisfied}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
