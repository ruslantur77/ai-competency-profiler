// frontend/src/components/MindMap.jsx
import React, { useState } from 'react'
import {
  ChevronRight, ChevronDown, Edit3, Trash2,
  Sparkles, Plus
} from 'lucide-react'
import NodeEditor from './NodeEditor'
import ConfirmDialog from './ConfirmDialog'
import AddSubDialog from './AddSubDialog'
import AiFixDialog from './AiFixDialog'
import EditCategoryDialog from './EditCategoryDialog'
import EditCompetencyDialog from './EditCompetencyDialog'
import AddCompetencyDialog from './AddCompetencyDialog'
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

// ===== SUB COMPETENCY =====
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
          <button title="Удалить" onClick={() => onDelete(sub, competencyId)}>
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

// ===== COMPETENCY =====
function CompetencyNode({ comp, onEdit, onDelete, onAiFix, onAdd, onEditComp, onDeleteComp, onAiFixComp }) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="mindmap__comp-node">
      <div className="mindmap__comp-header">
        <div className="mindmap__comp-header-left" onClick={() => setExpanded(!expanded)}>
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span className="mindmap__comp-name">{comp.skill}</span>
          <span className="mindmap__comp-count">{comp.sub_competencies?.length || 0}</span>
        </div>

        <div className="mindmap__comp-actions">
          <button title="Редактировать компетенцию" onClick={() => onEditComp(comp)}>
            <Edit3 size={14} />
          </button>
          <button title="AI исправление" onClick={() => onAiFixComp(comp)}>
            <Sparkles size={14} />
          </button>
          <button title="Удалить компетенцию" onClick={() => onDeleteComp(comp)}>
            <Trash2 size={14} />
          </button>
        </div>
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
          <button className="mindmap__add-btn" onClick={() => onAdd(comp)}>
            <Plus size={14} /> Добавить подкомпетенцию
          </button>
        </div>
      )}
    </div>
  )
}

