import React from 'react'
import { Loader2 } from 'lucide-react'

export default function AsyncState({
  kind = 'empty',
  title,
  hint,
  actionLabel,
  onAction,
}) {
  if (kind === 'loading') {
    return (
      <div style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
        <Loader2 size={24} className="spin" />
        <p>{title || 'Загрузка...'}</p>
      </div>
    )
  }

  return (
    <div style={{ padding: 24, textAlign: 'center' }}>
      <p style={{ margin: 0 }}>{title}</p>
      {hint && <p style={{ marginTop: 8, opacity: 0.8 }}>{hint}</p>}
      {actionLabel && onAction && (
        <button className="btn-primary" style={{ marginTop: 10 }} onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  )
}
