// frontend/src/components/VacancyEditor.jsx
import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, RotateCcw, Loader2 } from 'lucide-react'
import VacancySidebar from './VacancySidebar'
import MindMap from './MindMap'
import EditCategoryDialog from './EditCategoryDialog'
import SuggestionsPanel from './SuggestionsPanel'
import ForbiddenState from './ForbiddenState'
import { getVacancy, updateGraph } from '../api/vacancies'
import { getErrorMessage } from '../api/errors'
import { canEditGraph, canUseSuggestions } from '../api/roles'
import {
  buildVacancyGraphDTO,
  isUuidLike,
  nextPosition,
  normalizeTargetLevel,
  normalizeWeight,
} from '../domain/competencyGraph'
import './VacancyEditor.css'

// ===== HELPERS =====
const tempId = () => crypto.randomUUID()
const EDITABLE_STATUSES = new Set(['draft', 'ready'])
const VACANCY_STATUS_LABELS = {
  pending: 'Извлечение компетенций',
  draft: 'Черновик',
  ready: 'Готово',
  failed: 'Ошибка обработки',
}

export default function VacancyEditor({ notify, role }) {
  const { vacancyId } = useParams()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [vacancy, setVacancy] = useState(null)

  const [categoryNodes, setCategoryNodes] = useState([])
  const [competencyNodes, setCompetencyNodes] = useState([])
  const [subCompetencyNodes, setSubCompetencyNodes] = useState([])

  const [originalNodes, setOriginalNodes] = useState(null)
  const [isDirty, setIsDirty] = useState(false)
  const [addingCategory, setAddingCategory] = useState(false)
  const [isForbidden, setIsForbidden] = useState(false)
  const canEdit = canEditGraph(role)
  const isEditableStatus = EDITABLE_STATUSES.has(vacancy?.status)
  const canMutateGraph = canEdit && isEditableStatus
  const canReviewSuggestions = canUseSuggestions(role) && vacancy?.status === 'draft'

  // ===== ЗАГРУЗКА =====
  const loadVacancy = useCallback(async () => {
    try {
      const { data } = await getVacancy(vacancyId)
      setVacancy(data)
      const cats = data.category_nodes || []
      const comps = data.competency_nodes || []
      const subs = data.sub_competency_nodes || []
      setCategoryNodes(cats)
      setCompetencyNodes(comps)
      setSubCompetencyNodes(subs)
      setOriginalNodes({ cats, comps, subs })
      setIsDirty(false)
      setIsForbidden(false)
    } catch (error) {
      const forbidden = error?.response?.status === 403
      setIsForbidden(forbidden)
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки вакансии' }), 'error')
      if (!forbidden) {
        navigate('/')
      }
    } finally {
      setLoading(false)
    }
  }, [vacancyId, notify, navigate])

  useEffect(() => {
    loadVacancy()
  }, [loadVacancy])

  // ===== СОХРАНЕНИЕ ГРАФА =====
  const handleSave = async () => {
    if (!canMutateGraph) {
      notify('Недостаточно прав для редактирования графа', 'error')
      return
    }
    setSaving(true)
    try {
      const dto = buildVacancyGraphDTO(categoryNodes, competencyNodes, subCompetencyNodes)
      await updateGraph(vacancyId, dto)
  
      // Читаем свежие данные с именами через GET, не из ответа PATCH
      const { data: fresh } = await getVacancy(vacancyId)
      const cats = fresh.category_nodes || []
      const comps = fresh.competency_nodes || []
      const subs = fresh.sub_competency_nodes || []
  
      setVacancy(fresh)
      setCategoryNodes(cats)
      setCompetencyNodes(comps)
      setSubCompetencyNodes(subs)
      setOriginalNodes({ cats, comps, subs })
      setIsDirty(false)
      notify('✅ Граф компетенций сохранён')
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка сохранения' }), 'error')
    } finally {
      setSaving(false)
    }
  }

  // ===== ОТМЕНА =====
  const handleDiscard = () => {
    if (!originalNodes) return
    setCategoryNodes(originalNodes.cats)
    setCompetencyNodes(originalNodes.comps)
    setSubCompetencyNodes(originalNodes.subs)
    setIsDirty(false)
    notify('↩️ Изменения отменены')
  }

  const markDirty = () => setIsDirty(true)

  // ===== SUGGESTIONS =====
  // Вызывается после того как SuggestionsPanel отправила все decisions на бек
  // Перечитываем граф — бек уже добавил approved узлы
// Вызывается после того как SuggestionsPanel отправила все decisions
const handleSuggestionsApplied = useCallback(async () => {
  try {
    // 1. Читаем граф — бек уже добавил approved узлы
    const { data } = await getVacancy(vacancyId)
    const cats = data.category_nodes || []
    const comps = data.competency_nodes || []
    const subs = data.sub_competency_nodes || []

    // 2. Сохраняем граф → бек переводит статус в ready
    await updateGraph(vacancyId, buildVacancyGraphDTO(cats, comps, subs))

    // 3. Читаем ЕЩЁ РАЗ — теперь с заполненными именами
    const { data: fresh } = await getVacancy(vacancyId)
    const freshCats = fresh.category_nodes || []
    const freshComps = fresh.competency_nodes || []
    const freshSubs = fresh.sub_competency_nodes || []

    setVacancy(fresh)
    setCategoryNodes(freshCats)
    setCompetencyNodes(freshComps)
    setSubCompetencyNodes(freshSubs)
    setOriginalNodes({ cats: freshCats, comps: freshComps, subs: freshSubs })
    setIsDirty(false)

  } catch (error) {
    notify(getErrorMessage(error, { fallback: 'Ошибка обновления графа' }), 'error')
  }
}, [vacancyId, notify])

  // ===== КАТЕГОРИИ =====
  const handleUpdateCategory = (updated) => {
    if (!canMutateGraph) return
    setCategoryNodes(prev => prev.map(c =>
      c.category_id === updated.category_id ? { ...c, ...updated } : c
    ))
    markDirty()
  }

  const handleDeleteCategory = (categoryId) => {
    if (!canMutateGraph) return
    const removedCompIds = competencyNodes
      .filter(c => c.category_id === categoryId)
      .map(c => c.competency_id)
    setCategoryNodes(prev => prev.filter(c => c.category_id !== categoryId))
    setCompetencyNodes(prev => prev.filter(c => c.category_id !== categoryId))
    setSubCompetencyNodes(prev =>
      prev.filter(s => !removedCompIds.includes(s.competency_id))
    )
    markDirty()
  }

  const handleAddCategorySubmit = (newCat) => {
    if (!canMutateGraph) return
    const id = tempId()
    setCategoryNodes(prev => [...prev, {
      id,
      vacancy_id: vacancyId,
      category_id: id,
      category_name: newCat.name,
      category_emoji: newCat.emoji || '',
      category_description: newCat.description || '',
      position: nextPosition(prev),
    }])
    setAddingCategory(false)
    markDirty()
  }

  // ===== КОМПЕТЕНЦИИ =====
  const handleUpdateCompetency = (updated) => {
    if (!canMutateGraph) return
    setCompetencyNodes(prev => prev.map(c =>
      c.competency_id === updated.competency_id ? { ...c, ...updated } : c
    ))
    markDirty()
  }

  const handleDeleteCompetency = (competencyId) => {
    if (!canMutateGraph) return
    setCompetencyNodes(prev => prev.filter(c => c.competency_id !== competencyId))
    setSubCompetencyNodes(prev => prev.filter(s => s.competency_id !== competencyId))
    markDirty()
  }

  const handleAddCompetency = (categoryId, newComp) => {
    if (!canMutateGraph) return
    const id = tempId()
    setCompetencyNodes(prev => [...prev, {
      id,
      vacancy_id: vacancyId,
      competency_id: id,
      category_id: categoryId,
      competency_name: newComp.name,
      competency_description: newComp.description || '',
      is_required: newComp.is_required ?? true,
      position: nextPosition(prev, c => c.category_id === categoryId),
    }])
    markDirty()
  }

  // ===== ПОДКОМПЕТЕНЦИИ =====
  const handleUpdateSub = (updatedSub) => {
    if (!canMutateGraph) return
    setSubCompetencyNodes(prev => prev.map(s =>
      s.sub_competency_id === updatedSub.sub_competency_id
        ? {
          ...s,
          ...updatedSub,
          target_level: normalizeTargetLevel(updatedSub.target_level),
          weight: normalizeWeight(updatedSub.weight),
        }
        : s
    ))
    markDirty()
  }

  const handleDeleteSub = (subCompetencyId) => {
    if (!canMutateGraph) return
    setSubCompetencyNodes(prev =>
      prev.filter(s => s.sub_competency_id !== subCompetencyId)
    )
    markDirty()
  }

  const handleAddSub = (competencyId, newSub) => {
    if (!canMutateGraph) return
    const rawId = newSub.id || tempId()
    const id = isUuidLike(rawId) ? rawId : tempId()
    setSubCompetencyNodes(prev => [...prev, {
      id,
      vacancy_id: vacancyId,
      sub_competency_id: id,
      competency_id: competencyId,
      sub_competency_name: newSub.name,
      sub_competency_description: newSub.description || '',
      target_level: normalizeTargetLevel(newSub.target_level),
      weight: normalizeWeight(newSub.weight),
      position: nextPosition(prev, s => s.competency_id === competencyId),
    }])
    markDirty()
  }

  // ===== RENDER =====
  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Загрузка вакансии...</p>
      </div>
    )
  }

  return (
    <div className="workspace">
      <VacancySidebar vacancy={vacancy} />

      <main className="main-content">
        <div className="editor-topbar">
          <button
            className="editor-topbar__back"
            onClick={() => navigate('/')}
          >
            <ArrowLeft size={18} /> К вакансиям
          </button>

          <h2 className="editor-topbar__title">{vacancy?.name}</h2>
          <span
            style={{
              borderRadius: 999,
              border: '1px solid #d1d5db',
              padding: '4px 10px',
              fontSize: 12,
              color: '#374151',
            }}
          >
            Статус: {VACANCY_STATUS_LABELS[vacancy?.status] || vacancy?.status}
          </span>

          <div className="editor-topbar__actions">
            {isDirty && canMutateGraph && (
              <button
                className="btn-secondary"
                onClick={handleDiscard}
                disabled={saving}
              >
                <RotateCcw size={16} /> Отменить
              </button>
            )}
            <button
              className="btn-primary"
              onClick={handleSave}
              disabled={saving || !isDirty || !canMutateGraph}
            >
              {saving
                ? <><Loader2 size={16} className="spin" /> Сохранение...</>
                : <><Save size={16} /> Сохранить</>
              }
            </button>
          </div>
        </div>

        {isForbidden ? (
          <ForbiddenState hint="Недостаточно прав для работы с этой вакансией." />
        ) : (
          <>
            {!isEditableStatus && (
              <div style={{ marginBottom: 12 }}>
                <ForbiddenState
                  title="Редактирование недоступно"
                  hint="Изменения графа доступны только для вакансий в статусах draft и ready."
                />
              </div>
            )}

            {canReviewSuggestions && (
              <SuggestionsPanel
                vacancyId={vacancyId}
                categoryNodes={categoryNodes}
                competencyNodes={competencyNodes}
                onApprove={handleSuggestionsApplied}
                notify={notify}
              />
            )}

            <MindMap
              readOnly={!canMutateGraph}
              categoryNodes={categoryNodes}
              competencyNodes={competencyNodes}
              subCompetencyNodes={subCompetencyNodes}
              onUpdateCategory={handleUpdateCategory}
              onDeleteCategory={handleDeleteCategory}
              onAddCategory={() => setAddingCategory(true)}
              onUpdateCompetency={handleUpdateCompetency}
              onDeleteCompetency={handleDeleteCompetency}
              onAddCompetency={handleAddCompetency}
              onUpdateSub={handleUpdateSub}
              onDeleteSub={handleDeleteSub}
              onAddSub={handleAddSub}
            />
          </>
        )}

        {addingCategory && canMutateGraph && !isForbidden && (
          <EditCategoryDialog
            category={{ id: '', name: '', emoji: '📌', description: '' }}
            onSave={handleAddCategorySubmit}
            onClose={() => setAddingCategory(false)}
            title="➕ Добавить категорию"
          />
        )}
      </main>
    </div>
  )
}