// ===== MAIN MINDMAP =====
export default function MindMap({
  categories,
  competencies,
  onUpdateSub,
  onDeleteSub,
  onAddSub,
  onAiFix,
  onUpdateCategory,
  onDeleteCategory,
  onAiFixCategory,
  onUpdateCompetency,
  onDeleteCompetency,
  onAddCompetency,
  onAiFixCompetency,
  onAddCategory,
}) {
  // Подкомпетенции
  const [editing, setEditing] = useState(null)
  const [editingCompId, setEditingCompId] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [deletingCompId, setDeletingCompId] = useState(null)
  const [adding, setAdding] = useState(null)
  const [aiFixing, setAiFixing] = useState(null)
  const [aiFixingCompId, setAiFixingCompId] = useState(null)

  // Категории
  const [editingCat, setEditingCat] = useState(null)
  const [deletingCat, setDeletingCat] = useState(null)
  const [aiFixingCat, setAiFixingCat] = useState(null)

  // Компетенции
  const [editingComp, setEditingComp] = useState(null)
  const [deletingComp, setDeletingComp] = useState(null)
  const [aiFixingComp, setAiFixingComp] = useState(null)
  const [addingComp, setAddingComp] = useState(null) // категория, к которой добавляем

  // ===== ПОДКОМПЕТЕНЦИИ =====
  const handleEditSub = (sub, competencyId) => { setEditing(sub); setEditingCompId(competencyId) }
  const handleSaveSub = (updatedSub) => { onUpdateSub(editingCompId, updatedSub); setEditing(null) }
  const handleDeleteSubClick = (sub, competencyId) => { setDeleting(sub); setDeletingCompId(competencyId) }
  const handleDeleteSubConfirm = () => { onDeleteSub(deleting.id, deletingCompId); setDeleting(null) }
  const handleAddSubClick = (comp) => { setAdding(comp) }
  const handleAddSubSubmit = (newSub) => { onAddSub(adding.id, newSub); setAdding(null) }
  const handleAiFixSubClick = (sub, competencyId) => { setAiFixing(sub); setAiFixingCompId(competencyId) }
  const handleAiFixSubSubmit = (instruction) => { onAiFix(aiFixingCompId, aiFixing.id, instruction); setAiFixing(null) }

  // ===== КАТЕГОРИИ =====
  const handleSaveCat = (updated) => { onUpdateCategory(updated); setEditingCat(null) }
  const handleDeleteCatConfirm = () => { onDeleteCategory(deletingCat.id); setDeletingCat(null) }
  const handleAiFixCatSubmit = (instruction) => { onAiFixCategory(aiFixingCat.id, instruction); setAiFixingCat(null) }

  // ===== КОМПЕТЕНЦИИ =====
  const handleSaveComp = (updated) => { onUpdateCompetency(updated); setEditingComp(null) }
  const handleDeleteCompConfirm = () => { onDeleteCompetency(deletingComp.id); setDeletingComp(null) }
  const handleAiFixCompSubmit = (instruction) => { onAiFixCompetency(editingComp?.id || aiFixingComp.id, instruction); setAiFixingComp(null) }
  const handleAddCompSubmit = (skill) => { onAddCompetency(addingComp.id, skill); setAddingComp(null) }

  return (
    <div className="mindmap">
      <div className="mindmap__header">
        <h2>🧠 Граф компетенций</h2>
        <div className="mindmap__header-right">
          <div className="mindmap__legend">
            <span>🟢 Beginner</span>
            <span>🟡 Intermediate</span>
            <span>🔴 Advanced</span>
          </div>
          <button className="mindmap__add-cat-btn" onClick={onAddCategory}>
            <Plus size={14} /> Категория
          </button>
        </div>
      </div>

      <div className="mindmap__tree">
        {categories?.map((cat, catIdx) => {
          const catComps = competencies?.filter(c => c.category_id === cat.id) || []

          return (
            <div key={cat.id} className="mindmap__category">
              <div
                className="mindmap__category-header"
                style={{ borderLeftColor: CAT_COLORS[catIdx % CAT_COLORS.length] }}
              >
                <span className="mindmap__category-emoji">{cat.emoji}</span>
                <span className="mindmap__category-name">{cat.name}</span>
                <span className="mindmap__category-count">{catComps.length}</span>

                <div className="mindmap__category-actions">
                  <button title="Редактировать категорию" onClick={() => setEditingCat(cat)}>
                    <Edit3 size={14} />
                  </button>
                  <button title="AI исправление" onClick={() => setAiFixingCat(cat)}>
                    <Sparkles size={14} />
                  </button>
                  <button title="Удалить категорию" onClick={() => setDeletingCat(cat)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <div className="mindmap__category-children">
                {catComps.map(comp => (
                  <CompetencyNode
                    key={comp.id}
                    comp={comp}
                    onEdit={handleEditSub}
                    onDelete={handleDeleteSubClick}
                    onAiFix={handleAiFixSubClick}
                    onAdd={handleAddSubClick}
                    onEditComp={setEditingComp}
                    onDeleteComp={setDeletingComp}
                    onAiFixComp={setAiFixingComp}
                  />
                ))}
                <button className="mindmap__add-btn" onClick={() => setAddingComp(cat)}>
                  <Plus size={14} /> Добавить компетенцию
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* ===== МОДАЛКИ ПОДКОМПЕТЕНЦИЙ ===== */}
      {editing && <NodeEditor sub={editing} onSave={handleSaveSub} onClose={() => setEditing(null)} />}
      {deleting && <ConfirmDialog title="Удаление подкомпетенции" message={`Удалить "${deleting.name}"? Это действие нельзя отменить.`} onConfirm={handleDeleteSubConfirm} onCancel={() => setDeleting(null)} />}
      {adding && <AddSubDialog competencyName={adding.skill} onAdd={handleAddSubSubmit} onClose={() => setAdding(null)} />}
      {aiFixing && <AiFixDialog subName={aiFixing.name} onSubmit={handleAiFixSubSubmit} onClose={() => setAiFixing(null)} />}

      {/* ===== МОДАЛКИ КАТЕГОРИЙ ===== */}
      {editingCat && <EditCategoryDialog category={editingCat} onSave={handleSaveCat} onClose={() => setEditingCat(null)} />}
      {deletingCat && <ConfirmDialog title="Удаление категории" message={`Удалить категорию "${deletingCat.name}" и все её компетенции? Это действие нельзя отменить.`} onConfirm={handleDeleteCatConfirm} onCancel={() => setDeletingCat(null)} />}
      {aiFixingCat && <AiFixDialog subName={`Категория: ${aiFixingCat.name}`} onSubmit={handleAiFixCatSubmit} onClose={() => setAiFixingCat(null)} />}

      {/* ===== МОДАЛКИ КОМПЕТЕНЦИЙ ===== */}
      {editingComp && <EditCompetencyDialog competency={editingComp} onSave={handleSaveComp} onClose={() => setEditingComp(null)} />}
      {deletingComp && <ConfirmDialog title="Удаление компетенции" message={`Удалить "${deletingComp.skill}" и все подкомпетенции? Это действие нельзя отменить.`} onConfirm={handleDeleteCompConfirm} onCancel={() => setDeletingComp(null)} />}
      {aiFixingComp && <AiFixDialog subName={`Компетенция: ${aiFixingComp.skill}`} onSubmit={handleAiFixCompSubmit} onClose={() => setAiFixingComp(null)} />}
      {addingComp && <AddCompetencyDialog categoryName={addingComp.name} onAdd={handleAddCompSubmit} onClose={() => setAddingComp(null)} />}
    </div>
  )
}