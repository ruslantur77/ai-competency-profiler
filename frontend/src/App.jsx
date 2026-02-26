// frontend/src/App.jsx
import React, { useState, useCallback } from 'react'
import VacancyInput from './components/VacancyInput'
import VacancySidebar from './components/VacancySidebar'
import MindMap from './components/MindMap'
import Notification from './components/Notification'
import {
  parseVacancy, getGraph, updateSubCompetency,
  deleteSubCompetency, addSubCompetency, aiFixCompetency
} from './api/client'
import './App.css'

export default function App() {
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [vacancy, setVacancy] = useState(null)
  const [categories, setCategories] = useState([])
  const [competencies, setCompetencies] = useState([])
  const [notification, setNotification] = useState(null)

  const notify = useCallback((message, type = 'success') => {
    setNotification({ message, type })
  }, [])

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
        return {
          ...comp,
          sub_competencies: comp.sub_competencies.map(sub =>
            sub.id === updatedSub.id ? updatedSub : sub
          )
        }
      }))

      notify(`✏️ "${updatedSub.name}" обновлена`)
    } catch (err) {
      notify('Ошибка обновления', 'error')
    }
  }

  const handleDeleteSub = async (subId, competencyId) => {
    if (!confirm('Удалить эту подкомпетенцию?')) return

    try {
      await deleteSubCompetency(sessionId, {
        competency_id: competencyId,
        sub_competency_id: subId,
      })

      setCompetencies(prev => prev.map(comp => {
        if (comp.id !== competencyId) return comp
        return {
          ...comp,
          sub_competencies: comp.sub_competencies.filter(s => s.id !== subId)
        }
      }))

      notify('🗑️ Подкомпетенция удалена')
    } catch (err) {
      notify('Ошибка удаления', 'error')
    }
  }

  const handleAddSub = async (competencyId, newSub) => {
    try {
      const { data } = await addSubCompetency(sessionId, {
        competency_id: competencyId,
        ...newSub,
      })

      setCompetencies(prev => prev.map(comp => {
        if (comp.id !== competencyId) return comp
        return {
          ...comp,
          sub_competencies: [...comp.sub_competencies, data.created]
        }
      }))

      notify(`➕ "${newSub.name}" добавлена`)
    } catch (err) {
      notify('Ошибка добавления', 'error')
    }
  }

  const handleAiFix = async (competencyId, subId, instruction) => {
    try {
      const { data } = await aiFixCompetency(sessionId, {
        competency_id: competencyId,
        sub_competency_id: subId,
        instruction,
      })

      notify(`🤖 ${data.message}`)
    } catch (err) {
      notify('Ошибка AI', 'error')
    }
  }

  return (
    <div className="app">
      {notification && (
        <Notification
          message={notification.message}
          type={notification.type}
          onClose={() => setNotification(null)}
        />
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
              />
            )}
          </main>
        </div>
      )}
    </div>
  )
}