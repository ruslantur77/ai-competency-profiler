// frontend/src/components/MindMap.jsx
import React, { useState } from 'react'
import {
  ChevronRight, ChevronDown, Edit3, Trash2, Plus
} from 'lucide-react'
import NodeEditor from './NodeEditor'
import ConfirmDialog from './ConfirmDialog'
import AddSubDialog from './AddSubDialog'
import EditCategoryDialog from './EditCategoryDialog'
import EditCompetencyDialog from './EditCompetencyDialog'
import AddCompetencyDialog from './AddCompetencyDialog'
import './MindMap.css'

// ===== КОНСТАНТЫ =====
const LEVEL_CONFIG = {
  0: { bg: '#1e293b', border: '#475569', text: '#94a3b8', label: '⚪ No level' },
  1: { bg: '#dcfce7', border: '#22c55e', text: '#15803d', label: '🟢 Beginner' },
  2: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af', label: '🟡 Intermediate' },
  3: { bg: '#fef9c3', border: '#eab308', text: '#854d0e', label: '🟠 Upper-Int.' },
  4: { bg: '#fee2e2', border: '#ef4444', text: '#b91c1c', label: '🔴 Advanced' },
  5: { bg: '#fae8ff', border: '#a855f7', text: '#7e22ce', label: '⭐ Expert' },
}

const CAT_COLORS = [
  '#4CAF50', '#2196F3', '#FF9800', '#E91E63',
  '#9C27B0', '#00BCD4', '#FF5722', '#795548',
]

