// frontend/src/components/Notification.jsx
import React, { useEffect } from 'react'
import { CheckCircle, AlertCircle, X } from 'lucide-react'
import './Notification.css'
export default function Notification({ message, type = 'success', onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000)
    return () => clearTimeout(timer)
  }, [onClose])

  if (!message) return null

  return (
    <div className={`notification ${type}`}>
      {type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
      <span>{message}</span>
      <button onClick={onClose}><X size={16} /></button>
    </div>
  )
}