import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, RotateCcw, Loader2, CheckCircle2 } from 'lucide-react'
import VacancySidebar from './VacancySidebar'
import MindMap from './MindMap'
import AddCategoryDialog from './AddCategoryDialog'
import SuggestionsPanel from './SuggestionsPanel'
import ForbiddenState from './ForbiddenState'
import AsyncState from './AsyncState'
import { finalizeVacancyGraph, getVacancy, updateGraph } from '../api/vacancies'
import { listCategories } from '../api/ontology'
import { getErrorMessage } from '../api/errors'
import { canEditGraph, canUseSuggestions } from '../api/roles'
import {
  buildVacancyGraphDTO,
  isUuidLike,
  markPersistedGraphNodes,
  nextPosition,
  normalizeTargetLevel,
  normalizeWeight,
} from '../domain/competencyGraph'
import './VacancyEditor.css'

const tempId = () => crypto.randomUUID()
const EDITABLE_STATUSES = new Set(['draft', 'ready'])
const VACANCY_STATUS_LABELS = {
  pending: 'Извлечение компетенций',
  draft: 'Черновик',
  ready: 'Финализировано',
  failed: 'Ошибка обработки',
}

export default function VacancyEditor({ notify, role }) {
  const { vacancyId } = useParams()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [vacancy, setVacancy] = useState(null)
  const [ontologyCategories, setOntologyCategories] = useState([])

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
  const canFinalize = canEdit && vacancy?.status === 'draft' && !isDirty
  const canReviewSuggestions = canUseSuggestions(role) && vacancy?.status === 'draft'

  const ontologyCategoryOptions = useMemo(
    () =>
      ontologyCategories.map((category) => ({
        id: category.id,
        name: category.name,
        emoji: category.emoji || '',
        description: category.description || '',
      })),
    [ontologyCategories]
  )

  const ontologyCompetencyOptions = useMemo(
    () =>
      ontologyCategories.flatMap((category) =>
        (category.competencies || []).map((competency) => ({
          id: competency.id,
          category_id: competency.category_id,
          name: competency.name,
          description: competency.description || '',
        }))
      ),
    [ontologyCategories]
  )

  const ontologySubCompetencyOptions = useMemo(
    () =>
      ontologyCategories.flatMap((category) =>
        (category.competencies || []).flatMap((competency) =>
          (competency.sub_competencies || []).map((sub) => ({
            id: sub.id,
            competency_id: sub.competency_id,
            name: sub.name,
            description: sub.description || '',
            target_level: sub.target_level,
            weight: sub.weight,
          }))
        )
      ),
    [ontologyCategories]
  )

  const applyVacancyData = useCallback((data) => {
    const cats = markPersistedGraphNodes(data.category_nodes || [])
    const comps = markPersistedGraphNodes(data.competency_nodes || [])
    const subs = markPersistedGraphNodes(data.sub_competency_nodes || [])

    setVacancy(data)
    setCategoryNodes(cats)
    setCompetencyNodes(comps)
    setSubCompetencyNodes(subs)
    setOriginalNodes({ cats, comps, subs })
    setIsDirty(false)
  }, [])

  const loadVacancy = useCallback(async () => {
    try {
      const { data } = await getVacancy(vacancyId)
      applyVacancyData(data)
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
  }, [vacancyId, applyVacancyData, notify, navigate])

  useEffect(() => {
    loadVacancy()
  }, [loadVacancy])

  useEffect(() => {
    const loadOntology = async () => {
      try {
        const { data } = await listCategories()
        setOntologyCategories(Array.isArray(data) ? data : [])
      } catch (error) {
        notify(getErrorMessage(error, { fallback: 'Ошибка загрузки онтологии' }), 'error')
      }
    }
    loadOntology()
  }, [notify])

  const handleSave = async () => {
    if (!canMutateGraph) {
      notify('Недостаточно прав для редактирования графа', 'error')
      return
    }
    setSaving(true)
    try {
      const dto = buildVacancyGraphDTO(categoryNodes, competencyNodes, subCompetencyNodes)
      await updateGraph(vacancyId, dto)

      const { data: fresh } = await getVacancy(vacancyId)
      applyVacancyData(fresh)
      notify('Граф компетенций сохранен')
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка сохранения' }), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleFinalize = async () => {
    if (!canFinalize) return
    setFinalizing(true)
    try {
      await finalizeVacancyGraph(vacancyId)
      const { data: fresh } = await getVacancy(vacancyId)
      applyVacancyData(fresh)
      notify('Вакансия переведена в статус ready')
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка финализации графа' }), 'error')
    } finally {
      setFinalizing(false)
    }
  }

  const handleDiscard = () => {
    if (!originalNodes) return
    setCategoryNodes(originalNodes.cats)
    setCompetencyNodes(originalNodes.comps)
    setSubCompetencyNodes(originalNodes.subs)
    setIsDirty(false)
    notify('Изменения отменены')
  }

  const markDirty = () => setIsDirty(true)

  const handleSuggestionsApplied = useCallback(async () => {
    try {
      const { data } = await getVacancy(vacancyId)
      const cats = markPersistedGraphNodes(data.category_nodes || [])
      const comps = markPersistedGraphNodes(data.competency_nodes || [])
      const subs = markPersistedGraphNodes(data.sub_competency_nodes || [])

      await updateGraph(vacancyId, buildVacancyGraphDTO(cats, comps, subs))

      const { data: fresh } = await getVacancy(vacancyId)
      applyVacancyData(fresh)
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка обновления графа' }), 'error')
    }
  }, [vacancyId, applyVacancyData, notify])

  const handleUpdateCategory = (updated) => {
    if (!canMutateGraph) return
    setCategoryNodes((prev) => prev.map((c) => (
      c.category_id === updated.category_id ? { ...c, ...updated } : c
    )))
    markDirty()
  }

  const handleDeleteCategory = (categoryId) => {
    if (!canMutateGraph) return
    const removedCompIds = competencyNodes
      .filter((c) => c.category_id === categoryId)
      .map((c) => c.competency_id)
    setCategoryNodes((prev) => prev.filter((c) => c.category_id !== categoryId))
    setCompetencyNodes((prev) => prev.filter((c) => c.category_id !== categoryId))
    setSubCompetencyNodes((prev) =>
      prev.filter((s) => !removedCompIds.includes(s.competency_id))
    )
    markDirty()
  }

  const handleAddCategorySubmit = (newCat) => {
    if (!canMutateGraph) return
    if (newCat.mode === 'existing') {
      const exists = categoryNodes.some((item) => item.category_id === newCat.id)
      if (exists) {
        notify('Категория уже добавлена в граф', 'error')
        return
      }
      setCategoryNodes((prev) => [...prev, {
        id: tempId(),
        vacancy_id: vacancyId,
        category_id: newCat.id,
        category_name: newCat.name,
        category_emoji: newCat.emoji || '',
        category_description: newCat.description || '',
        position: nextPosition(prev),
        _persisted: true,
      }])
      setAddingCategory(false)
      markDirty()
      return
    }

    const id = tempId()
    setCategoryNodes((prev) => [...prev, {
      id,
      vacancy_id: vacancyId,
      category_id: id,
      category_name: newCat.name,
      category_emoji: newCat.emoji || '',
      category_description: newCat.description || '',
      position: nextPosition(prev),
      _persisted: false,
    }])
    setAddingCategory(false)
    markDirty()
  }

  const handleUpdateCompetency = (updated) => {
    if (!canMutateGraph) return
    setCompetencyNodes((prev) => prev.map((c) => (
      c.competency_id === updated.competency_id ? { ...c, ...updated } : c
    )))
    markDirty()
  }

  const handleDeleteCompetency = (competencyId) => {
    if (!canMutateGraph) return
    setCompetencyNodes((prev) => prev.filter((c) => c.competency_id !== competencyId))
    setSubCompetencyNodes((prev) => prev.filter((s) => s.competency_id !== competencyId))
    markDirty()
  }

  const handleAddCompetency = (categoryId, newComp) => {
    if (!canMutateGraph) return
    if (newComp.mode === 'existing') {
      const exists = competencyNodes.some((item) => item.competency_id === newComp.id)
      if (exists) {
        notify('Компетенция уже добавлена в граф', 'error')
        return
      }
      setCompetencyNodes((prev) => [...prev, {
        id: tempId(),
        vacancy_id: vacancyId,
        competency_id: newComp.id,
        category_id: categoryId,
        competency_name: newComp.name,
        competency_description: newComp.description || '',
        is_required: newComp.is_required ?? true,
        position: nextPosition(prev, (c) => c.category_id === categoryId),
        _persisted: true,
      }])
      markDirty()
      return
    }

    const id = tempId()
    setCompetencyNodes((prev) => [...prev, {
      id,
      vacancy_id: vacancyId,
      competency_id: id,
      category_id: categoryId,
      competency_name: newComp.name,
      competency_description: newComp.description || '',
      is_required: newComp.is_required ?? true,
      position: nextPosition(prev, (c) => c.category_id === categoryId),
      _persisted: false,
    }])
    markDirty()
  }

  const handleUpdateSub = (updatedSub) => {
    if (!canMutateGraph) return
    setSubCompetencyNodes((prev) => prev.map((s) => (
      s.sub_competency_id === updatedSub.sub_competency_id
        ? {
          ...s,
          ...updatedSub,
          target_level: normalizeTargetLevel(updatedSub.target_level),
          weight: normalizeWeight(updatedSub.weight),
        }
        : s
    )))
    markDirty()
  }

  const handleDeleteSub = (subCompetencyId) => {
    if (!canMutateGraph) return
    setSubCompetencyNodes((prev) =>
      prev.filter((s) => s.sub_competency_id !== subCompetencyId)
    )
    markDirty()
  }

  const handleAddSub = (competencyId, newSub) => {
    if (!canMutateGraph) return
    if (newSub.mode === 'existing') {
      const exists = subCompetencyNodes.some((item) => item.sub_competency_id === newSub.id)
      if (exists) {
        notify('Подкомпетенция уже добавлена в граф', 'error')
        return
      }
      setSubCompetencyNodes((prev) => [...prev, {
        id: tempId(),
        vacancy_id: vacancyId,
        sub_competency_id: newSub.id,
        competency_id: competencyId,
        sub_competency_name: newSub.name,
        sub_competency_description: newSub.description || '',
        target_level: normalizeTargetLevel(newSub.target_level),
        weight: normalizeWeight(newSub.weight),
        position: nextPosition(prev, (s) => s.competency_id === competencyId),
        _persisted: true,
      }])
      markDirty()
      return
    }

    const rawId = newSub.id || tempId()
    const id = isUuidLike(rawId) ? rawId : tempId()
    setSubCompetencyNodes((prev) => [...prev, {
      id,
      vacancy_id: vacancyId,
      sub_competency_id: id,
      competency_id: competencyId,
      sub_competency_name: newSub.name,
      sub_competency_description: newSub.description || '',
      target_level: normalizeTargetLevel(newSub.target_level),
      weight: normalizeWeight(newSub.weight),
      position: nextPosition(prev, (s) => s.competency_id === competencyId),
      _persisted: false,
    }])
    markDirty()
  }

  if (loading) {
    return <AsyncState kind="loading" title="Загрузка вакансии..." />
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
          <span className="editor-topbar__status">
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
            <button
              className="btn-secondary"
              onClick={handleFinalize}
              disabled={!canFinalize || finalizing}
              title={isDirty ? 'Сначала сохраните изменения графа' : 'Перевести в статус ready'}
            >
              {finalizing
                ? <><Loader2 size={16} className="spin" /> Финализация...</>
                : <><CheckCircle2 size={16} /> Finalize</>
              }
            </button>
          </div>
        </div>

        {isForbidden ? (
          <ForbiddenState hint="Недостаточно прав для работы с этой вакансией." />
        ) : (
          <>
            {!isEditableStatus && (
              <div className="editor-readonly-banner">
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
              ontologyCompetencyOptions={ontologyCompetencyOptions}
              ontologySubCompetencyOptions={ontologySubCompetencyOptions}
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
          <AddCategoryDialog
            existingOptions={ontologyCategoryOptions}
            onAdd={handleAddCategorySubmit}
            onClose={() => setAddingCategory(false)}
          />
        )}
      </main>
    </div>
  )
}
