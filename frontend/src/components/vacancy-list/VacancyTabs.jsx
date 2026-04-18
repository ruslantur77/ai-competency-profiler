import React from 'react';

export default function VacancyTabs({ tabs, activeTab, onTabChange }) {
  return (
    <div className="vacancy-list__tabs">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`vacancy-list__tab ${activeTab === tab.id ? 'vacancy-list__tab--active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
