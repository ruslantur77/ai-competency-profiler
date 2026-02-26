// frontend/src/components/MindMap.jsx
import React, { useState } from 'react'
import {
  ChevronRight, ChevronDown, Edit3, Trash2,
  Sparkles, Plus, GripVertical
} from 'lucide-react'
import NodeEditor from './NodeEditor'
import './MindMap.css'

const LEVEL_COLORS = {
  beginner: { bg: '#dcfce7', border: '#22c55e', text: '#15803d', badge: '🟢' },
  intermediate: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af', badge: '🟡' },
  advanced: { bg: '#fee2e2', border: '#ef4444', text: '#b91c1c', badge: '🔴' },
}

const CAT_COLORS = [
  '#4CAF50', '#2196F3', '#FF9800', '#E91E63',
  '#9C27B0', '#00BCD4', '#FF5722', '#795548',
]

function SubCompetencyNode({ sub, competencyId, onEdit, onDelete, onAiFix }) {
  const [expanded, setExpanded] = useState(false)
  const colors = LEVEL_COLORS[sub.level] || LEVEL_COLORS.intermediate

  return (
    <div className="mindmap__sub-node" style={{ borderLeftColor: colors.border }}>
      <div className="mindmap__sub-header">
        <button className="mindmap__expand-btn" onClick={() => setExpanded(!expanded)}>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        <span className="mindmap__level-badge" style={{
          backgroundColor: colors.bg, color: colors.text
        }}>
          {colors.badge} {sub.level}
        </span>

        <span className="mindmap__sub-name">{sub.name}</span>

        <div className="mindmap__sub-actions">
          <button title="Редактировать" onClick={() => onEdit(sub, competencyId)}>
            <Edit3 size={14} />
          </button>
          <button title="AI исправление" onClick={() => onAiFix(sub, competencyId)}>
            <Sparkles size={14} />
          </button>
          <button title="Удалить" onClick={() => onDelete(sub.id, competencyId)}>
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mindmap__sub-details">
          <p className="mindmap__sub-description">{sub.description}</p>
          {sub.sub_skills?.length > 0 && (
            <ul className="mindmap__sub-skills-list">
              {sub.sub_skills.map((ss, i) => (
                <li key={i}>{ss}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

function CompetencyNode({ comp, onEdit, onDelete, onAiFix, onAdd }) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="mindmap__comp-node">
      <div className="mindmap__comp-header" onClick={() => setExpanded(!expanded)}>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <GripVertical size={14} className="mindmap__grip" />
        <span className="mindmap__comp-name">{comp.skill}</span>
        <span className="mindmap__comp-count">{comp.sub_competencies?.length || 0}</span>
      </div>

      {expanded && (
        <div className="mindmap__comp-children">
          {comp.sub_competencies?.map(sub => (
            <SubCompetencyNode
              key={sub.id}
              sub={sub}
              competencyId={comp.id}
              onEdit={onEdit}
              onDelete={onDelete}
              onAiFix={onAiFix}
            />
          ))}
          <button className="mindmap__add-btn" onClick={() => onAdd(comp.id)}>
            <Plus size={14} /> Добавить подкомпетенцию
          </button>
        </div>
      )}
    </div>
  )
}

export default function MindMap({
  categories,
  competencies,
  onUpdateSub,
  onDeleteSub,
  onAddSub,
  onAiFix,
}) {
  const [editing, setEditing] = useState(null)
  const [editingCompId, setEditingCompId] = useState(null)

  const handleEdit = (sub, competencyId) => {
    setEditing(sub)
    setEditingCompId(competencyId)
  }

  const handleSave = (updatedSub) => {
    onUpdateSub(editingCompId, updatedSub)
    setEditing(null)
    setEditingCompId(null)
  }

  const handleAiFix = (sub, competencyId) => {
    const instruction = prompt(`🤖 Что изменить в "${sub.name}"?\nОпишите инструкцию для AI:`)
    if (instruction) {
      onAiFix(competencyId, sub.id, instruction)
    }
  }

  const handleAdd = (competencyId) => {
    const name = prompt('Название новой подкомпетенции:')
    if (name) {
      onAddSub(competencyId, {
        name,
        level: 'intermediate',
        description: '',
        sub_skills: [],
      })
    }
  }

  return (
    <div className="mindmap">
      <div className="mindmap__header">
        <h2>🧠 Граф компетенций</h2>
        <div className="mindmap__legend">
          <span>🟢 Beginner</span>
          <span>🟡 Intermediate</span>
          <span>🔴 Advanced</span>
        </div>
      </div>

      <div className="mindmap__tree">
        {categories?.map((cat, catIdx) => {
          const catComps = competencies?.filter(c => c.category_id === cat.id) || []
          if (catComps.length === 0) return null

          return (
            <div key={cat.id} className="mindmap__category">
              <div
                className="mindmap__category-header"
                style={{ borderLeftColor: CAT_COLORS[catIdx % CAT_COLORS.length] }}
              >
                <span className="mindmap__category-emoji">{cat.emoji}</span>
                <span className="mindmap__category-name">{cat.name}</span>
                <span className="mindmap__category-count">{catComps.length}</span>
              </div>

              <div className="mindmap__category-children">
                {catComps.map(comp => (
                  <CompetencyNode
                    key={comp.id}
                    comp={comp}
                    onEdit={handleEdit}
                    onDelete={onDeleteSub}
                    onAiFix={handleAiFix}
                    onAdd={handleAdd}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {editing && (
        <NodeEditor
          sub={editing}
          onSave={handleSave}
          onClose={() => { setEditing(null); setEditingCompId(null) }}
        />
      )}
    </div>
  )
}