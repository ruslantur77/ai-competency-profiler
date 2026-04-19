// frontend/src/components/AddCategoryDialog.jsx
import React, { useMemo, useState } from 'react';
import { Plus, X } from 'lucide-react';
import './AddCategoryDialog.css';

const EMOJI_OPTIONS = [
  '🔧', '📊', '🏢', '🤝', '💡', '📱', '🎨', '📈',
  '🔬', '🛠️', '📋', '🎯', '🧠', '💻', '📚', '⚙️',
];

export default function AddCategoryDialog({ onAdd, onClose, existingOptions = [] }) {
  const hasExisting = existingOptions.length > 0;
  const [mode, setMode] = useState(hasExisting ? 'existing' : 'new');
  const [selectedId, setSelectedId] = useState(existingOptions[0]?.id || '');
  const [form, setForm] = useState({
    name: '',
    emoji: EMOJI_OPTIONS[0],
    description: '',
  });

  const selectedExisting = useMemo(
    () => existingOptions.find((option) => option.id === selectedId) || null,
    [existingOptions, selectedId]
  );

  const handleSubmit = () => {
    if (mode === 'existing') {
      if (!selectedExisting) return;
      onAdd({
        mode: 'existing',
        id: selectedExisting.id,
        name: selectedExisting.name,
        emoji: selectedExisting.emoji || '',
        description: selectedExisting.description || '',
      });
      return;
    }

    if (!form.name.trim()) return;
    onAdd({
      mode: 'new',
      name: form.name.trim(),
      emoji: form.emoji || '',
      description: form.description.trim(),
    });
  };

  return (
    <div className="add-category-overlay" onClick={onClose}>
      <div className="add-category" onClick={(e) => e.stopPropagation()}>
        <div className="add-category__header">
          <h3>➕ Добавить категорию</h3>
          <button onClick={onClose}>
            <X size={20} />
          </button>
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
                <select
                  value={selectedId}
                  onChange={(e) => setSelectedId(e.target.value)}
                >
                  {existingOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.emoji || '📋'} {option.name}
                    </option>
                  ))}
                </select>
              </label>
              {!hasExisting && (
                <p className="add-category__hint">
                  В онтологии нет доступных категорий.
                </p>
              )}
            </>
          ) : (
            <>
              <label>
                Эмодзи
                <div className="add-category__emoji-grid">
                {EMOJI_OPTIONS.map((em, index) => (
                  <button
                    key={index}
                    type="button"
                    className={`add-category__emoji-btn ${form.emoji === em ? 'active' : ''}`}
                    onClick={() => setForm({ ...form, emoji: em })}
                  >
                    {em}
                  </button>
                ))}
                </div>
              </label>

              <label>
                Название категории *
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  autoFocus
                />
              </label>

              <label>
                Описание
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={3}
                />
              </label>
            </>
          )}
        </div>

        <div className="add-category__footer">
          <button className="btn-secondary" onClick={onClose}>
            Отмена
          </button>
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
  );
}