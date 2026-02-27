// frontend/src/App.jsx
import React, { useState, useCallback } from 'react'
import VacancyInput from './components/VacancyInput'
import VacancySidebar from './components/VacancySidebar'
import MindMap from './components/MindMap'
import Notification from './components/Notification'
import AddSubDialog from './components/AddSubDialog'
import {
  parseVacancy, getGraph,
  updateSubCompetency, deleteSubCompetency, addSubCompetency, aiFixCompetency,
  updateCategory, deleteCategory, addCategory, aiFixCategory,
  updateCompetency, deleteCompetency, addCompetency, aiFixCompetencyFull,
} from './api/client'
import './App.css'

export default function App() {
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [vacancy, setVacancy] = useState(null)
  const [categories, setCategories] = useState([])
  const [competencies, setCompetencies] = useState([])
  const [notification, setNotification] = useState(null)
  const [addingCategory, setAddingCategory] = useState(false)

  const notify = useCallback((message, type = 'success') => {
    setNotification({ message, type })
  }, [])

  // ===== ПАРСИНГ ВАКАНСИИ =====
  const handleSubmit = async (url) => {
    setLoading(true)
    try {
      const { data: vacData } = await parseVacancy(url)
      setVacancy(vacData)
      setSessionId(vacData.session_id)

      const { data: graphData } = await getGraph(vacData.session_id)
      setCategories(graphData.categories)
      setCompetencies(graphData.competencies)

      notify('Вакансия проанализирована! Профиль компетенций готов.')
    } catch (err) {
      notify('Ошибка: ' + (err.response?.data?.detail || err.message), 'error')
    } finally {
      setLoading(false)
    }
  }

  // ===== ПОДКОМПЕТЕНЦИИ =====
  const handleUpdateSub = async (competencyId, updatedSub) => {
    try {
      await updateSubCompetency(sessionId, {
        competency_id: competencyId,
        sub_competency_id: updatedSub.id,
        name: updatedSub.name,
        level: updatedSub.level,
        description: updatedSub.description,
        sub_skills: updatedSub.sub_skills,
      })
      setCompetencies(prev => prev.map(comp => {
        if (comp.id !== competencyId) return comp
        return { ...comp, sub_competencies: comp.sub_competencies.map(sub => sub.id === updatedSub.id ? updatedSub : sub) }
      }))
      notify(`✏️ "${updatedSub.name}" обновлена`)
    } catch (err) { notify('Ошибка обновления', 'error') }
  }

  const handleDeleteSub = async (subId, competencyId) => {
    try {
      await deleteSubCompetency(sessionId, { competency_id: competencyId, sub_competency_id: subId })
      setCompetencies(prev => prev.map(comp => {
        if (comp.id !== competencyId) return comp
        return { ...comp, sub_competencies: comp.sub_competencies.filter(s => s.id !== subId) }
      }))
      notify('🗑️ Подкомпетенция удалена')
    } catch (err) { notify('Ошибка удаления', 'error') }
  }

  const handleAddSub = async (competencyId, newSub) => {
    try {
      const { data } = await addSubCompetency(sessionId, { competency_id: competencyId, ...newSub })
      setCompetencies(prev => prev.map(comp => {
        if (comp.id !== competencyId) return comp
        return { ...comp, sub_competencies: [...comp.sub_competencies, data.created] }
      }))
      notify(`➕ "${newSub.name}" добавлена`)
    } catch (err) { notify('Ошибка добавления', 'error') }
  }

  const handleAiFix = async (competencyId, subId, instruction) => {
    try {
      const { data } = await aiFixCompetency(sessionId, { competency_id: competencyId, sub_competency_id: subId, instruction })
      notify(`🤖 ${data.message}`)
    } catch (err) { notify('Ошибка AI', 'error') }
  }

  // ===== КАТЕГОРИИ =====
  const handleUpdateCategory = async (updated) => {
    try {
      await updateCategory(sessionId, { category_id: updated.id, name: updated.name, emoji: updated.emoji, description: updated.description })
      setCategories(prev => prev.map(cat => cat.id === updated.id ? updated : cat))
      notify(`✏️ Категория "${updated.name}" обновлена`)
    } catch (err) { notify('Ошибка обновления категории', 'error') }
  }

  const handleDeleteCategory = async (categoryId) => {
    try {
      await deleteCategory(sessionId, { category_id: categoryId })
      setCategories(prev => prev.filter(cat => cat.id !== categoryId))
      setCompetencies(prev => prev.filter(comp => comp.category_id !== categoryId))
      notify('🗑️ Категория удалена')
    } catch (err) { notify('Ошибка удаления категории', 'error') }
  }

  const handleAiFixCategory = async (categoryId, instruction) => {
    try {
      const { data } = await aiFixCategory(sessionId, { category_id: categoryId, instruction })
      notify(`🤖 ${data.message}`)
    } catch (err) { notify('Ошибка AI', 'error') }
  }

  const handleAddCategory = () => {
    setAddingCategory(true)
  }

  const handleAddCategorySubmit = async (newCat) => {
    try {
      const { data } = await addCategory(sessionId, newCat)
      setCategories(prev => [...prev, data.created])
      setAddingCategory(false)
      notify(`➕ Категория "${newCat.name}" добавлена`)
    } catch (err) { notify('Ошибка добавления категории', 'error') }
  }

  // ===== КОМПЕТЕНЦИИ =====
  const handleUpdateCompetency = async (updated) => {
    try {
      await updateCompetency(sessionId, { competency_id: updated.id, skill: updated.skill })
      setCompetencies(prev => prev.map(comp => comp.id === updated.id ? { ...comp, skill: updated.skill } : comp))
      notify(`✏️ Компетенция обновлена`)
    } catch (err) { notify('Ошибка обновления компетенции', 'error') }
  }

  const handleDeleteCompetency = async (competencyId) => {
    try {
      await deleteCompetency(sessionId, { competency_id: competencyId })
      setCompetencies(prev => prev.filter(comp => comp.id !== competencyId))
      notify('🗑️ Компетенция удалена')
    } catch (err) { notify('Ошибка удаления компетенции', 'error') }
  }

  const handleAddCompetency = async (categoryId, skill) => {
    try {
      const { data } = await addCompetency(sessionId, { category_id: categoryId, skill })
      setCompetencies(prev => [...prev, data.created])
      notify(`➕ Компетенция "${skill}" добавлена`)
    } catch (err) { notify('Ошибка добавления компетенции', 'error') }
  }

  const handleAiFixCompetency = async (competencyId, instruction) => {
    try {
      const { data } = await aiFixCompetencyFull(sessionId, { competency_id: competencyId, instruction })
      notify(`🤖 ${data.message}`)
    } catch (err) { notify('Ошибка AI', 'error') }
  }

  return (
    <div className="app">
      {notification && (
        <Notification message={notification.message} type={notification.type} onClose={() => setNotification(null)} />
      )}

      {!sessionId ? (
        <div className="landing">
          <VacancyInput onSubmit={handleSubmit} loading={loading} />
        </div>
      ) : (
        <div className="workspace">
          <VacancySidebar vacancy={vacancy} />
          <main className="main-content">
            {loading ? (
              <div className="loading-state">
                <div className="spinner" />
                <p>Формируем компетентностный профиль...</p>
              </div>
            ) : (
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
            )}
          </main>
        </div>
      )}

      {addingCategory && (
        <AddSubDialog
          competencyName="Новая категория"
          onAdd={(data) => handleAddCategorySubmit({ name: data.name, emoji: '📌', description: data.description })}
          onClose={() => setAddingCategory(false)}
        />
      )}
    </div>
  )
}