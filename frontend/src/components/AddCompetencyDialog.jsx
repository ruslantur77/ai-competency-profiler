// frontend/src/components/AddCompetencyDialog.jsx
import React, { useState } from 'react';
import { X, Plus } from 'lucide-react';
import './AddCompetencyDialog.css';

export default function AddCompetencyDialog({
  categoryName,
  onAdd,
  onClose,
  existingOptions = [],
}) {
  const hasExisting = existingOptions.length > 0;
  const [mode, setMode] = useState(hasExisting ? 'existing' : 'new');
  const [selectedId, setSelectedId] = useState(existingOptions[0]?.id || '');
  const [form, setForm] = useState({
    name: '',
    description: '',
    is_required: true,
  });

  const selectedExisting = existingOptions.find((item) => item.id === selectedId) || null;

  const handleAdd = () => {
    if (mode === 'existing') {
      if (!selectedExisting) return;
      onAdd({
        mode: 'existing',
        id: selectedExisting.id,
        name: selectedExisting.name,
        description: selectedExisting.description || '',
        is_required: form.is_required,
      });
      return;
    }
    if (!form.name.trim()) return;
    onAdd({
      mode: 'new',
      name: form.name.trim(),
      description: form.description.trim(),
      is_required: form.is_required,
    });
  };

  return (
    <div className="add-comp-overlay" onClick={onClose}>
      <div className="add-comp" onClick={(e) => e.stopPropagation()}>
        <div className="add-comp__header">
          <h3>➕ Добавить компетенцию</h3>
          <button onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="add-comp__context">
          Категория: <strong>{categoryName}</strong>
        </div>

        <div className="add-comp__mode">
          <button
            type="button"
            className={`add-comp__mode-btn ${mode === 'existing' ? 'active' : ''}`}
            disabled={!hasExisting}
            onClick={() => setMode('existing')}
          >
            Из онтологии
          </button>
          <button
            type="button"
            className={`add-comp__mode-btn ${mode === 'new' ? 'active' : ''}`}
            onClick={() => setMode('new')}
          >
            Новая
          </button>
        </div>

        <div className="add-comp__body">
          {mode === 'existing' ? (
            <label>
              Компетенция из онтологии
              <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
                {existingOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label>
              Название компетенции *
              <textarea
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Например: SQL — аналитические функции, подзапросы"
                rows={3}
                autoFocus
              />
            </label>
          )}

          <label>
            Описание
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Подробнее о компетенции..."
              rows={2}
            />
          </label>

          <label className="add-comp__checkbox-label">
            <input
              type="checkbox"
              checked={form.is_required}
              onChange={(e) => setForm({ ...form, is_required: e.target.checked })}
            />
            Обязательная компетенция
          </label>
        </div>

        <div className="add-comp__footer">
          <button className="btn-secondary" onClick={onClose}>
            Отмена
          </button>
          <button
            className="btn-primary"
            onClick={handleAdd}
            disabled={mode === 'existing' ? !selectedExisting : !form.name.trim()}
          >
            <Plus size={16} /> Добавить
          </button>
        </div>
      </div>
    </div>
  );
}
