import React from 'react';

export default function ForbiddenState({ title = 'Недостаточно прав', hint }) {
  return (
    <div
      style={{
        border: '1px solid #f5c2c7',
        background: '#fff5f5',
        color: '#7f1d1d',
        borderRadius: 12,
        padding: 16,
        marginTop: 12,
      }}
    >
      <h3 style={{ margin: 0, fontSize: 18 }}>{title}</h3>
      <p style={{ margin: '8px 0 0', color: '#991b1b' }}>
        {hint || 'У вашей роли нет доступа к этому разделу.'}
      </p>
    </div>
  );
}
