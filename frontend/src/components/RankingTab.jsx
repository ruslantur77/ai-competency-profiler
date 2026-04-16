// frontend/src/components/RankingTab.jsx
import React, { useState, useCallback } from 'react'
import { ChevronDown, ChevronUp, Trophy, User, X } from 'lucide-react'
import { getVacancyRankings } from '../api/ranking'
import { getErrorMessage } from '../api/errors'
import ForbiddenState from './ForbiddenState'
import AsyncState from './AsyncState'
import './RankingTab.css'

// Медали для топ-3
const MEDALS = ['🥇', '🥈', '🥉']

function ScoreBar({ value, max = 1, color = '#3b82f6' }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="ranking__bar-bg">
      <div
        className="ranking__bar-fill"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  )
}

function BreakdownModal({ candidate, onClose }) {
  const score = Math.round(candidate.total_score * 100)
  const required = Math.round(candidate.required_match * 100)
  const desired = Math.round(candidate.desired_match * 100)

  return (
    <div className="ranking__modal-overlay" onClick={onClose}>
      <div className="ranking__modal" onClick={e => e.stopPropagation()}>
        <div className="ranking__modal-header">
          <div className="ranking__modal-title">
            <User size={20} />
            <span>{candidate.candidate_external_id}</span>
          </div>
          <button className="ranking__modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Общие метрики */}
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

        {/* Breakdown по компетенциям */}
        <div className="ranking__modal-breakdown">
          <h4>Детализация по компетенциям</h4>
          {candidate.breakdown.length === 0 ? (
            <p className="ranking__modal-empty">Нет данных по компетенциям</p>
          ) : (
            candidate.breakdown.map(item => {
              const coverage = Math.round(item.coverage * 100)
              return (
                <div key={item.competency_id} className="ranking__breakdown-item">
                  <div className="ranking__breakdown-header">
                    <span className="ranking__breakdown-name">
                      {item.competency_name}
                    </span>
                    <div className="ranking__breakdown-badges">
                      {item.required && (
                        <span className="ranking__badge ranking__badge--required">
                          обязательная
                        </span>
                      )}
                      <span className="ranking__badge ranking__badge--coverage">
                        {coverage}%
                      </span>
                    </div>
                  </div>
                  <ScoreBar
                    value={item.matched_weight}
                    max={item.total_weight}
                    color={item.required ? '#f59e0b' : '#3b82f6'}
                  />
                  <div className="ranking__breakdown-meta">
                    <span>
                      Подкомпетенции: {item.matched_subcompetency_ids.length} / {item.total_subcompetency_ids.length}
                    </span>
                    <span>
                      Вклад в балл: {item.score_contribution.toFixed(2)}
                    </span>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

// MOCK DATA
// const MOCK_RANKINGS = {
//   vacancy_id: 'mock',
//   rankings: [
//     {
//       candidate_id: '1',
//       candidate_external_id: 'ivanov_ivan',
//       total_score: 0.87,
//       required_match: 0.95,
//       desired_match: 0.72,
//       required_score: 0.91,
//       desired_score: 0.68,
//       breakdown: [
//         {
//           competency_id: 'c1',
//           competency_name: 'Python Backend',
//           required: true,
//           matched_weight: 0.9,
//           total_weight: 1.0,
//           coverage: 0.9,
//           score_contribution: 0.32,
//           matched_subcompetency_ids: ['s1', 's2', 's3'],
//           total_subcompetency_ids: ['s1', 's2', 's3', 's4'],
//         },
//         {
//           competency_id: 'c2',
//           competency_name: 'SQL Modeling',
//           required: true,
//           matched_weight: 0.8,
//           total_weight: 1.0,
//           coverage: 0.8,
//           score_contribution: 0.28,
//           matched_subcompetency_ids: ['s5', 's6'],
//           total_subcompetency_ids: ['s5', 's6', 's7'],
//         },
//         {
//           competency_id: 'c3',
//           competency_name: 'Containers and Delivery',
//           required: false,
//           matched_weight: 0.6,
//           total_weight: 1.0,
//           coverage: 0.6,
//           score_contribution: 0.15,
//           matched_subcompetency_ids: ['s8'],
//           total_subcompetency_ids: ['s8', 's9'],
//         },
//       ],
//     },
//     {
//       candidate_id: '2',
//       candidate_external_id: 'petrova_maria',
//       total_score: 0.74,
//       required_match: 0.82,
//       desired_match: 0.61,
//       required_score: 0.79,
//       desired_score: 0.55,
//       breakdown: [
//         {
//           competency_id: 'c1',
//           competency_name: 'Python Backend',
//           required: true,
//           matched_weight: 0.75,
//           total_weight: 1.0,
//           coverage: 0.75,
//           score_contribution: 0.27,
//           matched_subcompetency_ids: ['s1', 's2'],
//           total_subcompetency_ids: ['s1', 's2', 's3', 's4'],
//         },
//         {
//           competency_id: 'c2',
//           competency_name: 'SQL Modeling',
//           required: true,
//           matched_weight: 0.9,
//           total_weight: 1.0,
//           coverage: 0.9,
//           score_contribution: 0.31,
//           matched_subcompetency_ids: ['s5', 's6', 's7'],
//           total_subcompetency_ids: ['s5', 's6', 's7'],
//         },
//         {
//           competency_id: 'c3',
//           competency_name: 'Containers and Delivery',
//           required: false,
//           matched_weight: 0.3,
//           total_weight: 1.0,
//           coverage: 0.3,
//           score_contribution: 0.08,
//           matched_subcompetency_ids: [],
//           total_subcompetency_ids: ['s8', 's9'],
//         },
//       ],
//     },
//     {
//       candidate_id: '3',
//       candidate_external_id: 'sidorov_alex',
//       total_score: 0.61,
//       required_match: 0.65,
//       desired_match: 0.55,
//       required_score: 0.62,
//       desired_score: 0.48,
//       breakdown: [
//         {
//           competency_id: 'c1',
//           competency_name: 'Python Backend',
//           required: true,
//           matched_weight: 0.5,
//           total_weight: 1.0,
//           coverage: 0.5,
//           score_contribution: 0.18,
//           matched_subcompetency_ids: ['s1'],
//           total_subcompetency_ids: ['s1', 's2', 's3', 's4'],
//         },
//         {
//           competency_id: 'c2',
//           competency_name: 'SQL Modeling',
//           required: true,
//           matched_weight: 0.7,
//           total_weight: 1.0,
//           coverage: 0.7,
//           score_contribution: 0.24,
//           matched_subcompetency_ids: ['s5', 's6'],
//           total_subcompetency_ids: ['s5', 's6', 's7'],
//         },
//         {
//           competency_id: 'c3',
//           competency_name: 'Containers and Delivery',
//           required: false,
//           matched_weight: 0.5,
//           total_weight: 1.0,
//           coverage: 0.5,
//           score_contribution: 0.12,
//           matched_subcompetency_ids: ['s8'],
//           total_subcompetency_ids: ['s8', 's9'],
//         },
//       ],
//     },
//     {
//       candidate_id: '4',
//       candidate_external_id: 'kozlov_dmitry',
//       total_score: 0.45,
//       required_match: 0.48,
//       desired_match: 0.40,
//       required_score: 0.44,
//       desired_score: 0.35,
//       breakdown: [
//         {
//           competency_id: 'c1',
//           competency_name: 'Python Backend',
//           required: true,
//           matched_weight: 0.4,
//           total_weight: 1.0,
//           coverage: 0.4,
//           score_contribution: 0.14,
//           matched_subcompetency_ids: ['s1'],
//           total_subcompetency_ids: ['s1', 's2', 's3', 's4'],
//         },
//         {
//           competency_id: 'c2',
//           competency_name: 'SQL Modeling',
//           required: true,
//           matched_weight: 0.5,
//           total_weight: 1.0,
//           coverage: 0.5,
//           score_contribution: 0.17,
//           matched_subcompetency_ids: ['s5'],
//           total_subcompetency_ids: ['s5', 's6', 's7'],
//         },
//         {
//           competency_id: 'c3',
//           competency_name: 'Containers and Delivery',
//           required: false,
//           matched_weight: 0.2,
//           total_weight: 1.0,
//           coverage: 0.2,
//           score_contribution: 0.05,
//           matched_subcompetency_ids: [],
//           total_subcompetency_ids: ['s8', 's9'],
//         },
//       ],
//     },
//   ],
// }

export default function RankingTab({ vacancies, notify }) {
  const [selectedVacancyId, setSelectedVacancyId] = useState('')
  const [rankings, setRankings] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedCandidate, setSelectedCandidate] = useState(null)
  const [isForbidden, setIsForbidden] = useState(false)

  const loadRankings = useCallback(async (vacancyId) => {
    if (!vacancyId) return
    setLoading(true)
    setRankings([])
    try {
      const { data } = await getVacancyRankings(vacancyId)
      setRankings(data.rankings || [])
      setIsForbidden(false)
      
      // Для использования mock данных раскомментируйте 2 строки ниже и закомментируйте 2 строки выше
      // await new Promise(r => setTimeout(r, 600))
      // setRankings(MOCK_RANKINGS.rankings)
    } catch (error) {
      setIsForbidden(error?.response?.status === 403)
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки ранжирования' }), 'error')
    } finally {
      setLoading(false)
    }
  }, [notify])

  const handleVacancyChange = (e) => {
    const id = e.target.value
    setSelectedVacancyId(id)
    loadRankings(id)
  }

  return (
    <div className="ranking">
      {isForbidden && (
        <ForbiddenState hint="Недостаточно прав для просмотра ранжирования." />
      )}

      {/* ===== ВЫБОР ВАКАНСИИ ===== */}
      <div className="ranking__select-row">
        <Trophy size={20} className="ranking__trophy" />
        <select
          className="ranking__select"
          value={selectedVacancyId}
          onChange={handleVacancyChange}
        >
          <option value="">— Выберите вакансию —</option>
          {vacancies.map(v => (
            <option key={v.id} value={v.id}>{v.name}</option>
          ))}
        </select>
      </div>

      {/* ===== СОСТОЯНИЯ ===== */}
      {!selectedVacancyId && (
        <div className="ranking__empty">
          <Trophy size={48} />
          <p>Выберите вакансию чтобы увидеть ранжирование кандидатов</p>
          {vacancies.length === 0 && (
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

      {/* ===== ТАБЛИЦА ===== */}
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
            const score = Math.round(candidate.total_score * 100)
            const required = Math.round(candidate.required_match * 100)
            const desired = Math.round(candidate.desired_match * 100)
            const medal = MEDALS[idx]

            return (
              <div
                key={candidate.candidate_id}
                className={`ranking__row ${idx < 3 ? `ranking__row--top${idx + 1}` : ''}`}
                onClick={() => setSelectedCandidate(candidate)}
                title="Нажмите для детализации"
              >
                <span className="ranking__col-rank">
                  {medal || idx + 1}
                </span>

                <span className="ranking__col-name">
                  {candidate.candidate_external_id}
                </span>

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
            )
          })}
        </div>
      )}

      {/* ===== МОДАЛКА BREAKDOWN ===== */}
      {selectedCandidate && (
        <BreakdownModal
          candidate={selectedCandidate}
          onClose={() => setSelectedCandidate(null)}
        />
      )}
    </div>
  )
}