// ===== SUB COMPETENCY NODE =====
function SubCompetencyNode({ sub, onEdit, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const level = sub.target_level ?? 2
  const colors = LEVEL_CONFIG[level] || LEVEL_CONFIG[2]

  return (
    <div className="mindmap__sub-node" style={{ borderLeftColor: colors.border }}>
      <div className="mindmap__sub-header">
        <button
          className="mindmap__expand-btn"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        <span
          className="mindmap__level-badge"
          style={{ backgroundColor: colors.bg, color: colors.text }}
        >
          {colors.label}
        </span>

        <span className="mindmap__sub-name">{sub.sub_competency_name}</span>

        {sub.weight !== 1.0 && (
          <span className="mindmap__weight-badge">×{sub.weight}</span>
        )}

        {(onEdit || onDelete) && (
          <div className="mindmap__sub-actions">
            {onEdit && (
              <button title="Редактировать" onClick={() => onEdit(sub)}>
                <Edit3 size={14} />
              </button>
            )}
            {onDelete && (
              <button title="Удалить" onClick={() => onDelete(sub)}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        )}
      </div>

      {expanded && sub.sub_competency_description && (
        <div className="mindmap__sub-details">
          <p className="mindmap__sub-description">
            {sub.sub_competency_description}
          </p>
        </div>
      )}
    </div>
  )
}

// ===== COMPETENCY NODE =====
function CompetencyNode({
  comp, subNodes,
  onEditComp, onDeleteComp,
  onEditSub, onDeleteSub, onAddSub,
}) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="mindmap__comp-node">
      <div className="mindmap__comp-header">
        <div
          className="mindmap__comp-header-left"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <span className="mindmap__comp-name">{comp.competency_name}</span>
          {!comp.is_required && (
            <span className="mindmap__optional-badge">опц.</span>
          )}
          <span className="mindmap__comp-count">{subNodes.length}</span>
        </div>

        {(onEditComp || onDeleteComp) && (
          <div className="mindmap__comp-actions">
            {onEditComp && (
              <button title="Редактировать" onClick={() => onEditComp(comp)}>
                <Edit3 size={14} />
              </button>
            )}
            {onDeleteComp && (
              <button title="Удалить" onClick={() => onDeleteComp(comp)}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        )}
      </div>

      {expanded && (
        <div className="mindmap__comp-children">
          {subNodes.map(sub => (
            <SubCompetencyNode
              key={sub.sub_competency_id}
              sub={sub}
              onEdit={onEditSub}
              onDelete={onDeleteSub}
            />
          ))}
          {onAddSub && (
            <button
              className="mindmap__add-btn"
              onClick={() => onAddSub(comp)}
            >
              <Plus size={14} /> Добавить подкомпетенцию
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ===== MAIN MINDMAP =====
export default function MindMap({
  readOnly = false,
  categoryNodes,
  competencyNodes,
  subCompetencyNodes,
  onUpdateCategory,
  onDeleteCategory,
  onAddCategory,
  onUpdateCompetency,
  onDeleteCompetency,
  onAddCompetency,
  onUpdateSub,
  onDeleteSub,
  onAddSub,
}) {
  // Подкомпетенции
  const [editingSub, setEditingSub] = useState(null)
  const [deletingSub, setDeletingSub] = useState(null)
  const [addingSubComp, setAddingSubComp] = useState(null) // объект comp

  // Категории
  const [editingCat, setEditingCat] = useState(null)
  const [deletingCat, setDeletingCat] = useState(null)

  // Компетенции
  const [editingComp, setEditingComp] = useState(null)
  const [deletingComp, setDeletingComp] = useState(null)
  const [addingComp, setAddingComp] = useState(null) // объект cat

  // ===== HANDLERS — ПОДКОМПЕТЕНЦИИ =====
  const handleEditSubSave = (updated) => {
    onUpdateSub(updated)
    setEditingSub(null)
  }

  const handleDeleteSubConfirm = () => {
    onDeleteSub(deletingSub.sub_competency_id)
    setDeletingSub(null)
  }

  const handleAddSubSubmit = (newSub) => {
    onAddSub(addingSubComp.competency_id, newSub)
    setAddingSubComp(null)
  }

  // ===== HANDLERS — КАТЕГОРИИ =====
  const handleEditCatSave = (updated) => {
    onUpdateCategory({
      ...updated,
      category_id: updated.category_id || editingCat.category_id,
      category_name: updated.name || updated.category_name,
      category_emoji: updated.emoji || updated.category_emoji,
      category_description: updated.description || updated.category_description,
    })
    setEditingCat(null)
  }

  const handleDeleteCatConfirm = () => {
    onDeleteCategory(deletingCat.category_id)
    setDeletingCat(null)
  }

  // ===== HANDLERS — КОМПЕТЕНЦИИ =====
  const handleEditCompSave = (updated) => {
    onUpdateCompetency(updated)
    setEditingComp(null)
  }

  const handleDeleteCompConfirm = () => {
    onDeleteCompetency(deletingComp.competency_id)
    setDeletingComp(null)
  }

  const handleAddCompSubmit = (newComp) => {
    onAddCompetency(addingComp.category_id, newComp)
    setAddingComp(null)
  }

  return (
    <div className="mindmap">
      <div className="mindmap__header">
        <h2>🧠 Граф компетенций</h2>
        <div className="mindmap__header-right">
          <div className="mindmap__legend">
            {Object.entries(LEVEL_CONFIG).map(([lvl, cfg]) => (
              <span key={lvl}>{cfg.label}</span>
            ))}
          </div>
          {!readOnly && (
            <button className="mindmap__add-cat-btn" onClick={onAddCategory}>
              <Plus size={14} /> Категория
            </button>
          )}
        </div>
      </div>

      <div className="mindmap__tree">
        {categoryNodes.map((cat, catIdx) => {
          const catComps = competencyNodes.filter(
            c => c.category_id === cat.category_id
          )

          return (
            <div key={cat.category_id} className="mindmap__category">
              <div
                className="mindmap__category-header"
                style={{ borderLeftColor: CAT_COLORS[catIdx % CAT_COLORS.length] }}
              >
                <span className="mindmap__category-emoji">
                  {cat.category_emoji}
                </span>
                <span className="mindmap__category-name">
                  {cat.category_name}
                </span>
                <span className="mindmap__category-count">
                  {catComps.length}
                </span>

                {!readOnly && (
                  <div className="mindmap__category-actions">
                    <button
                      title="Редактировать"
                      onClick={() => setEditingCat(cat)}
                    >
                      <Edit3 size={14} />
                    </button>
                    <button
                      title="Удалить категорию"
                      onClick={() => setDeletingCat(cat)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                )}
              </div>

              <div className="mindmap__category-children">
                {catComps.map(comp => {
                  const compSubs = subCompetencyNodes.filter(
                    s => s.competency_id === comp.competency_id
                  )
                  return (
                    <CompetencyNode
                      key={comp.competency_id}
                      comp={comp}
                      subNodes={compSubs}
                      onEditComp={readOnly ? null : setEditingComp}
                      onDeleteComp={readOnly ? null : setDeletingComp}
                      onEditSub={readOnly ? null : setEditingSub}
                      onDeleteSub={readOnly ? null : setDeletingSub}
                      onAddSub={readOnly ? null : setAddingSubComp}
                    />
                  )
                })}
                {!readOnly && (
                  <button
                    className="mindmap__add-btn"
                    onClick={() => setAddingComp(cat)}
                  >
                    <Plus size={14} /> Добавить компетенцию
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* ===== МОДАЛКИ ПОДКОМПЕТЕНЦИЙ ===== */}
      {editingSub && (
        <NodeEditor
          sub={editingSub}
          onSave={handleEditSubSave}
          onClose={() => setEditingSub(null)}
        />
      )}
      {deletingSub && (
        <ConfirmDialog
          title="Удаление подкомпетенции"
          message={`Удалить "${deletingSub.sub_competency_name}"? Это действие нельзя отменить.`}
          onConfirm={handleDeleteSubConfirm}
          onCancel={() => setDeletingSub(null)}
        />
      )}
      {addingSubComp && (
        <AddSubDialog
          competencyName={addingSubComp.competency_name}
          onAdd={handleAddSubSubmit}
          onClose={() => setAddingSubComp(null)}
        />
      )}

      {/* ===== МОДАЛКИ КАТЕГОРИЙ ===== */}
      {editingCat && (
        <EditCategoryDialog
          category={{
            ...editingCat,
            name: editingCat.category_name,
            emoji: editingCat.category_emoji,
            description: editingCat.category_description,
          }}
          onSave={handleEditCatSave}
          onClose={() => setEditingCat(null)}
        />
      )}
      {deletingCat && (
        <ConfirmDialog
          title="Удаление категории"
          message={`Удалить категорию "${deletingCat.category_name}" и все её компетенции?`}
          onConfirm={handleDeleteCatConfirm}
          onCancel={() => setDeletingCat(null)}
        />
      )}

      {/* ===== МОДАЛКИ КОМПЕТЕНЦИЙ ===== */}
      {editingComp && (
        <EditCompetencyDialog
          competency={editingComp}
          onSave={handleEditCompSave}
          onClose={() => setEditingComp(null)}
        />
      )}
      {deletingComp && (
        <ConfirmDialog
          title="Удаление компетенции"
          message={`Удалить "${deletingComp.competency_name}" и все подкомпетенции?`}
          onConfirm={handleDeleteCompConfirm}
          onCancel={() => setDeletingComp(null)}
        />
      )}
      {addingComp && (
        <AddCompetencyDialog
          categoryName={addingComp.category_name}
          onAdd={handleAddCompSubmit}
          onClose={() => setAddingComp(null)}
        />
      )}
    </div>
  )
}
