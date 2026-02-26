// frontend/src/components/VacancyInput.jsx
import React, { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import './VacancyInput.css'

export default function VacancyInput({ onSubmit, loading }) {
  const [url, setUrl] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (url.trim()) {
      onSubmit(url.trim())
    }
  }

  return (
    <div className="vacancy-input">
      <h1 className="vacancy-input__logo">🎯 Competency Profiler</h1>
      <p className="vacancy-input__subtitle">
        Вставьте ссылку на вакансию с hh.ru для формирования компетентностного профиля
      </p>
      <form onSubmit={handleSubmit} className="vacancy-input__form">
        <div className="vacancy-input__wrapper">
          <Search size={20} className="vacancy-input__icon" />
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://hh.ru/vacancy/..."
            disabled={loading}
          />
        </div>
        <button type="submit" disabled={loading || !url.trim()}>
          {loading ? (
            <>
              <Loader2 size={18} className="spin" />
              Анализирую...
            </>
          ) : (
            'Анализировать'
          )}
        </button>
      </form>
    </div>
  )
}