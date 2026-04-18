import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, Save, CheckCircle2, X } from 'lucide-react';
import AddCategoryDialog from './AddCategoryDialog';
import MindMap from './MindMap';
import AsyncState from './AsyncState';
import { listCategories } from '../api/ontology';
import { finalizeTaskGraph, getTask, updateTaskGraph, updateTaskStatus } from '../api/tasks';
import { getErrorMessage } from '../api/errors';
import {
  buildTaskGraphDTO,
  isUuidLike,
  markPersistedGraphNodes,
  nextPosition,
  normalizeTargetLevel,
  normalizeWeight,
} from '../domain/competencyGraph';
import './TaskGraphDialog.css';

const TASK_STATUS_LABELS = {
  pending: 'Pending',
  draft: 'Draft',
  ready: 'Ready',
  failed: 'Failed',
};

const tempId = () => crypto.randomUUID();

export default function TaskGraphDialog({ taskId, notify, onClose, onUpdated }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [statusSaving, setStatusSaving] = useState(false);
  const [task, setTask] = useState(null);
  const [ontologyCategories, setOntologyCategories] = useState([]);

  const [categoryNodes, setCategoryNodes] = useState([]);
  const [competencyNodes, setCompetencyNodes] = useState([]);
  const [subCompetencyNodes, setSubCompetencyNodes] = useState([]);
  const [originalNodes, setOriginalNodes] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const [addingCategory, setAddingCategory] = useState(false);

  const ontologyCategoryOptions = useMemo(
    () =>
      ontologyCategories.map((category) => ({
        id: category.id,
        name: category.name,
        emoji: category.emoji || '',
        description: category.description || '',
      })),
    [ontologyCategories]
  );

  const ontologyCompetencyOptions = useMemo(
    () =>
      ontologyCategories.flatMap((category) =>
        (category.competencies || []).map((competency) => ({
          id: competency.id,
          category_id: competency.category_id,
          name: competency.name,
          description: competency.description || '',
        }))
      ),
    [ontologyCategories]
  );

  const ontologySubCompetencyOptions = useMemo(
    () =>
      ontologyCategories.flatMap((category) =>
        (category.competencies || []).flatMap((competency) =>
          (competency.sub_competencies || []).map((sub) => ({
            id: sub.id,
            competency_id: sub.competency_id,
            name: sub.name,
            description: sub.description || '',
            target_level: sub.target_level,
            weight: sub.weight,
          }))
        )
      ),
    [ontologyCategories]
  );

  const applyTask = useCallback((data) => {
    const cats = markPersistedGraphNodes(data.category_nodes || []);
    const comps = markPersistedGraphNodes(data.competency_nodes || []);
    const subs = markPersistedGraphNodes(data.sub_competency_nodes || []);
    setTask(data);
    setCategoryNodes(cats);
    setCompetencyNodes(comps);
    setSubCompetencyNodes(subs);
    setOriginalNodes({ cats, comps, subs });
    setIsDirty(false);
  }, []);

  const loadTask = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await getTask(taskId);
      applyTask(data);
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка загрузки задачи' }), 'error');
      onClose();
    } finally {
      setLoading(false);
    }
  }, [taskId, applyTask, notify, onClose]);

  useEffect(() => {
    loadTask();
  }, [loadTask]);

  useEffect(() => {
    const loadOntology = async () => {
      try {
        const { data } = await listCategories();
        setOntologyCategories(Array.isArray(data) ? data : []);
      } catch (error) {
        notify(getErrorMessage(error, { fallback: 'Ошибка загрузки онтологии' }), 'error');
      }
    };
    loadOntology();
  }, [notify]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const dto = buildTaskGraphDTO(categoryNodes, competencyNodes, subCompetencyNodes);
      const { data } = await updateTaskGraph(taskId, dto);
      applyTask(data);
      notify('Граф задачи сохранен');
      onUpdated();
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка сохранения графа задачи' }), 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleFinalize = async () => {
    setFinalizing(true);
    try {
      const { data } = await finalizeTaskGraph(taskId);
      applyTask(data);
      notify('Граф задачи финализирован');
      onUpdated();
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка финализации графа задачи' }), 'error');
    } finally {
      setFinalizing(false);
    }
  };

  const handleStatusChange = async (event) => {
    const nextStatus = event.target.value;
    if (!nextStatus || nextStatus === task?.status) return;

    setStatusSaving(true);
    try {
      const { data } = await updateTaskStatus(taskId, nextStatus);
      applyTask(data);
      notify(`Статус задачи обновлен: ${TASK_STATUS_LABELS[data.status] || data.status}`);
      onUpdated();
    } catch (error) {
      notify(getErrorMessage(error, { fallback: 'Ошибка изменения статуса задачи' }), 'error');
    } finally {
      setStatusSaving(false);
    }
  };

  const handleDiscard = () => {
    if (!originalNodes) return;
    setCategoryNodes(originalNodes.cats);
    setCompetencyNodes(originalNodes.comps);
    setSubCompetencyNodes(originalNodes.subs);
    setIsDirty(false);
  };

  const markDirty = () => setIsDirty(true);

  const handleUpdateCategory = (updated) => {
    setCategoryNodes((prev) =>
      prev.map((c) => (c.category_id === updated.category_id ? { ...c, ...updated } : c))
    );
    markDirty();
  };

  const handleDeleteCategory = (categoryId) => {
    const removedCompIds = competencyNodes
      .filter((c) => c.category_id === categoryId)
      .map((c) => c.competency_id);
    setCategoryNodes((prev) => prev.filter((c) => c.category_id !== categoryId));
    setCompetencyNodes((prev) => prev.filter((c) => c.category_id !== categoryId));
    setSubCompetencyNodes((prev) => prev.filter((s) => !removedCompIds.includes(s.competency_id)));
    markDirty();
  };

  const handleAddCategorySubmit = (newCat) => {
    if (newCat.mode === 'existing') {
      const exists = categoryNodes.some((item) => item.category_id === newCat.id);
      if (exists) {
        notify('Категория уже добавлена в граф', 'error');
        return;
      }
      setCategoryNodes((prev) => [
        ...prev,
        {
          id: tempId(),
          task_id: taskId,
          category_id: newCat.id,
          category_name: newCat.name,
          category_emoji: newCat.emoji || '',
          category_description: newCat.description || '',
          position: nextPosition(prev),
          _persisted: true,
        },
      ]);
      setAddingCategory(false);
      markDirty();
      return;
    }

    const id = tempId();
    setCategoryNodes((prev) => [
      ...prev,
      {
        id,
        task_id: taskId,
        category_id: id,
        category_name: newCat.name,
        category_emoji: newCat.emoji || '',
        category_description: newCat.description || '',
        position: nextPosition(prev),
        _persisted: false,
      },
    ]);
    setAddingCategory(false);
    markDirty();
  };

  const handleUpdateCompetency = (updated) => {
    setCompetencyNodes((prev) =>
      prev.map((c) => (c.competency_id === updated.competency_id ? { ...c, ...updated } : c))
    );
    markDirty();
  };

  const handleDeleteCompetency = (competencyId) => {
    setCompetencyNodes((prev) => prev.filter((c) => c.competency_id !== competencyId));
    setSubCompetencyNodes((prev) => prev.filter((s) => s.competency_id !== competencyId));
    markDirty();
  };

  const handleAddCompetency = (categoryId, newComp) => {
    if (newComp.mode === 'existing') {
      const exists = competencyNodes.some((item) => item.competency_id === newComp.id);
      if (exists) {
        notify('Компетенция уже добавлена в граф', 'error');
        return;
      }
      setCompetencyNodes((prev) => [
        ...prev,
        {
          id: tempId(),
          task_id: taskId,
          competency_id: newComp.id,
          category_id: categoryId,
          competency_name: newComp.name,
          competency_description: newComp.description || '',
          is_required: newComp.is_required ?? true,
          position: nextPosition(prev, (c) => c.category_id === categoryId),
          _persisted: true,
        },
      ]);
      markDirty();
      return;
    }

    const id = tempId();
    setCompetencyNodes((prev) => [
      ...prev,
      {
        id,
        task_id: taskId,
        competency_id: id,
        category_id: categoryId,
        competency_name: newComp.name,
        competency_description: newComp.description || '',
        is_required: newComp.is_required ?? true,
        position: nextPosition(prev, (c) => c.category_id === categoryId),
        _persisted: false,
      },
    ]);
    markDirty();
  };

  const handleUpdateSub = (updatedSub) => {
    setSubCompetencyNodes((prev) =>
      prev.map((s) =>
        s.sub_competency_id === updatedSub.sub_competency_id
          ? {
              ...s,
              ...updatedSub,
              target_level: normalizeTargetLevel(updatedSub.target_level),
              weight: normalizeWeight(updatedSub.weight),
            }
          : s
      )
    );
    markDirty();
  };

  const handleDeleteSub = (subCompetencyId) => {
    setSubCompetencyNodes((prev) => prev.filter((s) => s.sub_competency_id !== subCompetencyId));
    markDirty();
  };

  const handleAddSub = (competencyId, newSub) => {
    if (newSub.mode === 'existing') {
      const exists = subCompetencyNodes.some((item) => item.sub_competency_id === newSub.id);
      if (exists) {
        notify('Подкомпетенция уже добавлена в граф', 'error');
        return;
      }
      setSubCompetencyNodes((prev) => [
        ...prev,
        {
          id: tempId(),
          task_id: taskId,
          sub_competency_id: newSub.id,
          competency_id: competencyId,
          sub_competency_name: newSub.name,
          sub_competency_description: newSub.description || '',
          target_level: normalizeTargetLevel(newSub.target_level),
          weight: normalizeWeight(newSub.weight),
          position: nextPosition(prev, (s) => s.competency_id === competencyId),
          _persisted: true,
        },
      ]);
      markDirty();
      return;
    }

    const rawId = newSub.id || tempId();
    const id = isUuidLike(rawId) ? rawId : tempId();
    setSubCompetencyNodes((prev) => [
      ...prev,
      {
        id,
        task_id: taskId,
        sub_competency_id: id,
        competency_id: competencyId,
        sub_competency_name: newSub.name,
        sub_competency_description: newSub.description || '',
        target_level: normalizeTargetLevel(newSub.target_level),
        weight: normalizeWeight(newSub.weight),
        position: nextPosition(prev, (s) => s.competency_id === competencyId),
        _persisted: false,
      },
    ]);
    markDirty();
  };

  return (
    <div className="task-graph-dialog__overlay" onClick={onClose}>
      <div className="task-graph-dialog" onClick={(event) => event.stopPropagation()}>
        <div className="task-graph-dialog__header">
          <div>
            <h3>{task?.title || 'Граф задачи'}</h3>
            <p>ID: {task?.external_id || '—'}</p>
          </div>
          <button className="task-graph-dialog__close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {loading ? (
          <AsyncState kind="loading" title="Загрузка графа задачи..." />
        ) : (
          <>
            <div className="task-graph-dialog__actions">
              <label>
                Статус
                <select
                  value={task?.status || 'pending'}
                  onChange={handleStatusChange}
                  disabled={statusSaving}
                >
                  {Object.keys(TASK_STATUS_LABELS).map((status) => (
                    <option key={status} value={status}>
                      {TASK_STATUS_LABELS[status]}
                    </option>
                  ))}
                </select>
              </label>

              <div className="task-graph-dialog__buttons">
                {isDirty && (
                  <button className="btn-secondary" onClick={handleDiscard} disabled={saving}>
                    Отменить
                  </button>
                )}
                <button className="btn-primary" onClick={handleSave} disabled={saving || !isDirty}>
                  {saving ? (
                    <>
                      <Loader2 size={16} className="spin" /> Сохранение...
                    </>
                  ) : (
                    <>
                      <Save size={16} /> Сохранить граф
                    </>
                  )}
                </button>
                <button
                  className="btn-secondary"
                  onClick={handleFinalize}
                  disabled={finalizing || isDirty}
                  title={isDirty ? 'Сначала сохраните изменения' : 'Перевести граф в ready'}
                >
                  {finalizing ? (
                    <>
                      <Loader2 size={16} className="spin" /> Финализация...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={16} /> Finalize
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="task-graph-dialog__body">
              <MindMap
                categoryNodes={categoryNodes}
                competencyNodes={competencyNodes}
                subCompetencyNodes={subCompetencyNodes}
                ontologyCompetencyOptions={ontologyCompetencyOptions}
                ontologySubCompetencyOptions={ontologySubCompetencyOptions}
                onUpdateCategory={handleUpdateCategory}
                onDeleteCategory={handleDeleteCategory}
                onAddCategory={() => setAddingCategory(true)}
                onUpdateCompetency={handleUpdateCompetency}
                onDeleteCompetency={handleDeleteCompetency}
                onAddCompetency={handleAddCompetency}
                onUpdateSub={handleUpdateSub}
                onDeleteSub={handleDeleteSub}
                onAddSub={handleAddSub}
              />
            </div>
          </>
        )}

        {addingCategory && (
          <AddCategoryDialog
            existingOptions={ontologyCategoryOptions}
            onAdd={handleAddCategorySubmit}
            onClose={() => setAddingCategory(false)}
          />
        )}
      </div>
    </div>
  );
}
