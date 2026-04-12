// frontend/src/App.jsx
import React, { useState, useCallback, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import VacancyList from './components/VacancyList'
import VacancyEditor from './components/VacancyEditor'
import LoginPage from './components/LoginPage'
import Notification from './components/Notification'
import './App.css'

function PrivateRoute({ isAuth, children }) {
  return isAuth ? children : <Navigate to="/login" replace />
}

export default function App() {
  const [notification, setNotification] = useState(null)
  const [isAuth, setIsAuth] = useState(!!localStorage.getItem('access_token'))

  const notify = useCallback((message, type = 'success') => {
    setNotification({ message, type })
  }, [])

  const handleLogin = useCallback(() => {
    setIsAuth(true)
  }, [])

  const handleLogout = useCallback(async () => {
    try {
      const { logout } = await import('./api/client')
      await logout()
    } catch {
      // игнорируем
    } finally {
      localStorage.removeItem('access_token')
      setIsAuth(false)
    }
  }, [])

  // Слушаем событие от interceptor когда refresh упал
  useEffect(() => {
    const handleAuthLogout = () => {
      localStorage.removeItem('access_token')
      setIsAuth(false)
    }
    window.addEventListener('auth:logout', handleAuthLogout)
    return () => window.removeEventListener('auth:logout', handleAuthLogout)
  }, [])

  return (
    <div className="app">
      {notification && (
        <Notification
          message={notification.message}
          type={notification.type}
          onClose={() => setNotification(null)}
        />
      )}

      <Routes>
        <Route
          path="/login"
          element={
            isAuth
              ? <Navigate to="/" replace />
              : <LoginPage onLogin={handleLogin} />
          }
        />
        <Route
          path="/"
          element={
            <PrivateRoute isAuth={isAuth}>
              <VacancyList notify={notify} onLogout={handleLogout} />
            </PrivateRoute>
          }
        />
        <Route
          path="/vacancy/:vacancyId"
          element={
            <PrivateRoute isAuth={isAuth}>
              <VacancyEditor notify={notify} onLogout={handleLogout} />
            </PrivateRoute>
          }
        />
      </Routes>
    </div>
  )
}