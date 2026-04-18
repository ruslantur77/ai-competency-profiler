import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { BarChart3, ExternalLink, Trash2, User } from 'lucide-react'
import {
  deleteCandidate,
  getCandidate,
  getCandidateProfile,
  listCandidates,
} from '../api/candidates'
import { getErrorMessage } from '../api/errors'
import AsyncState from './AsyncState'
import ConfirmDialog from './ConfirmDialog'
import './CandidatesTab.css'

const STATUS_META = {
  pending: { label: 'Ожидает оценки', badge: 'pending' },
  completed: { label: 'Оценен', badge: 'completed' },
  failed: { label: 'Ошибка оценки', badge: 'failed' },
}

const formatDateTime = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleString('ru-RU')
}

function CandidateRow({ candidate, selected, onSelect }) {
  const statusMeta = STATUS_META[candidate.status] || STATUS_META.pending
  return (
    <button
      className={`candidates-tab__row ${selected ? 'is-selected' : ''}`}
      onClick={() => onSelect(candidate.id)}
    >
      <div className="candidates-tab__row-main">
        <span className="candidates-tab__candidate-id">{candidate.external_id}</span>
        <span className={`candidates-tab__status candidates-tab__status--${statusMeta.badge}`}>
          {statusMeta.label}
        </span>
      </div>
      <div className="candidates-tab__row-meta">
        <span>{formatDateTime(candidate.last_assessment_at)}</span>
      </div>
    </button>
  )
}

