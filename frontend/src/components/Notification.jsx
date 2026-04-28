// frontend/src/components/Notification.jsx
import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle, AlertCircle, X } from 'lucide-react';
import {CheckCircleIcon } from "@phosphor-icons/react";
import './Notification.css';

const DEFAULT_DURATION_BY_TYPE = {
  success: 4500,
  info: 6000,
  error: 9000,
};

export default function Notification({ message, type = 'success', onClose, duration }) {
  const [closing, setClosing] = useState(false);
  const closeDelay = duration ?? DEFAULT_DURATION_BY_TYPE[type] ?? 6000;

  const handleClose = useCallback(() => {
    setClosing(true);
    setTimeout(onClose, 400); // ждём завершения анимации
  }, [onClose]);

  useEffect(() => {
    const timer = setTimeout(handleClose, closeDelay);
    return () => clearTimeout(timer);
  }, [handleClose, closeDelay]);

  if (!message) return null;

  return (
    <div className={`notification notification--${type} ${closing ? 'notification--closing' : ''}`}>
      {type === 'success' ? <CheckCircleIcon size={22} weight='bold'/> : <AlertCircle size={18} />}
      <span>{message}</span>
      <button onClick={handleClose}>
        <X size={16} />
      </button>
    </div>
  );
}
