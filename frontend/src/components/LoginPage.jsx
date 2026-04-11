// frontend/src/components/LoginPage.jsx
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, LogIn } from 'lucide-react'
import { login } from '../api/client'
import './LoginPage.css'

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) return

    setLoading(true)
    setError(null)

    try {
      const { data } = await login(email.trim(), password)
      localStorage.setItem('access_token', data.access_token)
      onLogin()
      navigate('/')
    } catch (err) {
      setError(
        err.response?.status === 401
          ? 'Неверный email или пароль'
          : 'Ошибка сервера, попробуйте позже'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__header">
          <h1>🎯 Competency Profiler</h1>
          <p>Формирование компетентностного профиля специалиста</p>
        </div>

        <form className="login-card__form" onSubmit={handleSubmit}>
          {error && (
            <div className="login-card__error">
              {error}
            </div>
          )}

          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="admin@example.com"
              disabled={loading}
              autoFocus
            />
          </label>

          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
            />
          </label>

          <button
            type="submit"
            className="btn-primary login-card__submit"
            disabled={loading || !email.trim() || !password.trim()}
          >
            {loading
              ? <><Loader2 size={18} className="spin" /> Вход...</>
              : <><LogIn size={18} /> Войти</>
            }
          </button>
        </form>
      </div>
    </div>
  )
}