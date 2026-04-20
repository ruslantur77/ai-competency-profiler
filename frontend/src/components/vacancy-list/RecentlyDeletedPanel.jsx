import React from 'react';
import { RotateCcw, ShieldAlert } from 'lucide-react';

export default function RecentlyDeletedPanel({ items, onRestore, onHardDelete }) {
  if (items.length === 0) return null;

  return (
    <div className="vacancy-list__deleted-panel">
      <h4>
        <RotateCcw size={16} /> Недавно удаленные
      </h4>
      <div className="vacancy-list__deleted-list">
        {items.map((item) => (
          <div key={item.id} className="vacancy-list__deleted-item">
            <span>{item.name}</span>
            <div className="vacancy-list__deleted-actions">
              <button className="btn-secondary" onClick={() => onRestore(item)}>
                Восстановить
              </button>
              <button
                className="btn-danger"
                onClick={() => onHardDelete(item)}
                title="Полное удаление без восстановления"
              >
                <ShieldAlert size={14} /> Удалить навсегда
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
