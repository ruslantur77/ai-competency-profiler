// frontend/src/App.jsx
import React, { useState, useCallback, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import VacancyList from './components/VacancyList'
import VacancyEditor from './components/VacancyEditor'
import LoginPage from './components/LoginPage'
import Notification from './components/Notification'
import { getMe, logout } from './api/auth'
import { ROLES, hasAllowedRole } from './api/roles'
import './App.css'

function PrivateRoute({ isAuth, isLoading, role, allowedRoles, children }) {
  if (isLoading) {
    return (
      <div style={{ padding: 24 }}>
        <p>Проверка сессии...</p>
      </div>
    )
  }

  if (!isAuth) return <Navigate to="/login" replace />
  if (!hasAllowedRole(role, allowedRoles)) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const [notification, setNotification] = useState(null)
  const [isAuth, setIsAuth] = useState(!!localStorage.getItem('access_token'))
  const [authLoading, setAuthLoading] = useState(!!localStorage.getItem('access_token'))
  const [currentUser, setCurrentUser] = useState(null)

  const notify = useCallback((message, type = 'success', options = {}) => {
    setNotification({ message, type, duration: options.duration })
  }, [])

  const loadCurrentUser = useCallback(async () => {
    if (!localStorage.getItem('access_token')) {
      setCurrentUser(null)
      setIsAuth(false)
      setAuthLoading(false)
      return
    }

    setAuthLoading(true)
    try {
      const { data } = await getMe()
      setCurrentUser(data)
      setIsAuth(true)
    } catch {
      localStorage.removeItem('access_token')
      setCurrentUser(null)
      setIsAuth(false)
    } finally {
      setAuthLoading(false)
    }
  }, [])

  const handleLogin = useCallback(async () => {
    await loadCurrentUser()
  }, [loadCurrentUser])

  const handleLogout = useCallback(async () => {
    try {
      await logout()
    } catch {
      // игнорируем
    } finally {
      localStorage.removeItem('access_token')
      setCurrentUser(null)
      setIsAuth(false)
      setAuthLoading(false)
    }
  }, [])

  useEffect(() => {
    loadCurrentUser()
  }, [loadCurrentUser])

  // Слушаем событие от interceptor когда refresh упал
  useEffect(() => {
    const handleAuthLogout = () => {
      localStorage.removeItem('access_token')
      setCurrentUser(null)
      setIsAuth(false)
      setAuthLoading(false)
    }

    const handleAuthRefreshed = () => {
      loadCurrentUser()
    }

    window.addEventListener('auth:logout', handleAuthLogout)
    window.addEventListener('auth:refreshed', handleAuthRefreshed)
    return () => {
      window.removeEventListener('auth:logout', handleAuthLogout)
      window.removeEventListener('auth:refreshed', handleAuthRefreshed)
    }
  }, [loadCurrentUser])

  return (
    <div className="app">
      {notification && (
        <Notification
          message={notification.message}
          type={notification.type}
          duration={notification.duration}
          onClose={() => setNotification(null)}
        />
      )}

      <Routes>
        <Route
          path="/login"
          element={
            isAuth && !authLoading
              ? <Navigate to="/" replace />
              : <LoginPage onLogin={handleLogin} />
          }
        />
        <Route
          path="/"
          element={
            <PrivateRoute
              isAuth={isAuth}
              isLoading={authLoading}
              role={currentUser?.role}
              allowedRoles={[ROLES.ADMIN, ROLES.EXPERT, ROLES.HR, ROLES.SYSTEM]}
            >
              <VacancyList
                notify={notify}
                onLogout={handleLogout}
                role={currentUser?.role}
              />
            </PrivateRoute>
          }
        />
        <Route
          path="/vacancy/:vacancyId"
          element={
            <PrivateRoute
              isAuth={isAuth}
              isLoading={authLoading}
              role={currentUser?.role}
              allowedRoles={[ROLES.ADMIN, ROLES.EXPERT, ROLES.HR]}
            >
              <VacancyEditor
                notify={notify}
                role={currentUser?.role}
              />
            </PrivateRoute>
          }
        />
      </Routes>
    </div>
  )
}
