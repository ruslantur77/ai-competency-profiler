// frontend/src/components/VacancyEditor.jsx
import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, RotateCcw, Loader2 } from 'lucide-react'
import VacancySidebar from './VacancySidebar'
import MindMap from './MindMap'
import EditCategoryDialog from './EditCategoryDialog'
import { getVacancy, updateGraph } from '../api/client'
import './VacancyEditor.css'

// ===== HELPERS =====

// Генерация временного ID для новых узлов (до сохранения)
const tempId = () => crypto.randomUUID()

// Собираем VacancyGraphUpdateDTO из локального состояния
const buildGraphDTO = (categoryNodes, competencyNodes, subCompetencyNodes) => ({
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
})

export default function VacancyEditor({ notify, onLogout }) {
  const { vacancyId } = useParams()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [vacancy, setVacancy] = useState(null)

  // Три плоских массива — локальное состояние графа
  const [categoryNodes, setCategoryNodes] = useState([])
  const [competencyNodes, setCompetencyNodes] = useState([])
  const [subCompetencyNodes, setSubCompetencyNodes] = useState([])

  // Оригинальное состояние для кнопки "Отмена"
  const [originalNodes, setOriginalNodes] = useState(null)

  const [isDirty, setIsDirty] = useState(false)

  // Для диалога добавления категории
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
      const dto = buildGraphDTO(categoryNodes, competencyNodes, subCompetencyNodes)
      const { data } = await updateGraph(vacancyId, dto)
      // Обновляем состояние из ответа бека
      const cats = data.category_nodes || []
      const comps = data.competency_nodes || []
      const subs = data.sub_competency_nodes || []
      setCategoryNodes(cats)
      setCompetencyNodes(comps)
      setSubCompetencyNodes(subs)
      setOriginalNodes({ cats, comps, subs })
      setIsDirty(false)
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
    setIsDirty(false)
    notify('↩️ Изменения отменены')
  }

  // Помечаем граф как изменённый
  const markDirty = () => setIsDirty(true)

  // ===== КАТЕГОРИИ =====
  const handleUpdateCategory = (updated) => {
    setCategoryNodes(prev => prev.map(c =>
      c.category_id === updated.category_id ? { ...c, ...updated } : c
    ))
    markDirty()
  }

  const handleDeleteCategory = (categoryId) => {
    setCategoryNodes(prev => prev.filter(c => c.category_id !== categoryId))
    // Удаляем все компетенции и подкомпетенции этой категории
    const removedCompIds = competencyNodes
      .filter(c => c.category_id === categoryId)
      .map(c => c.competency_id)
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