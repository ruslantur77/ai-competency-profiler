import React from 'react';
import { LogOut, Plus } from 'lucide-react';

export default function VacancyListHeader({ activeTab, canCreate, onCreate, onLogout }) {
  return (
    <div className="vacancy-list__header">
      <div className="vacancy-list__title">
        <h1>🎯 Competency Profiler</h1>
        <p>Формирование компетентностного профиля специалиста</p>
      </div>
      <div className="vacancy-list__header-actions">
        {activeTab === 'vacancies' && canCreate && (
          <button className="btn-primary" onClick={onCreate}>
            <Plus size={18} /> Создать вакансию
          </button>
        )}
        <button className="btn-secondary vacancy-list__logout" onClick={onLogout}>
          <LogOut size={18} />
        </button>
      </div>
    </div>
  );
}
