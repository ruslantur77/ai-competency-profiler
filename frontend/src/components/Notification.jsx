// frontend/src/components/Notification.jsx
import React, { useEffect, useState } from 'react'
import { CheckCircle, AlertCircle, X } from 'lucide-react'
import './Notification.css'

export default function Notification({ message, type = 'success', onClose }) {
  const [closing, setClosing] = useState(false)

  const handleClose = () => {
    setClosing(true)
    setTimeout(onClose, 400) // ждём завершения анимации
  }

  useEffect(() => {
    const timer = setTimeout(handleClose, 8000)
    return () => clearTimeout(timer)
  }, [])

  if (!message) return null

  return (
    <div className={`notification notification--${type} ${closing ? 'notification--closing' : ''}`}>
      {type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
      <span>{message}</span>
      <button onClick={handleClose}><X size={16} /></button>
    </div>
  )
}