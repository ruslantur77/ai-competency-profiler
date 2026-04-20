// frontend/src/components/NotFoundPage.jsx
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Home } from 'lucide-react'
import './NotFoundPage.css'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="not-found">
      <div className="not-found__content">
        <span className="not-found__code">404</span>
        <h1 className="not-found__title">Вы попали не туда🫣</h1>
        <p className="not-found__hint">
        Возможно, вы искали какую-то страницу, о которой мы сами не знаем, но здесь вы точно не сформируете компетентностный профиль.
        </p>
        <button
          className="btn-primary not-found__btn"
          onClick={() => navigate('/')}
        >
          <Home size={18} /> На главную
        </button>
      </div>
    </div>
  )
}