function CandidateProfile({ profile }) {
  if (!profile) return null
  const score = Math.round((profile.total_score || 0) * 100)

  return (
    <div className="candidates-tab__profile">
      <div className="candidates-tab__profile-score">
        <span className="candidates-tab__profile-score-label">Итоговый score</span>
        <strong>{score}%</strong>
      </div>
      <div className="candidates-tab__profile-table">
        <div className="candidates-tab__profile-header">
          <span>Категория</span>
          <span>Компетенция</span>
          <span>Описание</span>
          <span>Уровень</span>
          <span>Confidence</span>
        </div>
        {profile.competency_scores.length === 0 ? (
          <div className="candidates-tab__profile-empty">Нет оцененных компетенций</div>
        ) : (
          profile.competency_scores.map((item) => (
            <div key={item.competency_id} className="candidates-tab__profile-row">
              <span>{item.category_name || item.category_id || '—'}</span>
              <span>{item.competency_name || item.competency_id}</span>
              <span className="candidates-tab__profile-description">
                {item.competency_description || '—'}
              </span>
              <span>{item.level}</span>
              <span>{Math.round((item.confidence || 0) * 100)}%</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default function CandidatesTab({
  notify,
  vacancies,
  onOpenVacancy,
  onOpenRanking,
}) {
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedCandidateId, setSelectedCandidateId] = useState(null)
  const [candidateDetail, setCandidateDetail] = useState(null)
  const [candidateProfile, setCandidateProfile] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(null)

  const vacancyMap = useMemo(
    () => new Map(vacancies.map((vacancy) => [vacancy.id, vacancy])),
    [vacancies]
  )

  const selectedCandidate = useMemo(
    () => candidates.find((item) => item.id === selectedCandidateId) || null,
    [candidates, selectedCandidateId]
  )

  const fetchCandidates = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await listCandidates()
      setCandidates(data || [])
      setSelectedCandidateId((prev) => prev || data?.[0]?.id || null)
    } catch (error) {
      setCandidates([])
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки кандидатов' }), 'error')
    } finally {
      setLoading(false)
    }
  }, [notify])

  useEffect(() => {
    fetchCandidates()
  }, [fetchCandidates])

  useEffect(() => {
    if (!selectedCandidateId) {
      setCandidateDetail(null)
      setCandidateProfile(null)
      return
    }

    const loadDetail = async () => {
      setDetailLoading(true)
      try {
        const [detailResult, profileResult] = await Promise.all([
          getCandidate(selectedCandidateId),
          getCandidateProfile(selectedCandidateId),
        ])
        setCandidateDetail(detailResult.data || null)
        setCandidateProfile(profileResult.data || null)
      } catch (error) {
        setCandidateDetail(null)
        setCandidateProfile(null)
        notify(
          getErrorMessage(error, { fallback: 'Ошибка загрузки профиля кандидата' }),
          'error'
        )
      } finally {
        setDetailLoading(false)
      }
    }

    loadDetail()
  }, [selectedCandidateId, notify])

  const statusCounters = useMemo(() => {
    return candidates.reduce(
      (acc, item) => {
        if (item.status === 'completed') acc.completed += 1
        else if (item.status === 'failed') acc.failed += 1
        else acc.pending += 1
        return acc
      },
      { pending: 0, completed: 0, failed: 0 }
    )
  }, [candidates])

  const handleDeleteCandidate = async () => {
    if (!confirmDelete) return
    try {
      await deleteCandidate(confirmDelete.id)
      setCandidates((prevList) => {
        const nextList = prevList.filter((item) => item.id !== confirmDelete.id)
        setSelectedCandidateId((prevSelected) => {
          if (prevSelected !== confirmDelete.id) return prevSelected
          return nextList[0]?.id || null
        })
        return nextList
      })
      setConfirmDelete(null)
      notify(`Кандидат "${confirmDelete.external_id}" удален`)
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка удаления кандидата' }), 'error')
    }
  }

  if (loading) {
    return <AsyncState kind="loading" title="Загрузка кандидатов..." />
  }

  if (candidates.length === 0) {
    return (
      <AsyncState
        kind="empty"
        title="👤 Кандидатов пока нет"
        hint="Кандидаты появятся после прохождения тестирования во внешней системе"
      />
    )
  }

  const selectedVacancy = selectedCandidate
    ? vacancyMap.get(selectedCandidate.vacancy_id)
    : null

  return (
    <div className="candidates-tab">
      <div className="candidates-tab__stats">
        <div className="candidates-tab__stat">
          <span className="candidates-tab__stat-value">{candidates.length}</span>
          <span className="candidates-tab__stat-label">Всего</span>
        </div>
        <div className="candidates-tab__stat candidates-tab__stat--completed">
          <span className="candidates-tab__stat-value">{statusCounters.completed}</span>
          <span className="candidates-tab__stat-label">Completed</span>
        </div>
        <div className="candidates-tab__stat candidates-tab__stat--pending">
          <span className="candidates-tab__stat-value">{statusCounters.pending}</span>
          <span className="candidates-tab__stat-label">Pending</span>
        </div>
        <div className="candidates-tab__stat candidates-tab__stat--failed">
          <span className="candidates-tab__stat-value">{statusCounters.failed}</span>
          <span className="candidates-tab__stat-label">Failed</span>
        </div>
      </div>

      <div className="candidates-tab__layout">
        <div className="candidates-tab__list">
          {candidates.map((candidate) => (
            <CandidateRow
              key={candidate.id}
              candidate={candidate}
              selected={candidate.id === selectedCandidateId}
              onSelect={setSelectedCandidateId}
            />
          ))}
        </div>

        <div className="candidates-tab__detail">
          {detailLoading ? (
            <AsyncState kind="loading" title="Загрузка профиля..." />
          ) : !selectedCandidate || !candidateDetail ? (
            <AsyncState kind="empty" title="Выберите кандидата" />
          ) : (
            <>
              <div className="candidates-tab__detail-header">
                <div className="candidates-tab__detail-title">
                  <User size={18} />
                  <h3>{candidateDetail.external_id}</h3>
                </div>
                <span className="candidates-tab__detail-id">{candidateDetail.id}</span>
              </div>

              <div className="candidates-tab__detail-meta">
                <span>
                  Статус: {STATUS_META[candidateDetail.status]?.label || candidateDetail.status}
                </span>
                <span>Последняя оценка: {formatDateTime(candidateDetail.last_assessment_at)}</span>
                <span>
                  Вакансия: {selectedVacancy?.name || candidateDetail.vacancy_id}
                </span>
              </div>

              <div className="candidates-tab__actions">
                <button
                  className="btn-secondary"
                  onClick={() => onOpenVacancy(candidateDetail.vacancy_id)}
                >
                  <ExternalLink size={14} />
                  Открыть вакансию
                </button>
                <button
                  className="btn-secondary"
                  onClick={() =>
                    onOpenRanking({
                      vacancyId: candidateDetail.vacancy_id,
                      candidateId: candidateDetail.id,
                    })
                  }
                >
                  <BarChart3 size={14} />
                  В ранжирование
                </button>
                <button
                  className="btn-danger"
                  onClick={() => setConfirmDelete(candidateDetail)}
                >
                  <Trash2 size={14} />
                  Удалить
                </button>
              </div>

              <CandidateProfile profile={candidateProfile} />
            </>
          )}
        </div>
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title="Удаление кандидата"
          message={`Удалить кандидата "${confirmDelete.external_id}"? Операция необратима.`}
          confirmLabel="Удалить кандидата"
          requireText={confirmDelete.external_id}
          requireHint={`Для подтверждения введите внешний id: ${confirmDelete.external_id}`}
          onCancel={() => setConfirmDelete(null)}
          onConfirm={handleDeleteCandidate}
        />
      )}
    </div>
  )
}
