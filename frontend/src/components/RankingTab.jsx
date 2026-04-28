import React, { useState, useCallback, useEffect } from 'react';
import { User, X } from 'lucide-react';
import {RankingIcon } from "@phosphor-icons/react";
import { getVacancyRankings } from '../api/ranking';
import { getErrorMessage } from '../api/errors';
import ForbiddenState from './ForbiddenState';
import AsyncState from './AsyncState';
import './RankingTab.css';

const MEDALS = ['🥇', '🥈', '🥉'];

function ScoreBar({ value, max = 1, color = '#3b82f6' }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="ranking__bar-bg">
      <div className="ranking__bar-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  );
}

function BreakdownModal({ candidate, onClose }) {
  const breakdown = Array.isArray(candidate.breakdown) ? candidate.breakdown : [];
  const score = Math.round(candidate.total_score * 100);
  const required = Math.round(candidate.required_match * 100);
  const desired = Math.round(candidate.desired_match * 100);

  return (
    <div className="ranking__modal-overlay" onClick={onClose}>
      <div className="ranking__modal" onClick={(e) => e.stopPropagation()}>
        <div className="ranking__modal-header">
          <div className="ranking__modal-title">
            <User size={20} />
            <span>{candidate.candidate_external_id}</span>
          </div>
          <button className="ranking__modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="ranking__modal-summary">
          <div className="ranking__modal-metric">
            <span className="ranking__modal-metric-label">Общий балл</span>
            <span className="ranking__modal-metric-value ranking__modal-metric-value--main">
              {score}%
            </span>
          </div>
          <div className="ranking__modal-metric">
            <span className="ranking__modal-metric-label">Обязательные</span>
            <span className="ranking__modal-metric-value ranking__modal-metric-value--required">
              {required}%
            </span>
          </div>
          <div className="ranking__modal-metric">
            <span className="ranking__modal-metric-label">Желательные</span>
            <span className="ranking__modal-metric-value ranking__modal-metric-value--desired">
              {desired}%
            </span>
          </div>
        </div>

        <div className="ranking__modal-breakdown">
          <h4>Детализация по компетенциям</h4>
          {breakdown.length === 0 ? (
            <p className="ranking__modal-empty">Нет данных по компетенциям</p>
          ) : (
            breakdown.map((item) => {
              const coverage = Math.round(item.coverage * 100);
              return (
                <div key={item.competency_id} className="ranking__breakdown-item">
                  <div className="ranking__breakdown-header">
                    <span className="ranking__breakdown-name">{item.competency_name}</span>
                    <div className="ranking__breakdown-badges">
                      {item.required && (
                        <span className="ranking__badge ranking__badge--required">
                          обязательная
                        </span>
                      )}
                      <span className="ranking__badge ranking__badge--coverage">{coverage}%</span>
                    </div>
                  </div>
                  <ScoreBar
                    value={item.matched_weight}
                    max={item.total_weight}
                    color={item.required ? '#f59e0b' : '#3b82f6'}
                  />
                  <div className="ranking__breakdown-meta">
                    <span>
                      Подкомпетенции: {(item.matched_subcompetency_ids || []).length}
                      {' / '}
                      {(item.total_subcompetency_ids || []).length}
                    </span>
                    <span>Вклад в балл: {(item.score_contribution || 0).toFixed(2)}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
export default function RankingTab({ vacancies, notify, navigationTarget = null }) {
  const vacancyList = Array.isArray(vacancies) ? vacancies : [];
  const [selectedVacancyId, setSelectedVacancyId] = useState('');
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [isForbidden, setIsForbidden] = useState(false);

  const loadRankings = useCallback(
    async (vacancyId, focusCandidateId = null) => {
      if (!vacancyId) return;
      setLoading(true);
      setRankings([]);
      setSelectedCandidate(null);
      try {
        const { data } = await getVacancyRankings(vacancyId);
        const nextRankings = data.rankings || [];
        setRankings(nextRankings);
        if (focusCandidateId) {
          const target = nextRankings.find((item) => item.candidate_id === focusCandidateId);
          if (target) {
            setSelectedCandidate(target);
          } else {
            notify('Кандидат не найден в текущем ранжировании вакансии', 'error');
          }
        }
        setIsForbidden(false);
      } catch (error) {
        setIsForbidden(error?.response?.status === 403);
        notify(getErrorMessage(error, { fallback: 'Ошибка загрузки ранжирования' }), 'error');
      } finally {
        setLoading(false);
      }
    },
    [notify]
  );

  const handleVacancyChange = (e) => {
    const id = e.target.value;
    setSelectedVacancyId(id);
    loadRankings(id);
  };

  useEffect(() => {
    if (!navigationTarget?.vacancyId) return;
    setSelectedVacancyId(navigationTarget.vacancyId);
    loadRankings(navigationTarget.vacancyId, navigationTarget.candidateId || null);
  }, [navigationTarget, loadRankings]);

  return (
    <div className="ranking">
      {isForbidden && <ForbiddenState hint="Недостаточно прав для просмотра ранжирования." />}

      <div className="ranking__select-row">
        <select
          className="ranking__select"
          value={selectedVacancyId}
          onChange={handleVacancyChange}
        >
          <option value="">Выберите вакансию</option>
          {vacancyList.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
      </div>

      {!selectedVacancyId && (
        <div className="ranking__empty">
          <RankingIcon size={52} weight="bold"/>
          <p>Выберите вакансию, чтобы увидеть ранжирование кандидатов</p>
          {vacancyList.length === 0 && (
            <p className="ranking__empty-hint">
              Нет вакансий со статусом "Готово". Сначала завершите редактирование вакансии.
            </p>
          )}
        </div>
      )}

      {selectedVacancyId && loading && (
        <AsyncState kind="loading" title="Загрузка ранжирования..." />
      )}

      {selectedVacancyId && !loading && rankings.length === 0 && (
        <AsyncState
          kind="empty"
          title="Кандидатов пока нет"
          hint="Ранжирование появится после того как кандидаты пройдут тестирование"
        />
      )}

      {!loading && rankings.length > 0 && (
        <div className="ranking__table-wrap">
          <div className="ranking__table-header">
            <span className="ranking__col-rank">#</span>
            <span className="ranking__col-name">Кандидат</span>
            <span className="ranking__col-score">Общий балл</span>
            <span className="ranking__col-required">Обязательные</span>
            <span className="ranking__col-desired">Желательные</span>
          </div>

          {rankings.map((candidate, idx) => {
            const score = Math.round(candidate.total_score * 100);
            const required = Math.round(candidate.required_match * 100);
            const desired = Math.round(candidate.desired_match * 100);
            const medal = MEDALS[idx];

            return (
              <div
                key={candidate.candidate_id}
                className={`ranking__row ${idx < 3 ? `ranking__row--top${idx + 1}` : ''}`}
                onClick={() => setSelectedCandidate(candidate)}
                title="Нажмите для детализации"
              >
                <span className="ranking__col-rank">{medal || idx + 1}</span>

                <span className="ranking__col-name">{candidate.candidate_external_id}</span>

                <div className="ranking__col-score">
                  <span className="ranking__score-value">{score}%</span>
                  <ScoreBar value={score} max={100} color="#3b82f6" />
                </div>

                <div className="ranking__col-required">
                  <span className="ranking__score-value">{required}%</span>
                  <ScoreBar value={required} max={100} color="#f59e0b" />
                </div>

                <div className="ranking__col-desired">
                  <span className="ranking__score-value">{desired}%</span>
                  <ScoreBar value={desired} max={100} color="#8b5cf6" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedCandidate && (
        <BreakdownModal candidate={selectedCandidate} onClose={() => setSelectedCandidate(null)} />
      )}
    </div>
  );
}
