import { useCallback, useState } from 'react'
import {
  createCategory,
  createCompetency,
  createSubCompetency,
  deleteCategory,
  deleteCompetency,
  deleteSubCompetency,
  updateCategory,
  updateCompetency,
  updateSubCompetency,
} from '../api/ontology'
import { getErrorMessage } from '../api/errors'
import { ENTITY_TYPE } from './useOntologyData'

export function useOntologyCrud({
  notify,
  selected,
  categoryById,
  competencyById,
  subCompetencies,
  refreshAndPreserveSelection,
  resetSelection,
}) {
  const [editingCategory, setEditingCategory] = useState(null)
  const [addingCompetencyForCategory, setAddingCompetencyForCategory] = useState(null)
  const [editingCompetency, setEditingCompetency] = useState(null)
  const [addingSubForCompetency, setAddingSubForCompetency] = useState(null)
  const [editingSubCompetency, setEditingSubCompetency] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

  const handleCreateCategory = useCallback(async (payload) => {
    try {
      await createCategory({
        name: payload.name,
        description: payload.description || '',
        emoji: payload.emoji || '📋',
      })
      notify('Категория создана')
      setEditingCategory(null)
      await refreshAndPreserveSelection()
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка создания категории' }), 'error')
    }
  }, [notify, refreshAndPreserveSelection])

  const handleUpdateCategory = useCallback(async (payload) => {
    try {
      await updateCategory(payload.id, {
        name: payload.name,
        description: payload.description || '',
        emoji: payload.emoji || '📋',
      })
      notify('Категория обновлена')
      setEditingCategory(null)
      await refreshAndPreserveSelection()
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка обновления категории' }), 'error')
    }
  }, [notify, refreshAndPreserveSelection])

  const handleCreateCompetency = useCallback(async (payload) => {
    if (!addingCompetencyForCategory?.id) return

    try {
      await createCompetency({
        category_id: addingCompetencyForCategory.id,
        name: payload.name,
        description: payload.description || '',
      })
      notify('Компетенция создана')
      setAddingCompetencyForCategory(null)
      await refreshAndPreserveSelection()
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка создания компетенции' }), 'error')
    }
  }, [addingCompetencyForCategory, notify, refreshAndPreserveSelection])

  const handleUpdateCompetency = useCallback(async (payload) => {
    try {
      await updateCompetency(payload.id, {
        name: payload.competency_name,
        description: payload.competency_description || '',
      })
      notify('Компетенция обновлена')
      setEditingCompetency(null)
      await refreshAndPreserveSelection()
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка обновления компетенции' }), 'error')
    }
  }, [notify, refreshAndPreserveSelection])

  const handleCreateSubCompetency = useCallback(async (payload) => {
    if (!addingSubForCompetency?.id) return

    try {
      await createSubCompetency({
        competency_id: addingSubForCompetency.id,
        name: payload.name,
        description: payload.description || '',
        target_level: payload.target_level,
        weight: payload.weight,
      })
      notify('Подкомпетенция создана')
      setAddingSubForCompetency(null)
      await refreshAndPreserveSelection()
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка создания подкомпетенции' }), 'error')
    }
  }, [addingSubForCompetency, notify, refreshAndPreserveSelection])

  const handleUpdateSubCompetency = useCallback(async (payload) => {
    try {
      await updateSubCompetency(payload.id, {
        name: payload.sub_competency_name,
        description: payload.sub_competency_description || '',
        target_level: payload.target_level,
        weight: payload.weight,
      })
      notify('Подкомпетенция обновлена')
      setEditingSubCompetency(null)
      await refreshAndPreserveSelection()
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка обновления подкомпетенции' }), 'error')
    }
  }, [notify, refreshAndPreserveSelection])

  const handleDeleteEntity = useCallback(async () => {
    if (!confirmDelete) return

    try {
      if (confirmDelete.type === ENTITY_TYPE.CATEGORY) {
        await deleteCategory(confirmDelete.id)
      } else if (confirmDelete.type === ENTITY_TYPE.COMPETENCY) {
        await deleteCompetency(confirmDelete.id)
      } else {
        await deleteSubCompetency(confirmDelete.id)
      }

      notify('Удаление выполнено')
      if (selected.id === confirmDelete.id) resetSelection()
      setConfirmDelete(null)
      await refreshAndPreserveSelection()
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка удаления' }), 'error')
    }
  }, [confirmDelete, notify, refreshAndPreserveSelection, resetSelection, selected.id])

  const openCreateCategory = useCallback(() => {
    setEditingCategory({ mode: 'create', payload: { id: '', name: '', emoji: '📋', description: '' } })
  }, [])

  const openEditSelected = useCallback(() => {
    if (!selected.type || !selected.id) return

    if (selected.type === ENTITY_TYPE.CATEGORY) {
      const category = categoryById.get(selected.id)
      if (!category) return

      setEditingCategory({
        mode: 'edit',
        payload: {
          id: category.id,
          name: category.name,
          emoji: category.emoji || '📋',
          description: category.description || '',
        },
      })
      return
    }

    if (selected.type === ENTITY_TYPE.COMPETENCY) {
      const competency = competencyById.get(selected.id)
      if (!competency) return

      setEditingCompetency({
        id: competency.id,
        competency_name: competency.name,
        competency_description: competency.description || '',
        is_required: true,
      })
      return
    }

    const sub = subCompetencies.find((item) => item.id === selected.id)
    if (!sub) return

    setEditingSubCompetency({
      id: sub.id,
      sub_competency_name: sub.name,
      sub_competency_description: sub.description || '',
      target_level: sub.target_level,
      weight: sub.weight,
    })
  }, [categoryById, competencyById, selected.id, selected.type, subCompetencies])

  const openCreateForSelection = useCallback(() => {
    if (!selected.type || !selected.id) return

    if (selected.type === ENTITY_TYPE.CATEGORY) {
      const category = categoryById.get(selected.id)
      if (category) setAddingCompetencyForCategory(category)
      return
    }

    if (selected.type === ENTITY_TYPE.COMPETENCY) {
      const competency = competencyById.get(selected.id)
      if (competency) setAddingSubForCompetency(competency)
    }
  }, [categoryById, competencyById, selected.id, selected.type])

  const openDeleteSelected = useCallback(() => {
    if (!selected.type || !selected.id) return

    const label = selected.type === ENTITY_TYPE.CATEGORY
      ? categoryById.get(selected.id)?.name
      : selected.type === ENTITY_TYPE.COMPETENCY
        ? competencyById.get(selected.id)?.name
        : subCompetencies.find((item) => item.id === selected.id)?.name

    setConfirmDelete({
      type: selected.type,
      id: selected.id,
      title: selected.type === ENTITY_TYPE.CATEGORY
        ? 'Удаление категории'
        : selected.type === ENTITY_TYPE.COMPETENCY
          ? 'Удаление компетенции'
          : 'Удаление подкомпетенции',
      message: label
        ? `Удалить "${label}"? Это действие нельзя отменить.`
        : 'Удалить выбранную сущность? Это действие нельзя отменить.',
    })
  }, [categoryById, competencyById, selected.id, selected.type, subCompetencies])

  return {
    editingCategory,
    addingCompetencyForCategory,
    editingCompetency,
    addingSubForCompetency,
    editingSubCompetency,
    confirmDelete,
    setEditingCategory,
    setAddingCompetencyForCategory,
    setEditingCompetency,
    setAddingSubForCompetency,
    setEditingSubCompetency,
    setConfirmDelete,
    handleCreateCategory,
    handleUpdateCategory,
    handleCreateCompetency,
    handleUpdateCompetency,
    handleCreateSubCompetency,
    handleUpdateSubCompetency,
    handleDeleteEntity,
    openCreateCategory,
    openEditSelected,
    openCreateForSelection,
    openDeleteSelected,
  }
}
