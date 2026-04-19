const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export const COMPETENCY_LEVEL_OPTIONS = [
  { value: 0, label: '⚪ No level' },
  { value: 1, label: '🟢 Beginner' },
  { value: 2, label: '🟡 Intermediate' },
  { value: 3, label: '🟠 Upper-Intermediate' },
  { value: 4, label: '🔴 Advanced' },
  { value: 5, label: '⭐ Expert' },
];

const GRAPH_NODE_MODE = {
  EXISTING: 'existing',
  NEW: 'new',
};

export const normalizeTargetLevel = (value) => {
  const level = Number.parseInt(value, 10);
  if (!Number.isFinite(level)) return 2;
  return Math.min(5, Math.max(0, level));
};

export const normalizeWeight = (value) => {
  const weight = Number.parseFloat(value);
  if (!Number.isFinite(weight)) return 1.0;
  return Math.min(1.0, Math.max(0.0, Number(weight.toFixed(3))));
};

export const isUuidLike = (value) => UUID_V4_RE.test(String(value || ''));

const assertRequiredString = (value, fieldName) => {
  if (!String(value || '').trim()) {
    throw new Error(`Поле ${fieldName} обязательно для сохранения графа`);
  }
};

const assertRequiredId = (value, fieldName) => {
  if (!value) {
    throw new Error(`Поле ${fieldName} обязательно для сохранения графа`);
  }
};

const pickTempId = (...values) => {
  const found = values.find((value) => isUuidLike(value));
  return found || crypto.randomUUID();
};

const isPersisted = (node) => node?._persisted === true;

const buildSubCompetencyInput = (sub) => {
  const target_level = normalizeTargetLevel(sub.target_level);
  const weight = normalizeWeight(sub.weight);

  if (isPersisted(sub)) {
    assertRequiredId(sub.sub_competency_id, 'sub_competency_id');
    return {
      mode: GRAPH_NODE_MODE.EXISTING,
      id: sub.sub_competency_id,
      target_level,
      weight,
    };
  }

  assertRequiredString(sub.sub_competency_name, 'sub_competency_name');
  return {
    mode: GRAPH_NODE_MODE.NEW,
    temp_id: pickTempId(sub.sub_competency_id, sub.id),
    name: String(sub.sub_competency_name).trim(),
    description: sub.sub_competency_description || '',
    target_level,
    weight,
  };
};

const buildCompetencyInput = (comp, subCompetencyNodes) => {
  const sub_competencies = subCompetencyNodes
    .filter((sub) => sub.competency_id === comp.competency_id)
    .map(buildSubCompetencyInput);

  if (isPersisted(comp)) {
    assertRequiredId(comp.competency_id, 'competency_id');
    return {
      mode: GRAPH_NODE_MODE.EXISTING,
      id: comp.competency_id,
      is_required: comp.is_required ?? true,
      sub_competencies,
    };
  }

  assertRequiredString(comp.competency_name, 'competency_name');
  return {
    mode: GRAPH_NODE_MODE.NEW,
    temp_id: pickTempId(comp.competency_id, comp.id),
    name: String(comp.competency_name).trim(),
    description: comp.competency_description || '',
    is_required: comp.is_required ?? true,
    sub_competencies,
  };
};

const buildCategoryInput = (cat, competencyNodes, subCompetencyNodes) => {
  const competencies = competencyNodes
    .filter((comp) => comp.category_id === cat.category_id)
    .map((comp) => buildCompetencyInput(comp, subCompetencyNodes));

  if (isPersisted(cat)) {
    assertRequiredId(cat.category_id, 'category_id');
    return {
      mode: GRAPH_NODE_MODE.EXISTING,
      id: cat.category_id,
      competencies,
    };
  }

  assertRequiredString(cat.category_name, 'category_name');
  return {
    mode: GRAPH_NODE_MODE.NEW,
    temp_id: pickTempId(cat.category_id, cat.id),
    name: String(cat.category_name).trim(),
    description: cat.category_description || '',
    emoji: cat.category_emoji || '',
    competencies,
  };
};

const buildGraphUpdateDTO = (categoryNodes, competencyNodes, subCompetencyNodes) => ({
  categories: categoryNodes.map((cat) =>
    buildCategoryInput(cat, competencyNodes, subCompetencyNodes)
  ),
});

export const markPersistedGraphNodes = (nodes = []) =>
  nodes.map((node) => ({ ...node, _persisted: true }));

export const buildVacancyGraphDTO = (categoryNodes, competencyNodes, subCompetencyNodes) =>
  buildGraphUpdateDTO(categoryNodes, competencyNodes, subCompetencyNodes);

export const buildTaskGraphDTO = (categoryNodes, competencyNodes, subCompetencyNodes) =>
  buildGraphUpdateDTO(categoryNodes, competencyNodes, subCompetencyNodes);

export const nextPosition = (items, predicate = () => true) => {
  const scoped = items.filter(predicate);
  if (scoped.length === 0) return 0;
  const maxPos = Math.max(...scoped.map((item) => Number(item.position ?? 0)));
  return Number.isFinite(maxPos) ? maxPos + 1 : scoped.length;
};
