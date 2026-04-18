import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import {
  createCategory,
  createCompetency,
  createSubCompetency,
  deleteCategory,
  deleteCompetency,
  deleteSubCompetency,
  getCategory,
  getCompetency,
  getSubCompetency,
  listCategories,
  listCompetencies,
  listSubCompetencies,
  updateCategory,
  updateCompetency,
  updateSubCompetency,
} from '../api/ontology'
import { getErrorMessage } from '../api/errors'
import AsyncState from './AsyncState'
import EditCategoryDialog from './EditCategoryDialog'
import AddCompetencyDialog from './AddCompetencyDialog'
import EditCompetencyDialog from './EditCompetencyDialog'
import AddSubDialog from './AddSubDialog'
import NodeEditor from './NodeEditor'
import ConfirmDialog from './ConfirmDialog'
import './OntologyTab.css'

const ENTITY_TYPE = {
  CATEGORY: 'category',
  COMPETENCY: 'competency',
  SUB_COMPETENCY: 'sub_competency',
}

const emptySelection = { type: null, id: null }

function SelectionBadge({ selected }) {
  if (!selected?.type || !selected?.id) return null
  return (
    <span className="ontology__selection-badge">
      {selected.type}: {selected.id}
    </span>
  )
}

export default function OntologyTab({ notify }) {
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [categories, setCategories] = useState([])
  const [competencies, setCompetencies] = useState([])
  const [subCompetencies, setSubCompetencies] = useState([])
  const [selected, setSelected] = useState(emptySelection)
  const [selectedDetails, setSelectedDetails] = useState(null)

  const [expandedCategories, setExpandedCategories] = useState(() => new Set())
  const [expandedCompetencies, setExpandedCompetencies] = useState(() => new Set())

  const [editingCategory, setEditingCategory] = useState(null)
  const [addingCompetencyForCategory, setAddingCompetencyForCategory] = useState(null)
  const [editingCompetency, setEditingCompetency] = useState(null)
  const [addingSubForCompetency, setAddingSubForCompetency] = useState(null)
  const [editingSubCompetency, setEditingSubCompetency] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

  const fetchOntology = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)

    try {
      const [categoriesResponse, competenciesResponse, subCompetenciesResponse] = await Promise.all([
        listCategories(),
        listCompetencies(),
        listSubCompetencies(),
      ])

      const nextCategories = Array.isArray(categoriesResponse.data) ? categoriesResponse.data : []
      const nextCompetencies = Array.isArray(competenciesResponse.data) ? competenciesResponse.data : []
      const nextSubCompetencies = Array.isArray(subCompetenciesResponse.data)
        ? subCompetenciesResponse.data
        : []

      setCategories(nextCategories)
      setCompetencies(nextCompetencies)
      setSubCompetencies(nextSubCompetencies)

      setExpandedCategories(new Set(nextCategories.map((category) => category.id)))
      setExpandedCompetencies(new Set(nextCompetencies.map((competency) => competency.id)))
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки онтологии' }), 'error')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [notify])

  const refreshSelectedDetails = useCallback(async (selection) => {
    if (!selection?.type || !selection?.id) {
      setSelectedDetails(null)
      return
    }

    try {
      if (selection.type === ENTITY_TYPE.CATEGORY) {
        const { data } = await getCategory(selection.id)
        setSelectedDetails(data)
        return
      }
      if (selection.type === ENTITY_TYPE.COMPETENCY) {
        const { data } = await getCompetency(selection.id)
        setSelectedDetails(data)
        return
      }
      const { data } = await getSubCompetency(selection.id)
      setSelectedDetails(data)
    } catch (error) {
      setSelectedDetails(null)
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки деталей' }), 'error')
    }
  }, [notify])

  useEffect(() => {
    fetchOntology()
  }, [fetchOntology])

  useEffect(() => {
    refreshSelectedDetails(selected)
  }, [selected, refreshSelectedDetails])

  const categoryById = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories]
  )
  const competencyById = useMemo(
    () => new Map(competencies.map((competency) => [competency.id, competency])),
    [competencies]
  )

  const handleSelect = (type, id) => {
    setSelected({ type, id })
  }

  const toggleCategory = (categoryId) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(categoryId)) next.delete(categoryId)
      else next.add(categoryId)
      return next
    })
  }

  const toggleCompetency = (competencyId) => {
    setExpandedCompetencies((prev) => {
      const next = new Set(prev)
      if (next.has(competencyId)) next.delete(competencyId)
      else next.add(competencyId)
      return next
    })
  }

  const refreshAndPreserveSelection = async () => {
    await fetchOntology({ silent: true })
    await refreshSelectedDetails(selected)
  }

  const handleCreateCategory = async (payload) => {
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
  }

  const handleUpdateCategory = async (payload) => {
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
  }

  const handleCreateCompetency = async (payload) => {
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
  }

  const handleUpdateCompetency = async (payload) => {
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
  }

  const handleCreateSubCompetency = async (payload) => {
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
  }

  const handleUpdateSubCompetency = async (payload) => {
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
  }

  const handleDeleteEntity = async () => {
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
      if (selected.id === confirmDelete.id) {
        setSelected(emptySelection)
        setSelectedDetails(null)
      }
      setConfirmDelete(null)
      await refreshAndPreserveSelection()
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка удаления' }), 'error')
    }
  }

  const openCreateCategory = () => {
    setEditingCategory({ mode: 'create', payload: { id: '', name: '', emoji: '📋', description: '' } })
  }

  const openEditSelected = () => {
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
  }

  const openCreateForSelection = () => {
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
  }

  const openDeleteSelected = () => {
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
  }

  if (loading) {
    return <AsyncState kind="loading" title="Загрузка онтологии..." />
  }

  return (
    <div className="ontology">
      <div className="ontology__toolbar">
        <div className="ontology__toolbar-left">
          <h2>🧩 Онтология</h2>
          <SelectionBadge selected={selected} />
        </div>
        <div className="ontology__toolbar-actions">
          <button className="btn-secondary" onClick={() => fetchOntology({ silent: true })}>
            <RefreshCw size={16} className={refreshing ? 'spin' : ''} /> Обновить
          </button>
          <button className="btn-primary" onClick={openCreateCategory}>
            <Plus size={16} /> Категория
          </button>
          <button
            className="btn-secondary"
            onClick={openCreateForSelection}
            disabled={selected.type !== ENTITY_TYPE.CATEGORY && selected.type !== ENTITY_TYPE.COMPETENCY}
          >
            <Plus size={16} /> Добавить в выбранное
          </button>
          <button
            className="btn-secondary"
            onClick={openEditSelected}
            disabled={!selected.type}
          >
            <Pencil size={16} /> Изменить
          </button>
          <button
            className="btn-danger"
            onClick={openDeleteSelected}
            disabled={!selected.type}
          >
            <Trash2 size={16} /> Удалить
          </button>
        </div>
      </div>

      <div className="ontology__content">
        <aside className="ontology__tree">
          {categories.length === 0 ? (
            <AsyncState kind="empty" title="Онтология пока пуста" hint="Создайте первую категорию." />
          ) : (
            categories.map((category) => {
              const categoryExpanded = expandedCategories.has(category.id)
              return (
                <div key={category.id} className="ontology__category">
                  <button
                    className={`ontology__node ontology__node--category ${
                      selected.type === ENTITY_TYPE.CATEGORY && selected.id === category.id ? 'is-selected' : ''
                    }`}
                    onClick={() => handleSelect(ENTITY_TYPE.CATEGORY, category.id)}
                  >
                    <span
                      className="ontology__node-expand"
                      onClick={(event) => {
                        event.stopPropagation()
                        toggleCategory(category.id)
                      }}
                    >
                      {categoryExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </span>
                    <span>{category.emoji || '📋'} {category.name}</span>
                  </button>

                  {categoryExpanded && (
                    <div className="ontology__children">
                      {(category.competencies || []).map((competency) => {
                        const competencyExpanded = expandedCompetencies.has(competency.id)
                        return (
                          <div key={competency.id} className="ontology__competency">
                            <button
                              className={`ontology__node ontology__node--competency ${
                                selected.type === ENTITY_TYPE.COMPETENCY && selected.id === competency.id
                                  ? 'is-selected'
                                  : ''
                              }`}
                              onClick={() => handleSelect(ENTITY_TYPE.COMPETENCY, competency.id)}
                            >
                              <span
                                className="ontology__node-expand"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  toggleCompetency(competency.id)
                                }}
                              >
                                {competencyExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                              </span>
                              <span>{competency.name}</span>
                            </button>

                            {competencyExpanded && (
                              <div className="ontology__children ontology__children--sub">
                                {(competency.sub_competencies || []).map((sub) => (
                                  <button
                                    key={sub.id}
                                    className={`ontology__node ontology__node--sub ${
                                      selected.type === ENTITY_TYPE.SUB_COMPETENCY && selected.id === sub.id
                                        ? 'is-selected'
                                        : ''
                                    }`}
                                    onClick={() => handleSelect(ENTITY_TYPE.SUB_COMPETENCY, sub.id)}
                                  >
                                    <span className="ontology__node-dot">•</span>
                                    <span>{sub.name}</span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </aside>

        <section className="ontology__details">
          {!selected.type ? (
            <AsyncState
              kind="empty"
              title="Выберите узел онтологии"
              hint="Слева выберите категорию, компетенцию или подкомпетенцию для просмотра деталей."
            />
          ) : !selectedDetails ? (
            <AsyncState kind="loading" title="Загрузка деталей..." />
          ) : (
            <div className="ontology__details-card">
              <h3>
                {selected.type === ENTITY_TYPE.CATEGORY && 'Категория'}
                {selected.type === ENTITY_TYPE.COMPETENCY && 'Компетенция'}
                {selected.type === ENTITY_TYPE.SUB_COMPETENCY && 'Подкомпетенция'}
              </h3>

              <div className="ontology__details-grid">
                {Object.entries(selectedDetails).map(([key, value]) => (
                  <div key={key} className="ontology__details-item">
                    <span className="ontology__details-key">{key}</span>
                    <pre className="ontology__details-value">
                      {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>

      {editingCategory && (
        <EditCategoryDialog
          category={editingCategory.payload}
          onSave={editingCategory.mode === 'create' ? handleCreateCategory : handleUpdateCategory}
          onClose={() => setEditingCategory(null)}
          title={editingCategory.mode === 'create' ? '➕ Добавить категорию' : '✏️ Редактировать категорию'}
        />
      )}

      {addingCompetencyForCategory && (
        <AddCompetencyDialog
          categoryName={addingCompetencyForCategory.name}
          onAdd={handleCreateCompetency}
          onClose={() => setAddingCompetencyForCategory(null)}
        />
      )}

      {editingCompetency && (
        <EditCompetencyDialog
          competency={editingCompetency}
          onSave={handleUpdateCompetency}
          onClose={() => setEditingCompetency(null)}
        />
      )}

      {addingSubForCompetency && (
        <AddSubDialog
          competencyName={addingSubForCompetency.name}
          onAdd={handleCreateSubCompetency}
          onClose={() => setAddingSubForCompetency(null)}
        />
      )}

      {editingSubCompetency && (
        <NodeEditor
          sub={editingSubCompetency}
          onSave={handleUpdateSubCompetency}
          onClose={() => setEditingSubCompetency(null)}
        />
      )}

      {confirmDelete && (
        <ConfirmDialog
          title={confirmDelete.title}
          message={confirmDelete.message}
          onConfirm={handleDeleteEntity}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  )
}
