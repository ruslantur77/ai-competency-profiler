// frontend/src/components/VacancyList.jsx
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Edit3, Trash2, Loader2, CheckCircle, ExternalLink } from 'lucide-react'
import { listVacancies, createVacancy, deleteVacancy } from '../api/client'
import CreateVacancyDialog from './CreateVacancyDialog'
import ConfirmDialog from './ConfirmDialog'
import './VacancyList.css'

export default function VacancyList({ notify }) {
  const navigate = useNavigate()
  const [vacancies, setVacancies] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState(null)

  const fetchVacancies = async () => {
    try {
      const { data } = await listVacancies()
      setVacancies(data.vacancies || [])
    } catch (err) {
      notify('Ошибка загрузки вакансий', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchVacancies()
    // Поллинг статусов каждые 2 секунды
    const interval = setInterval(fetchVacancies, 2000)
    return () => clearInterval(interval)
  }, [])

  const handleCreate = async (data) => {
    try {
      const { data: result } = await createVacancy(data)
      setCreating(false)
      fetchVacancies()
      notify(`✅ Вакансия "${data.name}" создана`)
    } catch (err) {
      notify('Ошибка создания', 'error')
    }
  }

  const handleDelete = async () => {
    try {
      await deleteVacancy(deleting.id)
      setDeleting(null)
      fetchVacancies()
      notify('🗑️ Вакансия удалена')
    } catch (err) {
      notify('Ошибка удаления', 'error')
    }
  }

  const handleOpen = (vacancy) => {
    if (vacancy.status === 'ready') {
      navigate(`/vacancy/${vacancy.id}`)
    }
  }

  return (
    <div className="vacancy-list">
      <div className="vacancy-list__header">
        <div className="vacancy-list__title">
          <h1>🎯 Competency Profiler</h1>
          <p>Формирование компетентностного профиля специалиста</p>
        </div>
        <button className="btn-primary" onClick={() => setCreating(true)}>
          <Plus size={18} /> Создать вакансию
        </button>
      </div>

      <div className="vacancy-list__content">
        {loading ? (
          <div className="vacancy-list__loading">
            <div className="spinner" />
            <p>Загрузка...</p>
          </div>
        ) : vacancies.length === 0 ? (
          <div className="vacancy-list__empty">
            <p>📋 Вакансий пока нет</p>
            <p>Создайте первую вакансию для формирования профиля компетенций</p>
            <button className="btn-primary" onClick={() => setCreating(true)}>
              <Plus size={18} /> Создать вакансию
            </button>
          </div>
        ) : (
          <div className="vacancy-list__grid">
            {vacancies.map(vac => (
              <div
                key={vac.id}
                className={`vacancy-card ${vac.status === 'ready' ? 'vacancy-card--ready' : 'vacancy-card--extracting'}`}
                onClick={() => handleOpen(vac)}
              >
                <div className="vacancy-card__header">
                  <h3>{vac.name}</h3>
                  <div className="vacancy-card__actions" onClick={e => e.stopPropagation()}>
                    <button
                      title="Удалить"
                      onClick={() => setDeleting(vac)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                <div className="vacancy-card__status">
                  {vac.status === 'extracting' ? (
                    <span className="vacancy-card__badge vacancy-card__badge--extracting">
                      <Loader2 size={14} className="spin" />
                      Извлечение компетенций...
                    </span>
                  ) : (
                    <span className="vacancy-card__badge vacancy-card__badge--ready">
                      <CheckCircle size={14} />
                      Готово к редактированию
                    </span>
                  )}
                </div>

                <div className="vacancy-card__footer">
                  <span className="vacancy-card__date">
                    {new Date(vac.created_at).toLocaleDateString('ru-RU')}
                  </span>
                  {vac.status === 'ready' && (
                    <span className="vacancy-card__open">
                      Открыть <ExternalLink size={14} />
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {creating && (
        <CreateVacancyDialog
          onClose={() => setCreating(false)}
          onCreate={handleCreate}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title="Удаление вакансии"
          message={`Удалить "${deleting.name}" и все её компетенции? Это действие нельзя отменить.`}
          onConfirm={handleDelete}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  )
}