// frontend/src/components/VacancyEditor.jsx
import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import VacancySidebar from './VacancySidebar'
import MindMap from './MindMap'
import {
  getVacancy, getGraph,
  updateSubCompetency, deleteSubCompetency, addSubCompetency, aiFixCompetency,
  updateCategory, deleteCategory, addCategory, aiFixCategory,
  updateCompetency, deleteCompetency, addCompetency, aiFixCompetencyFull,
} from '../api/client'
import './VacancyEditor.css'

export default function VacancyEditor({ notify }) {
  const { vacancyId } = useParams()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [vacancy, setVacancy] = useState(null)
  const [categories, setCategories] = useState([])
  const [competencies, setCompetencies] = useState([])

  useEffect(() => {
    const load = async () => {
      try {
        const [vacRes, graphRes] = await Promise.all([
          getVacancy(vacancyId),
          getGraph(vacancyId),
        ])
        setVacancy(vacRes.data)
        setCategories(graphRes.data.categories)
        setCompetencies(graphRes.data.competencies)
      } catch (err) {
        notify('Ошибка загрузки вакансии', 'error')
        navigate('/')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [vacancyId])

  // ===== ПОДКОМПЕТЕНЦИИ =====
  const handleUpdateSub = async (competencyId, updatedSub) => {
    try {
      await updateSubCompetency(vacancyId, {
        competency_id: competencyId, sub_competency_id: updatedSub.id,
        name: updatedSub.name, level: updatedSub.level,
        description: updatedSub.description, sub_skills: updatedSub.sub_skills,
      })
      setCompetencies(prev => prev.map(comp => {
        if (comp.id !== competencyId) return comp
        return { ...comp, sub_competencies: comp.sub_competencies.map(s => s.id === updatedSub.id ? updatedSub : s) }
      }))
      notify(`✏️ "${updatedSub.name}" обновлена`)
    } catch { notify('Ошибка обновления', 'error') }
  }

  const handleDeleteSub = async (subId, competencyId) => {
    try {
      await deleteSubCompetency(vacancyId, { competency_id: competencyId, sub_competency_id: subId })
      setCompetencies(prev => prev.map(comp => {
        if (comp.id !== competencyId) return comp
        return { ...comp, sub_competencies: comp.sub_competencies.filter(s => s.id !== subId) }
      }))
      notify('🗑️ Подкомпетенция удалена')
    } catch { notify('Ошибка удаления', 'error') }
  }

  const handleAddSub = async (competencyId, newSub) => {
    try {
      const { data } = await addSubCompetency(vacancyId, { competency_id: competencyId, ...newSub })
      setCompetencies(prev => prev.map(comp => {
        if (comp.id !== competencyId) return comp
        return { ...comp, sub_competencies: [...comp.sub_competencies, data.created] }
      }))
      notify(`➕ "${newSub.name}" добавлена`)
    } catch { notify('Ошибка добавления', 'error') }
  }

  const handleAiFix = async (competencyId, subId, instruction) => {
    try {
      const { data } = await aiFixCompetency(vacancyId, { competency_id: competencyId, sub_competency_id: subId, instruction })
      notify(`🤖 ${data.message}`)
    } catch { notify('Ошибка AI', 'error') }
  }

  // ===== КАТЕГОРИИ =====
  const handleUpdateCategory = async (updated) => {
    try {
      await updateCategory(vacancyId, { category_id: updated.id, name: updated.name, emoji: updated.emoji, description: updated.description })
      setCategories(prev => prev.map(c => c.id === updated.id ? updated : c))
      notify(`✏️ Категория "${updated.name}" обновлена`)
    } catch { notify('Ошибка', 'error') }
  }

  const handleDeleteCategory = async (categoryId) => {
    try {
      await deleteCategory(vacancyId, { category_id: categoryId })
      setCategories(prev => prev.filter(c => c.id !== categoryId))
      setCompetencies(prev => prev.filter(c => c.category_id !== categoryId))
      notify('🗑️ Категория удалена')
    } catch { notify('Ошибка', 'error') }
  }

  const handleAiFixCategory = async (categoryId, instruction) => {
    try {
      const { data } = await aiFixCategory(vacancyId, { category_id: categoryId, instruction })
      notify(`🤖 ${data.message}`)
    } catch { notify('Ошибка AI', 'error') }
  }

  const handleAddCategory = async () => {
    const name = prompt('Название новой категории:')
    if (!name) return
    try {
      const { data } = await addCategory(vacancyId, { name, emoji: '📌', description: '' })
      setCategories(prev => [...prev, data.created])
      notify(`➕ Категория "${name}" добавлена`)
    } catch { notify('Ошибка', 'error') }
  }

  // ===== КОМПЕТЕНЦИИ =====
  const handleUpdateCompetency = async (updated) => {
    try {
      await updateCompetency(vacancyId, { competency_id: updated.id, skill: updated.skill })
      setCompetencies(prev => prev.map(c => c.id === updated.id ? { ...c, skill: updated.skill } : c))
      notify('✏️ Компетенция обновлена')
    } catch { notify('Ошибка', 'error') }
  }

  const handleDeleteCompetency = async (competencyId) => {
    try {
      await deleteCompetency(vacancyId, { competency_id: competencyId })
      setCompetencies(prev => prev.filter(c => c.id !== competencyId))
      notify('🗑️ Компетенция удалена')
    } catch { notify('Ошибка', 'error') }
  }

  const handleAddCompetency = async (categoryId, skill) => {
    try {
      const { data } = await addCompetency(vacancyId, { category_id: categoryId, skill })
      setCompetencies(prev => [...prev, data.created])
      notify(`➕ "${skill}" добавлена`)
    } catch { notify('Ошибка', 'error') }
  }

  const handleAiFixCompetency = async (competencyId, instruction) => {
    try {
      const { data } = await aiFixCompetencyFull(vacancyId, { competency_id: competencyId, instruction })
      notify(`🤖 ${data.message}`)
    } catch { notify('Ошибка AI', 'error') }
  }

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
          <button className="editor-topbar__back" onClick={() => navigate('/')}>
            <ArrowLeft size={18} /> К вакансиям
          </button>
          <h2 className="editor-topbar__title">{vacancy?.name}</h2>
        </div>

        <MindMap
          categories={categories}
          competencies={competencies}
          onUpdateSub={handleUpdateSub}
          onDeleteSub={handleDeleteSub}
          onAddSub={handleAddSub}
          onAiFix={handleAiFix}
          onUpdateCategory={handleUpdateCategory}
          onDeleteCategory={handleDeleteCategory}
          onAiFixCategory={handleAiFixCategory}
          onAddCategory={handleAddCategory}
          onUpdateCompetency={handleUpdateCompetency}
          onDeleteCompetency={handleDeleteCompetency}
          onAddCompetency={handleAddCompetency}
          onAiFixCompetency={handleAiFixCompetency}
        />
      </main>
    </div>
  )
}