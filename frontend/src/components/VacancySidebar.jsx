// frontend/src/components/VacancySidebar.jsx
import React, { useState } from 'react'
import { ChevronLeft, ChevronRight, Briefcase, Clock, Tag } from 'lucide-react'
import './VacancySidebar.css'

export default function VacancySidebar({ vacancy }) {
  const [collapsed, setCollapsed] = useState(false)

  if (!vacancy) return null

  return (
    <div className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}>
      <button
        className="sidebar__toggle"
        onClick={() => setCollapsed(!collapsed)}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>

      {!collapsed && (
        <div className="sidebar__content">
          <h2 className="sidebar__title">
            <Briefcase size={18} />
            {vacancy.vacancy_name}
          </h2>

          <div className="sidebar__meta">
            <span><Clock size={14} /> {vacancy.experience}</span>
            {vacancy.key_skills?.length > 0 && (
              <div className="sidebar__skills">
                <Tag size={14} />
                <div className="sidebar__skill-tags">
                  {vacancy.key_skills.map((skill, i) => (
                    <span key={i} className="sidebar__skill-tag">{skill}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="sidebar__text">
            <h3>Описание вакансии</h3>
            <pre>{vacancy.vacancy_text}</pre>
          </div>
        </div>
      )}
    </div>
  )
}