// frontend/src/components/VacancyEditor.jsx
import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, RotateCcw, Loader2 } from 'lucide-react'
import VacancySidebar from './VacancySidebar'
import MindMap from './MindMap'
import EditCategoryDialog from './EditCategoryDialog'
import SuggestionsPanel from './SuggestionsPanel'
import { getVacancy, updateGraph } from '../api/client'
import './VacancyEditor.css'

// ===== HELPERS =====
const tempId = () => crypto.randomUUID()

const buildGraphDTO = (categoryNodes, competencyNodes, subCompetencyNodes, suggestionDecisions = []) => ({
  categories: categoryNodes.map(cat => ({
    id: cat.category_id,
    name: cat.category_name,
    description: cat.category_description || '',
    emoji: cat.category_emoji || '',
    competencies: competencyNodes
      .filter(comp => comp.category_id === cat.category_id)
      .map(comp => ({
        id: comp.competency_id,
        category_id: cat.category_id,
        name: comp.competency_name,
        description: comp.competency_description || '',
        is_required: comp.is_required ?? true,
        sub_competencies: subCompetencyNodes
          .filter(sub => sub.competency_id === comp.competency_id)
          .map(sub => ({
            id: sub.sub_competency_id,
            name: sub.sub_competency_name,
            description: sub.sub_competency_description || '',
            target_level: sub.target_level ?? 2,
            weight: sub.weight ?? 1.0,
          })),
      })),
  })),
  suggestion_decisions: suggestionDecisions,
})

