import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Shield, UserPlus, UserX } from 'lucide-react'
import {
  createAdminUser,
  listAdminUsers,
  updateAdminUserRole,
  updateAdminUserStatus,
} from '../api/adminUsers'
import { getErrorMessage } from '../api/errors'
import { extractItems } from '../api/adapters'
import ConfirmDialog from './ConfirmDialog'
import AsyncState from './AsyncState'
import './AdminUsersTab.css'

const ROLE_OPTIONS = ['admin', 'expert', 'hr', 'system']
const SELF_ACTION_GUARD_MESSAGE =
  'Операция запрещена: нельзя изменять собственную роль или деактивировать свою учетную запись'

const formatDateTime = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleString('ru-RU')
}

function CreateUserForm({ onSubmit, creating }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('hr')

  const isValid = email.trim().length > 0 && password.trim().length >= 8

  const handleSubmit = (event) => {
    event.preventDefault()
    if (!isValid || creating) return
    onSubmit({
      email: email.trim(),
      password,
      role,
    })
    setEmail('')
    setPassword('')
    setRole('hr')
  }

  return (
    <form className="admin-users__create" onSubmit={handleSubmit}>
      <h3>
        <UserPlus size={16} />
        Создать пользователя
      </h3>
      <div className="admin-users__create-grid">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Пароль (мин. 8 символов)"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={8}
          required
        />
        <select value={role} onChange={(event) => setRole(event.target.value)}>
          {ROLE_OPTIONS.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <button type="submit" className="btn-primary" disabled={!isValid || creating}>
          Создать
        </button>
      </div>
    </form>
  )
}

export default function AdminUsersTab({ notify, currentUserId }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)
  const [updatingRoleId, setUpdatingRoleId] = useState(null)
  const [updatingStatusId, setUpdatingStatusId] = useState(null)

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await listAdminUsers({ limit: 200, offset: 0 })
      const items = extractItems(data).sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      )
      setUsers(items)
    } catch (error) {
      setUsers([])
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки пользователей' }), 'error')
    } finally {
      setLoading(false)
    }
  }, [notify])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const counters = useMemo(() => {
    const active = users.filter((user) => user.is_active).length
    return {
      total: users.length,
      active,
      inactive: users.length - active,
    }
  }, [users])

  const handleCreateUser = async (payload) => {
    setCreating(true)
    try {
      const { data } = await createAdminUser(payload)
      setUsers((prev) => [data, ...prev])
      notify(`Пользователь ${payload.email} создан`)
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка создания пользователя' }), 'error')
    } finally {
      setCreating(false)
    }
  }

  const handleRoleChange = async (userId, nextRole) => {
    setUpdatingRoleId(userId)
    try {
      const { data } = await updateAdminUserRole(userId, nextRole)
      setUsers((prev) => prev.map((item) => (item.id === userId ? data : item)))
      notify('Роль пользователя обновлена')
    } catch (error) {
      notify(
        getErrorMessage(error, {
          fallback: 'Ошибка смены роли',
          overrides: {
            409: SELF_ACTION_GUARD_MESSAGE,
            422: SELF_ACTION_GUARD_MESSAGE,
          },
        }),
        'error'
      )
    } finally {
      setUpdatingRoleId(null)
    }
  }

  const handleStatusConfirm = async () => {
    if (!pendingAction) return
    const { user } = pendingAction
    setUpdatingStatusId(user.id)
    try {
      const { data } = await updateAdminUserStatus(user.id, !user.is_active)
      setUsers((prev) => prev.map((item) => (item.id === user.id ? data : item)))
      notify(data.is_active ? 'Пользователь активирован' : 'Пользователь деактивирован')
      setPendingAction(null)
    } catch (error) {
      notify(
        getErrorMessage(error, {
          fallback: 'Ошибка изменения статуса',
          overrides: {
            409: SELF_ACTION_GUARD_MESSAGE,
            422: SELF_ACTION_GUARD_MESSAGE,
          },
        }),
        'error'
      )
    } finally {
      setUpdatingStatusId(null)
    }
  }

  if (loading) {
    return <AsyncState kind="loading" title="Загрузка пользователей..." />
  }

  return (
    <div className="admin-users">
      <div className="admin-users__stats">
        <div className="admin-users__stat">
          <span className="admin-users__stat-value">{counters.total}</span>
          <span className="admin-users__stat-label">Всего</span>
        </div>
        <div className="admin-users__stat admin-users__stat--active">
          <span className="admin-users__stat-value">{counters.active}</span>
          <span className="admin-users__stat-label">Активные</span>
        </div>
        <div className="admin-users__stat admin-users__stat--inactive">
          <span className="admin-users__stat-value">{counters.inactive}</span>
          <span className="admin-users__stat-label">Неактивные</span>
        </div>
      </div>

      <CreateUserForm onSubmit={handleCreateUser} creating={creating} />

      <div className="admin-users__table-wrap">
        <div className="admin-users__table-header">
          <span>Email</span>
          <span>Роль</span>
          <span>Статус</span>
          <span>Создан</span>
          <span>Обновлен</span>
          <span>Действия</span>
        </div>
        {users.map((user) => {
          const isSelf = user.id === currentUserId
          return (
            <div key={user.id} className="admin-users__table-row">
              <span className="admin-users__email">
                <Shield size={14} />
                {user.email}
              </span>
              <span>
                <select
                  value={user.role}
                  disabled={updatingRoleId === user.id || isSelf}
                  title={isSelf ? 'Собственную роль менять нельзя' : undefined}
                  onChange={(event) => handleRoleChange(user.id, event.target.value)}
                >
                  {ROLE_OPTIONS.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </span>
              <span>
                <span className={`admin-users__status ${user.is_active ? 'is-active' : 'is-inactive'}`}>
                  {user.is_active ? 'active' : 'inactive'}
                </span>
              </span>
              <span>{formatDateTime(user.created_at)}</span>
              <span>{formatDateTime(user.updated_at)}</span>
              <span>
                <button
                  className="btn-secondary admin-users__toggle"
                  disabled={updatingStatusId === user.id || isSelf}
                  title={isSelf ? 'Собственную учетную запись деактивировать нельзя' : undefined}
                  onClick={() =>
                    setPendingAction({
                      user,
                      title: user.is_active ? 'Деактивация пользователя' : 'Активация пользователя',
                      confirmLabel: user.is_active ? 'Деактивировать' : 'Активировать',
                      message: user.is_active
                        ? `Деактивировать ${user.email}? Пользователь потеряет доступ к системе.`
                        : `Активировать ${user.email}?`,
                    })
                  }
                >
                  <UserX size={14} />
                  {user.is_active ? 'Deactivate' : 'Activate'}
                </button>
              </span>
            </div>
          )
        })}
      </div>

      {pendingAction && (
        <ConfirmDialog
          title={pendingAction.title}
          message={pendingAction.message}
          confirmLabel={pendingAction.confirmLabel}
          onCancel={() => setPendingAction(null)}
          onConfirm={handleStatusConfirm}
        />
      )}
    </div>
  )
}
