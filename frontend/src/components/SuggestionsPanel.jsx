// frontend/src/components/SuggestionsPanel.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Check,
  X,
  CheckCheck,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Save,
} from 'lucide-react';
import { getSuggestions, decideSuggestionsBulk } from '../api/suggestions';
import { getErrorMessage } from '../api/errors';
import './SuggestionsPanel.css';

const STAGE_LABELS = {
  category: '📁 Категория',
  competency: '🎯 Компетенция',
  sub_competency: '🔹 Подкомпетенция',
};

const STAGE_ORDER = ['category', 'competency', 'sub_competency'];

export default function SuggestionsPanel({
  vacancyId,
  categoryNodes,
  competencyNodes,
  onApprove,
  notify,
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const saveInFlightRef = useRef(false);
  // id → 'approved' | 'rejected'
  const [decisions, setDecisions] = useState({});

  const loadSuggestions = useCallback(async () => {
    try {
      const { data } = await getSuggestions(vacancyId);
      setSuggestions(data.filter((s) => s.status === 'pending'));
      setDecisions({});
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки предложений' }), 'error');
    } finally {
      setLoading(false);
    }
  }, [vacancyId, notify]);

  useEffect(() => {
    loadSuggestions();
  }, [loadSuggestions]);

  // ===== ХЛЕБНЫЕ КРОШКИ =====
  const getCategoryName = useCallback(
    (categoryId) => {
      if (!categoryId) return null;
      const node = categoryNodes.find((c) => c.category_id === categoryId);
      return node ? `${node.category_emoji || ''} ${node.category_name}`.trim() : null;
    },
    [categoryNodes]
  );

  const getCompetencyName = useCallback(
    (competencyId) => {
      if (!competencyId) return null;
      const node = competencyNodes.find((c) => c.competency_id === competencyId);
      return node ? node.competency_name : null;
    },
    [competencyNodes]
  );

  // ===== ЛОКАЛЬНЫЕ РЕШЕНИЯ =====
  const decide = useCallback((suggestion, status) => {
    setDecisions((prev) => {
      // Повторный клик — снимаем решение
      if (prev[suggestion.id] === status) {
        const next = { ...prev };
        delete next[suggestion.id];
        return next;
      }
      return { ...prev, [suggestion.id]: status };
    });
  }, []);

  const approveAll = useCallback(() => {
    const next = {};
    suggestions.forEach((s) => {
      next[s.id] = 'approved';
    });
    setDecisions(next);
  }, [suggestions]);

  const rejectAll = useCallback(() => {
    const next = {};
    suggestions.forEach((s) => {
      next[s.id] = 'rejected';
    });
    setDecisions(next);
  }, [suggestions]);

  // ===== СОХРАНЕНИЕ ПРЕДЛОЖЕНИЙ =====
  const handleSaveDecisions = useCallback(async () => {
    if (saveInFlightRef.current) return;
    saveInFlightRef.current = true;
    setSaving(true);
    try {
      const payload = suggestions
        .filter((s) => decisions[s.id])
        .map((s) => ({
          suggestion_id: s.id,
          status: decisions[s.id],
        }));

      if (payload.length === 0) return;

      await decideSuggestionsBulk(vacancyId, payload);

      // Обновляем граф один раз после всех запросов
      await onApprove();

      const approvedCount = payload.filter((item) => item.status === 'approved').length;
      const rejectedCount = payload.length - approvedCount;
      notify(`✅ Применено: ${approvedCount} одобрено, ${rejectedCount} отклонено`);

      // Перезагружаем suggestions — pending должны исчезнуть
      await loadSuggestions();
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка при сохранении предложений' }), 'error');
    } finally {
      saveInFlightRef.current = false;
      setSaving(false);
    }
  }, [vacancyId, suggestions, decisions, onApprove, notify, loadSuggestions]);

  // ===== RENDER =====
  if (loading) {
    return (
      <div className="suggestions-panel">
        <div className="suggestions-panel__loading">
          <Loader2 size={16} className="spin" /> Загрузка предложений...
        </div>
      </div>
    );
  }

  if (suggestions.length === 0) return null;

  const grouped = STAGE_ORDER.reduce((acc, stage) => {
    const items = suggestions.filter((s) => s.stage === stage);
    if (items.length > 0) acc[stage] = items;
    return acc;
  }, {});

  const decidedCount = Object.keys(decisions).length;
  const allDecided = decidedCount === suggestions.length;
  const canSave = allDecided && !saving;

  return (
    <div className="suggestions-panel">
      <div className="suggestions-panel__header" onClick={() => setExpanded((e) => !e)}>
        <div className="suggestions-panel__header-left">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span>✨ Предложения AI</span>
          <span className="suggestions-panel__count">{suggestions.length}</span>
          {decidedCount > 0 && !allDecided && (
            <span className="suggestions-panel__decided">
              {decidedCount} из {suggestions.length} отмечено
            </span>
          )}
          {allDecided && (
            <span className="suggestions-panel__decided suggestions-panel__decided--done">
              ✅ Все отмечены
            </span>
          )}
        </div>

        <div className="suggestions-panel__header-actions" onClick={(e) => e.stopPropagation()}>
          <button
            className="suggestions-panel__btn suggestions-panel__btn--approve"
            onClick={approveAll}
            disabled={saving}
            title="Отметить все как одобренные"
          >
            <CheckCheck size={14} /> Добавить все
          </button>
          <button
            className="suggestions-panel__btn suggestions-panel__btn--reject"
            onClick={rejectAll}
            disabled={saving}
            title="Отметить все как отклонённые"
          >
            <XCircle size={14} /> Отклонить все
          </button>
          <button
            className="suggestions-panel__btn suggestions-panel__btn--save"
            onClick={handleSaveDecisions}
            disabled={!canSave}
            title={!allDecided ? 'Отметьте все предложения' : 'Применить решения'}
          >
            {saving ? (
              <>
                <Loader2 size={14} className="spin" /> Сохранение...
              </>
            ) : (
              <>
                <Save size={14} /> Сохранить предложения
              </>
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="suggestions-panel__body">
          {Object.entries(grouped).map(([stage, items]) => (
            <div key={stage} className="suggestions-panel__group">
              <div className="suggestions-panel__group-label">{STAGE_LABELS[stage]}</div>
              {items.map((s) => {
                const decision = decisions[s.id];
                const categoryName = getCategoryName(s.parent_category_id);
                const competencyName = getCompetencyName(s.parent_competency_id);

                return (
                  <div
                    key={s.id}
                    className={`suggestions-panel__item ${
                      decision === 'approved'
                        ? 'suggestions-panel__item--approved'
                        : decision === 'rejected'
                          ? 'suggestions-panel__item--rejected'
                          : ''
                    }`}
                  >
                    <div className="suggestions-panel__item-info">
                      <span className="suggestions-panel__item-name">{s.name}</span>

                      {/* Хлебные крошки — только если нашли имя */}
                      {s.stage === 'competency' && categoryName && (
                        <span className="suggestions-panel__item-meta">{categoryName}</span>
                      )}
                      {s.stage === 'sub_competency' && (competencyName || categoryName) && (
                        <span className="suggestions-panel__item-meta">
                          {categoryName && <span>{categoryName}</span>}
                          {categoryName && competencyName && <span> → </span>}
                          {competencyName && <span>🎯 {competencyName}</span>}
                        </span>
                      )}

                      {s.description && (
                        <span className="suggestions-panel__item-desc">{s.description}</span>
                      )}
                      {s.reason && (
                        <span className="suggestions-panel__item-reason">💡 {s.reason}</span>
                      )}
                    </div>

                    <div className="suggestions-panel__item-actions">
                      <button
                        className={`suggestions-panel__btn ${
                          decision === 'approved'
                            ? 'suggestions-panel__btn--approve-active'
                            : 'suggestions-panel__btn--approve'
                        }`}
                        onClick={() => decide(s, 'approved')}
                        disabled={saving}
                        title="Добавить в граф"
                      >
                        <Check size={14} />
                      </button>
                      <button
                        className={`suggestions-panel__btn ${
                          decision === 'rejected'
                            ? 'suggestions-panel__btn--reject-active'
                            : 'suggestions-panel__btn--reject'
                        }`}
                        onClick={() => decide(s, 'rejected')}
                        disabled={saving}
                        title="Отклонить"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
