import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createAdminUser,
  listAdminUsers,
  updateAdminUserRole,
  updateAdminUserStatus,
} from '../api/adminUsers';
import { getErrorMessage } from '../api/errors';
import usePaginatedResource from '../hooks/usePaginatedResource';
import ConfirmDialog from './ConfirmDialog';
import AsyncState from './AsyncState';
import CreateUserForm from './admin-users/CreateUserForm';
import AdminUsersStats from './admin-users/AdminUsersStats';
import AdminUsersTable from './admin-users/AdminUsersTable';
import './AdminUsersTab.css';

const SELF_ACTION_GUARD_MESSAGE =
  'Операция запрещена: нельзя изменять собственную роль или деактивировать свою учетную запись';
const USERS_PAGE_LIMIT = 50;

export default function AdminUsersTab({ notify, currentUserId }) {
  const [creating, setCreating] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [updatingRoleId, setUpdatingRoleId] = useState(null);
  const [updatingStatusId, setUpdatingStatusId] = useState(null);

  const fetchUsersPage = useCallback(async ({ offset, limit }) => {
    const { data } = await listAdminUsers({ limit, offset });
    return data;
  }, []);

  const handleError = useCallback(
    (error) => {
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки пользователей' }), 'error');
    },
    [notify]
  );

  const {
    items: usersRaw,
    total: usersTotal,
    limit: usersLimit,
    loading,
    loadPage: loadUsersPage,
  } = usePaginatedResource({
    fetchPage: fetchUsersPage,
    initialLimit: USERS_PAGE_LIMIT,
    initialOffset: 0,
    onError: handleError,
  });

  useEffect(() => {
    loadUsersPage({ offset: 0, limit: USERS_PAGE_LIMIT });
  }, [loadUsersPage]);

  const users = useMemo(
    () => [...usersRaw].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [usersRaw]
  );

  const counters = useMemo(() => {
    const active = users.filter((user) => user.is_active).length;
    return {
      total: usersTotal || users.length,
      active,
      inactive: (usersTotal || users.length) - active,
    };
  }, [users, usersTotal]);

  const handleCreateUser = async (payload) => {
    setCreating(true);
    try {
      await createAdminUser(payload);
      await loadUsersPage({ offset: 0, limit: usersLimit, silent: true });
      notify(`Пользователь ${payload.email} создан`);
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка создания пользователя' }), 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleRoleChange = async (userId, nextRole) => {
    setUpdatingRoleId(userId);
    try {
      await updateAdminUserRole(userId, nextRole);
      await loadUsersPage({ offset: 0, limit: usersLimit, silent: true });
      notify('Роль пользователя обновлена');
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
      );
    } finally {
      setUpdatingRoleId(null);
    }
  };

  const handleStatusToggle = (user) => {
    setPendingAction({
      user,
      title: user.is_active ? 'Деактивация пользователя' : 'Активация пользователя',
      confirmLabel: user.is_active ? 'Деактивировать' : 'Активировать',
      message: user.is_active
        ? `Деактивировать ${user.email}? Пользователь потеряет доступ к системе.`
        : `Активировать ${user.email}?`,
    });
  };

  const handleStatusConfirm = async () => {
    if (!pendingAction) return;
    const { user } = pendingAction;
    setUpdatingStatusId(user.id);
    try {
      const nextStatus = !user.is_active;
      await updateAdminUserStatus(user.id, nextStatus);
      await loadUsersPage({ offset: 0, limit: usersLimit, silent: true });
      notify(nextStatus ? 'Пользователь активирован' : 'Пользователь деактивирован');
      setPendingAction(null);
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
      );
    } finally {
      setUpdatingStatusId(null);
    }
  };

  if (loading) {
    return <AsyncState kind="loading" title="Загрузка пользователей..." />;
  }

  return (
    <div className="admin-users">
      <AdminUsersStats counters={counters} />

      <CreateUserForm onSubmit={handleCreateUser} creating={creating} />

      <AdminUsersTable
        users={users}
        currentUserId={currentUserId}
        updatingRoleId={updatingRoleId}
        updatingStatusId={updatingStatusId}
        onRoleChange={handleRoleChange}
        onStatusToggle={handleStatusToggle}
      />

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
  );
}
