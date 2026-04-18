// frontend/src/components/AddSubDialog.jsx
import React, { useState } from 'react';
import { X, Plus } from 'lucide-react';
import {
  COMPETENCY_LEVEL_OPTIONS,
  normalizeTargetLevel,
  normalizeWeight,
} from '../domain/competencyGraph';
import './AddSubDialog.css';

export default function AddSubDialog({ competencyName, onAdd, onClose, existingOptions = [] }) {
  const hasExisting = existingOptions.length > 0;
  const [mode, setMode] = useState(hasExisting ? 'existing' : 'new');
  const [selectedId, setSelectedId] = useState(existingOptions[0]?.id || '');
  const [form, setForm] = useState({
    name: '',
    target_level: 2,
    description: '',
    weight: 1.0,
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
        target_level: normalizeTargetLevel(selectedExisting.target_level ?? form.target_level),
        weight: normalizeWeight(selectedExisting.weight ?? form.weight),
      });
      return;
    }

    if (!form.name.trim()) return;
    onAdd({
      mode: 'new',
      name: form.name.trim(),
      target_level: normalizeTargetLevel(form.target_level),
      description: form.description.trim(),
      weight: normalizeWeight(form.weight),
    });
  };

  return (
    <div className="add-dialog-overlay" onClick={onClose}>
      <div className="add-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="add-dialog__header">
          <h3>➕ Добавить подкомпетенцию</h3>
          <button onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="add-dialog__context">
          Компетенция: <strong>{competencyName}</strong>
        </div>

        <div className="add-dialog__mode">
          <button
            type="button"
            className={`add-dialog__mode-btn ${mode === 'existing' ? 'active' : ''}`}
            disabled={!hasExisting}
            onClick={() => setMode('existing')}
          >
            Из онтологии
          </button>
          <button
            type="button"
            className={`add-dialog__mode-btn ${mode === 'new' ? 'active' : ''}`}
            onClick={() => setMode('new')}
          >
            Новая
          </button>
        </div>

        <div className="add-dialog__body">
          {mode === 'existing' ? (
            <label>
              Подкомпетенция из онтологии
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
              Название *
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Например: Работа с индексами"
                autoFocus
              />
            </label>
          )}

          <label>
            Уровень
            <select
              value={form.target_level}
              onChange={(e) => setForm({ ...form, target_level: parseInt(e.target.value) })}
            >
              {COMPETENCY_LEVEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Описание
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Что конкретно нужно уметь..."
              rows={3}
            />
          </label>

          <label>
            Вес (0.0 — 1.0)
            <input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={form.weight}
              onChange={(e) => setForm({ ...form, weight: e.target.value })}
            />
          </label>
        </div>

        <div className="add-dialog__footer">
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
