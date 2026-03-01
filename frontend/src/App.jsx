// frontend/src/App.jsx
import React, { useState, useCallback } from 'react'
import { Routes, Route } from 'react-router-dom'
import VacancyList from './components/VacancyList'
import VacancyEditor from './components/VacancyEditor'
import Notification from './components/Notification'
import './App.css'

export default function App() {
  const [notification, setNotification] = useState(null)

  const notify = useCallback((message, type = 'success') => {
    setNotification({ message, type })
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
        <Route path="/" element={<VacancyList notify={notify} />} />
        <Route path="/vacancy/:vacancyId" element={<VacancyEditor notify={notify} />} />
      </Routes>
    </div>
  )
}