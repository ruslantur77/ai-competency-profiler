import React from 'react'
import { Shield, UserX } from 'lucide-react'
import { formatDateTime } from '../../utils/formatters'

const ROLE_OPTIONS = ['admin', 'expert', 'hr', 'system']

export default function AdminUsersTable({
  users,
  currentUserId,
  updatingRoleId,
  updatingStatusId,
  onRoleChange,
  onStatusToggle,
}) {
  return (
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
                onChange={(event) => onRoleChange(user.id, event.target.value)}
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
                onClick={() => onStatusToggle(user)}
              >
                <UserX size={14} />
                {user.is_active ? 'Deactivate' : 'Activate'}
              </button>
            </span>
          </div>
        )
      })}
    </div>
  )
}
