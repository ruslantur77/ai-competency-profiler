import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { BarChart3, ExternalLink, Trash2, User } from 'lucide-react'
import {
  deleteCandidate,
  getCandidate,
  getCandidateProfile,
  listCandidates,
} from '../api/candidates'
import { getErrorMessage } from '../api/errors'
import usePaginatedResource from '../hooks/usePaginatedResource'
import AsyncState from './AsyncState'
import ConfirmDialog from './ConfirmDialog'
import CandidateRow from './candidates/CandidateRow'
import CandidateProfileTable from './candidates/CandidateProfileTable'
import CandidateStats from './candidates/CandidateStats'
import { getCandidateStatusMeta } from '../domain/statusMeta'
import { formatDateTime } from '../utils/formatters'
import './CandidatesTab.css'

const PAGE_LIMIT = 20

export default function CandidatesTab({
  notify,
  vacancies,
  onOpenVacancy,
  onOpenRanking,
}) {
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

  const fetchCandidatesPage = useCallback(async ({ offset, limit }) => {
    const { data } = await listCandidates({ limit, offset })
    return data
  }, [])

  const {
    items: candidates,
    total: totalCandidates,
    offset: pageOffset,
    limit: pageLimit,
    loading,
    loadPage: loadCandidatesPage,
  } = usePaginatedResource({
    fetchPage: fetchCandidatesPage,
    initialLimit: PAGE_LIMIT,
    initialOffset: 0,
    onError: (error) => notify(
      getErrorMessage(error, { fallback: 'Ошибка загрузки кандидатов' }),
      'error'
    ),
  })

  useEffect(() => {
    loadCandidatesPage({ offset: 0, limit: PAGE_LIMIT })
  }, [loadCandidatesPage])

  useEffect(() => {
    setSelectedCandidateId((prev) => {
      if (prev && candidates.some((item) => item.id === prev)) return prev
      return candidates[0]?.id || null
    })
  }, [candidates])

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

  const pageStatusCounters = useMemo(() => {
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

  const currentPage = Math.floor(pageOffset / pageLimit) + 1
  const totalPages = Math.max(1, Math.ceil(totalCandidates / pageLimit))
  const canGoPrev = pageOffset > 0
  const canGoNext = pageOffset + pageLimit < totalCandidates

  const goPrevPage = () => {
    if (!canGoPrev) return
    const nextOffset = Math.max(0, pageOffset - pageLimit)
    loadCandidatesPage({ offset: nextOffset, limit: pageLimit })
  }

  const goNextPage = () => {
    if (!canGoNext) return
    loadCandidatesPage({ offset: pageOffset + pageLimit, limit: pageLimit })
  }

  const handleDeleteCandidate = async () => {
    if (!confirmDelete) return
    try {
      await deleteCandidate(confirmDelete.id)
      const nextTotal = Math.max(0, totalCandidates - 1)
      const lastValidOffset = nextTotal > 0
        ? Math.floor((nextTotal - 1) / pageLimit) * pageLimit
        : 0
      const nextOffset = Math.min(pageOffset, lastValidOffset)

      await loadCandidatesPage({ offset: nextOffset, limit: pageLimit, silent: true })
      setConfirmDelete(null)
      notify(`Кандидат "${confirmDelete.external_id}" удален`)
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка удаления кандидата' }), 'error')
    }
  }

  if (loading) {
    return <AsyncState kind="loading" title="Загрузка кандидатов..." />
  }

  if (totalCandidates === 0) {
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
  const selectedStatusMeta = candidateDetail
    ? getCandidateStatusMeta(candidateDetail.status)
    : null

  return (
    <div className="candidates-tab">
      <CandidateStats total={totalCandidates} counters={pageStatusCounters} />

      <div className="candidates-tab__layout">
        <div className="candidates-tab__list-wrap">
          <div className="candidates-tab__pagination">
            <button className="btn-secondary" onClick={goPrevPage} disabled={!canGoPrev}>
              Назад
            </button>
            <span>
              Страница {currentPage} / {totalPages}
            </span>
            <button className="btn-secondary" onClick={goNextPage} disabled={!canGoNext}>
              Вперед
            </button>
          </div>
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
                  Статус: {selectedStatusMeta?.label || candidateDetail.status}
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

              <CandidateProfileTable profile={candidateProfile} />
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
