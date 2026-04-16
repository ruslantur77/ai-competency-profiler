const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export const COMPETENCY_LEVEL_OPTIONS = [
  { value: 0, label: '⚪ None' },
  { value: 1, label: '🟢 Novice' },
  { value: 2, label: '🔵 Beginner' },
  { value: 3, label: '🟡 Intermediate' },
  { value: 4, label: '🟠 Advanced' },
  { value: 5, label: '⭐ Expert' },
]

export const normalizeTargetLevel = (value) => {
  const level = Number.parseInt(value, 10)
  if (!Number.isFinite(level)) return 2
  return Math.min(5, Math.max(0, level))
}

export const normalizeWeight = (value) => {
  const weight = Number.parseFloat(value)
  if (!Number.isFinite(weight)) return 1.0
  return Math.min(1.0, Math.max(0.0, Number(weight.toFixed(3))))
}

export const isUuidLike = (value) => UUID_V4_RE.test(String(value || ''))

const assertRequiredString = (value, fieldName) => {
  if (!String(value || '').trim()) {
    throw new Error(`Поле ${fieldName} обязательно для сохранения графа`)
  }
}

const assertRequiredId = (value, fieldName) => {
  if (!value) {
    throw new Error(`Поле ${fieldName} обязательно для сохранения графа`)
  }
}

export const nextPosition = (items, predicate = () => true) => {
  const scoped = items.filter(predicate)
  if (scoped.length === 0) return 0
  const maxPos = Math.max(...scoped.map(item => Number(item.position ?? 0)))
  return Number.isFinite(maxPos) ? maxPos + 1 : scoped.length
}

export const buildVacancyGraphDTO = (categoryNodes, competencyNodes, subCompetencyNodes) => ({
  categories: categoryNodes.map(cat => {
    assertRequiredId(cat.category_id, 'category_id')
    assertRequiredString(cat.category_name, 'category_name')

    return {
      id: cat.category_id,
      name: String(cat.category_name).trim(),
      description: cat.category_description || '',
      emoji: cat.category_emoji || '',
      competencies: competencyNodes
        .filter(comp => comp.category_id === cat.category_id)
        .map(comp => {
          assertRequiredId(comp.competency_id, 'competency_id')
          assertRequiredString(comp.competency_name, 'competency_name')

          return {
            id: comp.competency_id,
            category_id: cat.category_id,
            name: String(comp.competency_name).trim(),
            description: comp.competency_description || '',
            is_required: comp.is_required ?? true,
            sub_competencies: subCompetencyNodes
              .filter(sub => sub.competency_id === comp.competency_id)
              .map(sub => {
                assertRequiredId(sub.sub_competency_id, 'sub_competency_id')
                assertRequiredString(sub.sub_competency_name, 'sub_competency_name')
                return {
                  id: sub.sub_competency_id,
                  name: String(sub.sub_competency_name).trim(),
                  description: sub.sub_competency_description || '',
                  target_level: normalizeTargetLevel(sub.target_level),
                  weight: normalizeWeight(sub.weight),
                }
              }),
          }
        }),
    }
  }),
})
