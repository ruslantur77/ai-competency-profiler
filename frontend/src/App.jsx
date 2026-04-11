// frontend/src/App.jsx
import React, { useState, useCallback } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import VacancyList from './components/VacancyList'
import VacancyEditor from './components/VacancyEditor'
import LoginPage from './components/LoginPage'
import Notification from './components/Notification'
import './App.css'

function PrivateRoute({ children }) {
  const token = localStorage.getItem('access_token')
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  const [notification, setNotification] = useState(null)
  // Используем стейт чтобы перерисовать после логина
  const [isAuth, setIsAuth] = useState(!!localStorage.getItem('access_token'))

  const notify = useCallback((message, type = 'success') => {
    setNotification({ message, type })
  }, [])

  const handleLogin = () => setIsAuth(true)

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    setIsAuth(false)
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
            <PrivateRoute>
              <VacancyList notify={notify} onLogout={handleLogout} />
            </PrivateRoute>
          }
        />
        <Route
          path="/vacancy/:vacancyId"
          element={
            <PrivateRoute>
              <VacancyEditor notify={notify} onLogout={handleLogout} />
            </PrivateRoute>
          }
        />
      </Routes>
    </div>
  )
}