export default function VacancyEditor({ notify, onLogout }) {
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
  const [suggestionDecisions, setSuggestionDecisions] = useState([])
  const [addingCategory, setAddingCategory] = useState(false)

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
      setSuggestionDecisions([])
    } catch (err) {
      notify('Ошибка загрузки вакансии', 'error')
      navigate('/')
    } finally {
      setLoading(false)
    }
  }, [vacancyId, notify, navigate])

  useEffect(() => {
    loadVacancy()
  }, [loadVacancy])

  // ===== СОХРАНЕНИЕ =====
  const handleSave = async () => {
    setSaving(true)
    try {
      const dto = buildGraphDTO(
        categoryNodes,
        competencyNodes,
        subCompetencyNodes,
        suggestionDecisions
      )
      const { data } = await updateGraph(vacancyId, dto)
      const cats = data.category_nodes || []
      const comps = data.competency_nodes || []
      const subs = data.sub_competency_nodes || []
      setCategoryNodes(cats)
      setCompetencyNodes(comps)
      setSubCompetencyNodes(subs)
      setOriginalNodes({ cats, comps, subs })
      setSuggestionDecisions([])
      setIsDirty(false)
      await loadVacancy()
      notify('✅ Граф компетенций сохранён')
    } catch (err) {
      notify('Ошибка сохранения', 'error')
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
    setSuggestionDecisions([])
    setIsDirty(false)
    notify('↩️ Изменения отменены')
  }

  const markDirty = () => setIsDirty(true)

  // ===== SUGGESTIONS → ГРАФ =====
  const handleApproveSuggestion = useCallback((suggestion) => {
    const id = tempId()

    if (suggestion.stage === 'category') {
      setCategoryNodes(prev => {
        if (prev.find(c => c.category_name === suggestion.name)) return prev
        return [...prev, {
          id,
          vacancy_id: vacancyId,
          category_id: id,
          category_name: suggestion.name,
          category_emoji: suggestion.parent_category_emoji || '',
          category_description: suggestion.description || '',
          position: prev.length,
        }]
      })

    } else if (suggestion.stage === 'competency') {
      const parentCatId = suggestion.parent_category_id
      const parentCatName = suggestion.parent_category_name || 'Категория'
      const parentCatEmoji = suggestion.parent_category_emoji || ''

      // Гарантируем что категория есть в графе
      setCategoryNodes(prev => {
        if (prev.find(c => c.category_id === parentCatId)) return prev
        return [...prev, {
          id: parentCatId,
          vacancy_id: vacancyId,
          category_id: parentCatId,
          category_name: parentCatName,
          category_emoji: parentCatEmoji,
          category_description: '',
          position: prev.length,
        }]
      })

      // Добавляем компетенцию
      setCompetencyNodes(prev => {
        if (prev.find(c =>
          c.competency_name === suggestion.name &&
          c.category_id === parentCatId
        )) return prev
        return [...prev, {
          id,
          vacancy_id: vacancyId,
          competency_id: id,
          category_id: parentCatId,
          competency_name: suggestion.name,
          competency_description: suggestion.description || '',
          is_required: suggestion.is_required ?? true,
          position: prev.filter(c => c.category_id === parentCatId).length,
        }]
      })

    } else if (suggestion.stage === 'sub_competency') {
      const parentCompId = suggestion.parent_competency_id
      const parentCatId = suggestion.parent_category_id
      const parentCatName = suggestion.parent_category_name || 'Категория'
      const parentCatEmoji = suggestion.parent_category_emoji || ''
      const parentCompName = suggestion.parent_competency_name || 'Компетенция'

      // Гарантируем что категория есть
      if (parentCatId) {
        setCategoryNodes(prev => {
          if (prev.find(c => c.category_id === parentCatId)) return prev
          return [...prev, {
            id: parentCatId,
            vacancy_id: vacancyId,
            category_id: parentCatId,
            category_name: parentCatName,
            category_emoji: parentCatEmoji,
            category_description: '',
            position: prev.length,
          }]
        })
      }

      // Гарантируем что компетенция есть
      if (parentCompId) {
        setCompetencyNodes(prev => {
          if (prev.find(c => c.competency_id === parentCompId)) return prev
          return [...prev, {
            id: parentCompId,
            vacancy_id: vacancyId,
            competency_id: parentCompId,
            category_id: parentCatId,
            competency_name: parentCompName,
            competency_description: '',
            is_required: true,
            position: prev.filter(c => c.category_id === parentCatId).length,
          }]
        })
      }

      // Добавляем подкомпетенцию
      if (parentCompId) {
        setSubCompetencyNodes(prev => {
          if (prev.find(s =>
            s.sub_competency_name === suggestion.name &&
            s.competency_id === parentCompId
          )) return prev
          return [...prev, {
            id,
            vacancy_id: vacancyId,
            sub_competency_id: id,
            competency_id: parentCompId,
            sub_competency_name: suggestion.name,
            sub_competency_description: suggestion.description || '',
            target_level: suggestion.target_level ?? 2,
            weight: suggestion.weight ?? 1.0,
            position: prev.filter(s => s.competency_id === parentCompId).length,
          }]
        })
      }
    }

    markDirty()
  }, [vacancyId])

  const handleRejectSuggestion = useCallback((suggestion) => {
    if (suggestion.stage === 'category') {
      setCategoryNodes(prev =>
        prev.filter(c => c.category_name !== suggestion.name)
      )
    } else if (suggestion.stage === 'competency') {
      setCompetencyNodes(prev =>
        prev.filter(c => c.competency_name !== suggestion.name)
      )
    } else if (suggestion.stage === 'sub_competency') {
      setSubCompetencyNodes(prev =>
        prev.filter(s => s.sub_competency_name !== suggestion.name)
      )
    }
    markDirty()
  }, [])

  // ===== КАТЕГОРИИ =====
  const handleUpdateCategory = (updated) => {
    setCategoryNodes(prev => prev.map(c =>
      c.category_id === updated.category_id ? { ...c, ...updated } : c
    ))
    markDirty()
  }

  const handleDeleteCategory = (categoryId) => {
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
    const id = tempId()
    setCategoryNodes(prev => [...prev, {
      id,
      vacancy_id: vacancyId,
      category_id: id,
      category_name: newCat.name,
      category_emoji: newCat.emoji || '',
      category_description: newCat.description || '',
      position: prev.length,
    }])
    setAddingCategory(false)
    markDirty()
  }

  // ===== КОМПЕТЕНЦИИ =====
  const handleUpdateCompetency = (updated) => {
    setCompetencyNodes(prev => prev.map(c =>
      c.competency_id === updated.competency_id ? { ...c, ...updated } : c
    ))
    markDirty()
  }

  const handleDeleteCompetency = (competencyId) => {
    setCompetencyNodes(prev => prev.filter(c => c.competency_id !== competencyId))
    setSubCompetencyNodes(prev => prev.filter(s => s.competency_id !== competencyId))
    markDirty()
  }

  const handleAddCompetency = (categoryId, newComp) => {
    const id = tempId()
    setCompetencyNodes(prev => [...prev, {
      id,
      vacancy_id: vacancyId,
      competency_id: id,
      category_id: categoryId,
      competency_name: newComp.name,
      competency_description: newComp.description || '',
      is_required: newComp.is_required ?? true,
      position: prev.filter(c => c.category_id === categoryId).length,
    }])
    markDirty()
  }

  // ===== ПОДКОМПЕТЕНЦИИ =====
  const handleUpdateSub = (updatedSub) => {
    setSubCompetencyNodes(prev => prev.map(s =>
      s.sub_competency_id === updatedSub.sub_competency_id ? { ...s, ...updatedSub } : s
    ))
    markDirty()
  }

  const handleDeleteSub = (subCompetencyId) => {
    setSubCompetencyNodes(prev =>
      prev.filter(s => s.sub_competency_id !== subCompetencyId)
    )
    markDirty()
  }

  const handleAddSub = (competencyId, newSub) => {
    const id = tempId()
    setSubCompetencyNodes(prev => [...prev, {
      id,
      vacancy_id: vacancyId,
      sub_competency_id: id,
      competency_id: competencyId,
      sub_competency_name: newSub.name,
      sub_competency_description: newSub.description || '',
      target_level: newSub.target_level ?? 2,
      weight: newSub.weight ?? 1.0,
      position: prev.filter(s => s.competency_id === competencyId).length,
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

          <div className="editor-topbar__actions">
            {isDirty && (
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
              disabled={saving || !isDirty}
            >
              {saving
                ? <><Loader2 size={16} className="spin" /> Сохранение...</>
                : <><Save size={16} /> Сохранить</>
              }
            </button>
          </div>
        </div>

        {vacancy?.status === 'draft' && (
          <SuggestionsPanel
            vacancyId={vacancyId}
            onApprove={handleApproveSuggestion}
            onReject={handleRejectSuggestion}
            onDecisionsChange={(decisions) => {
              setSuggestionDecisions(decisions)
              if (decisions.length > 0) setIsDirty(true)
            }}
            notify={notify}
          />
        )}

        <MindMap
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

        {addingCategory && (
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