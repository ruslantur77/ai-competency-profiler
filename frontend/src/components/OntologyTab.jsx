import React from 'react';
import AsyncState from './AsyncState';
import EditCategoryDialog from './EditCategoryDialog';
import AddCompetencyDialog from './AddCompetencyDialog';
import EditCompetencyDialog from './EditCompetencyDialog';
import AddSubDialog from './AddSubDialog';
import NodeEditor from './NodeEditor';
import ConfirmDialog from './ConfirmDialog';
import OntologyToolbar from './ontology/OntologyToolbar';
import OntologyTree from './ontology/OntologyTree';
import OntologyDetails from './ontology/OntologyDetails';
import { ENTITY_TYPE, useOntologyData } from '../hooks/useOntologyData';
import { useOntologyCrud } from '../hooks/useOntologyCrud';
import './OntologyTab.css';

export default function OntologyTab({ notify }) {
  const {
    loading,
    refreshing,
    categories,
    subCompetencies,
    selected,
    selectedDetails,
    expandedCategories,
    expandedCompetencies,
    categoryById,
    competencyById,
    setSelected,
    fetchOntology,
    refreshAndPreserveSelection,
    toggleCategory,
    toggleCompetency,
    resetSelection,
  } = useOntologyData({ notify });

  const {
    editingCategory,
    addingCompetencyForCategory,
    editingCompetency,
    addingSubForCompetency,
    editingSubCompetency,
    confirmDelete,
    setEditingCategory,
    setAddingCompetencyForCategory,
    setEditingCompetency,
    setAddingSubForCompetency,
    setEditingSubCompetency,
    setConfirmDelete,
    handleCreateCategory,
    handleUpdateCategory,
    handleCreateCompetency,
    handleUpdateCompetency,
    handleCreateSubCompetency,
    handleUpdateSubCompetency,
    handleDeleteEntity,
    openCreateCategory,
    openEditSelected,
    openCreateForSelection,
    openDeleteSelected,
  } = useOntologyCrud({
    notify,
    selected,
    categoryById,
    competencyById,
    subCompetencies,
    refreshAndPreserveSelection,
    resetSelection,
  });

  const handleSelect = (type, id) => {
    setSelected({ type, id });
  };

  if (loading) {
    return <AsyncState kind="loading" title="Загрузка онтологии..." />;
  }

  return (
    <div className="ontology">
      <OntologyToolbar
        selected={selected}
        refreshing={refreshing}
        onRefresh={() => fetchOntology({ silent: true })}
        onCreateCategory={openCreateCategory}
        onCreateForSelection={openCreateForSelection}
        onEditSelected={openEditSelected}
        onDeleteSelected={openDeleteSelected}
        entityType={ENTITY_TYPE}
      />

      <div className="ontology__content">
        <OntologyTree
          categories={categories}
          selected={selected}
          entityType={ENTITY_TYPE}
          expandedCategories={expandedCategories}
          expandedCompetencies={expandedCompetencies}
          onSelect={handleSelect}
          onToggleCategory={toggleCategory}
          onToggleCompetency={toggleCompetency}
        />

        <OntologyDetails
          selected={selected}
          selectedDetails={selectedDetails}
          entityType={ENTITY_TYPE}
        />
      </div>

      {editingCategory && (
        <EditCategoryDialog
          category={editingCategory.payload}
          onSave={editingCategory.mode === 'create' ? handleCreateCategory : handleUpdateCategory}
          onClose={() => setEditingCategory(null)}
          title={
            editingCategory.mode === 'create'
              ? '➕ Добавить категорию'
              : '✏️ Редактировать категорию'
          }
        />
      )}

      {addingCompetencyForCategory && (
        <AddCompetencyDialog
          categoryName={addingCompetencyForCategory.name}
          onAdd={handleCreateCompetency}
          onClose={() => setAddingCompetencyForCategory(null)}
        />
      )}

      {editingCompetency && (
        <EditCompetencyDialog
          competency={editingCompetency}
          onSave={handleUpdateCompetency}
          onClose={() => setEditingCompetency(null)}
        />
      )}

      {addingSubForCompetency && (
        <AddSubDialog
          competencyName={addingSubForCompetency.name}
          onAdd={handleCreateSubCompetency}
          onClose={() => setAddingSubForCompetency(null)}
        />
      )}

      {editingSubCompetency && (
        <NodeEditor
          sub={editingSubCompetency}
          onSave={handleUpdateSubCompetency}
          onClose={() => setEditingSubCompetency(null)}
        />
      )}

      {confirmDelete && (
        <ConfirmDialog
          title={confirmDelete.title}
          message={confirmDelete.message}
          onConfirm={handleDeleteEntity}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
}
