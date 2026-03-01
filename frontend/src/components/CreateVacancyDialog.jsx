// frontend/src/components/CreateVacancyDialog.jsx
import React, { useState } from 'react'
import { X, Plus, Download, Loader2 } from 'lucide-react'
import { importFromHH } from '../api/client'
import './CreateVacancyDialog.css'

export default function CreateVacancyDialog({ onClose, onCreate }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [hhUrl, setHhUrl] = useState('')
  const [importing, setImporting] = useState(false)
  const [tab, setTab] = useState('manual') // manual | import

  const handleImport = async () => {
    if (!hhUrl.trim()) return
    setImporting(true)
    try {
      const { data } = await importFromHH(hhUrl.trim())
      setName(data.name)
      setDescription(data.description)
      setTab('manual')
    } catch (err) {
      alert('Ошибка импорта: ' + (err.response?.data?.detail || err.message))
    } finally {
      setImporting(false)
    }
  }

  const handleCreate = () => {
    if (!name.trim()) return
    onCreate({ name: name.trim(), description: description.trim() })
  }

  return (
    <div className="create-vacancy-overlay" onClick={onClose}>
      <div className="create-vacancy" onClick={e => e.stopPropagation()}>
        <div className="create-vacancy__header">
          <h3>➕ Создать вакансию</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="create-vacancy__tabs">
          <button
            className={`create-vacancy__tab ${tab === 'manual' ? 'active' : ''}`}
            onClick={() => setTab('manual')}
          >
            ✏️ Вручную
          </button>
          <button
            className={`create-vacancy__tab ${tab === 'import' ? 'active' : ''}`}
            onClick={() => setTab('import')}
          >
            📥 Импорт с hh.ru
          </button>
        </div>

        <div className="create-vacancy__body">
          {tab === 'import' && (
            <div className="create-vacancy__import">
              <label>
                Ссылка на вакансию hh.ru
                <div className="create-vacancy__import-row">
                  <input
                    value={hhUrl}
                    onChange={e => setHhUrl(e.target.value)}
                    placeholder="https://hh.ru/vacancy/..."
                    disabled={importing}
                  />
                  <button onClick={handleImport} disabled={importing || !hhUrl.trim()}>
                    {importing ? <Loader2 size={16} className="spin" /> : <Download size={16} />}
                    {importing ? 'Загрузка...' : 'Импорт'}
                  </button>
                </div>
              </label>
            </div>
          )}

          <label>
            Название вакансии *
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Например: Data-аналитик"
              autoFocus={tab === 'manual'}
            />
          </label>

          <label>
            Описание вакансии
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Требования, обязанности, условия..."
              rows={10}
            />
          </label>
        </div>

        <div className="create-vacancy__footer">
          <button className="btn-secondary" onClick={onClose}>Отмена</button>
          <button className="btn-primary" onClick={handleCreate} disabled={!name.trim()}>
            <Plus size={16} /> Создать
          </button>
        </div>
      </div>
    </div>
  )
}