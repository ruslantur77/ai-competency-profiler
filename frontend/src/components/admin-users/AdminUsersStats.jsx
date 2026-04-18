import React from 'react';

export default function AdminUsersStats({ counters }) {
  return (
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
  );
}
