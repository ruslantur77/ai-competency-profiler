import { describe, it, expect } from 'vitest';
import {
  normalizeTargetLevel,
  normalizeWeight,
  isUuidLike,
  buildVacancyGraphDTO,
  buildTaskGraphDTO,
  markPersistedGraphNodes,
  nextPosition,
  COMPETENCY_LEVEL_OPTIONS,
} from './competencyGraph.js';

// normalizeTargetLevel

describe('normalizeTargetLevel', () => {
  it('возвращает корректный уровень для валидных значений', () => {
    expect(normalizeTargetLevel(0)).toBe(0);
    expect(normalizeTargetLevel(1)).toBe(1);
    expect(normalizeTargetLevel(3)).toBe(3);
    expect(normalizeTargetLevel(5)).toBe(5);
  });

  it('клампит значения выше 5', () => {
    expect(normalizeTargetLevel(6)).toBe(5);
    expect(normalizeTargetLevel(100)).toBe(5);
  });

  it('клампит отрицательные значения до 0', () => {
    expect(normalizeTargetLevel(-1)).toBe(0);
    expect(normalizeTargetLevel(-100)).toBe(0);
  });

  it('возвращает 2 для невалидных значений', () => {
    expect(normalizeTargetLevel(null)).toBe(2);
    expect(normalizeTargetLevel(undefined)).toBe(2);
    expect(normalizeTargetLevel('abc')).toBe(2);
    expect(normalizeTargetLevel(NaN)).toBe(2);
    expect(normalizeTargetLevel('')).toBe(2);
  });

  it('парсит строковые числа', () => {
    expect(normalizeTargetLevel('3')).toBe(3);
    expect(normalizeTargetLevel('0')).toBe(0);
    expect(normalizeTargetLevel('5')).toBe(5);
  });

  it('граничные значения 0 и 5', () => {
    expect(normalizeTargetLevel(0)).toBe(0);
    expect(normalizeTargetLevel(5)).toBe(5);
  });
});

// normalizeWeight 

describe('normalizeWeight', () => {
  it('возвращает корректный вес для валидных значений', () => {
    expect(normalizeWeight(0)).toBe(0);
    expect(normalizeWeight(1)).toBe(1);
    expect(normalizeWeight(0.5)).toBe(0.5);
  });

  it('клампит значения выше 1.0', () => {
    expect(normalizeWeight(1.5)).toBe(1.0);
    expect(normalizeWeight(100)).toBe(1.0);
  });

  it('клампит отрицательные значения до 0', () => {
    expect(normalizeWeight(-0.5)).toBe(0);
    expect(normalizeWeight(-100)).toBe(0);
  });

  it('возвращает 1.0 для невалидных значений', () => {
    expect(normalizeWeight(null)).toBe(1.0);
    expect(normalizeWeight(undefined)).toBe(1.0);
    expect(normalizeWeight('abc')).toBe(1.0);
    expect(normalizeWeight(NaN)).toBe(1.0);
    expect(normalizeWeight('')).toBe(1.0);
  });

  it('парсит строковые числа', () => {
    expect(normalizeWeight('0.5')).toBe(0.5);
    expect(normalizeWeight('1')).toBe(1.0);
    expect(normalizeWeight('0')).toBe(0);
  });

  it('округляет до 3 знаков после запятой', () => {
    expect(normalizeWeight(0.1234)).toBe(0.123);
    expect(normalizeWeight(0.9999)).toBe(1.0);
    expect(normalizeWeight(0.0005)).toBe(0.001);
  });

  it('граничные значения 0 и 1', () => {
    expect(normalizeWeight(0)).toBe(0);
    expect(normalizeWeight(1)).toBe(1);
  });
});

// isUuidLike 

describe('isUuidLike', () => {
  it('возвращает true для валидного UUID v4', () => {
    expect(isUuidLike('550e8400-e29b-41d4-a716-446655440000')).toBe(true);
    expect(isUuidLike('123e4567-e89b-12d3-a456-426614174000')).toBe(true);
  });

  it('возвращает true для UUID в верхнем регистре', () => {
    expect(isUuidLike('550E8400-E29B-41D4-A716-446655440000')).toBe(true);
  });

  it('возвращает false для пустой строки', () => {
    expect(isUuidLike('')).toBe(false);
  });

  it('возвращает false для null и undefined', () => {
    expect(isUuidLike(null)).toBe(false);
    expect(isUuidLike(undefined)).toBe(false);
  });

  it('возвращает false для произвольной строки', () => {
    expect(isUuidLike('not-a-uuid')).toBe(false);
    expect(isUuidLike('123')).toBe(false);
    expect(isUuidLike('competency-name')).toBe(false);
  });

  it('возвращает false для uuid без дефисов', () => {
    expect(isUuidLike('550e8400e29b41d4a716446655440000')).toBe(false);
  });
});

// markPersistedGraphNodes

describe('markPersistedGraphNodes', () => {
  it('добавляет _persisted: true каждому узлу', () => {
    const nodes = [{ id: 1 }, { id: 2 }];
    const result = markPersistedGraphNodes(nodes);
    result.forEach((node) => {
      expect(node._persisted).toBe(true);
    });
  });

  it('не мутирует оригинальные объекты', () => {
    const nodes = [{ id: 1 }];
    const result = markPersistedGraphNodes(nodes);
    expect(nodes[0]._persisted).toBeUndefined();
    expect(result[0]._persisted).toBe(true);
  });

  it('возвращает пустой массив для пустого входа', () => {
    expect(markPersistedGraphNodes([])).toEqual([]);
  });

  it('возвращает пустой массив если аргумент не передан', () => {
    expect(markPersistedGraphNodes()).toEqual([]);
  });
});

// nextPosition 

describe('nextPosition', () => {
  it('возвращает 0 для пустого массива', () => {
    expect(nextPosition([])).toBe(0);
  });

  it('возвращает max + 1', () => {
    const items = [{ position: 0 }, { position: 1 }, { position: 2 }];
    expect(nextPosition(items)).toBe(3);
  });

  it('работает с одним элементом', () => {
    expect(nextPosition([{ position: 5 }])).toBe(6);
  });

  it('работает если position не задан (undefined)', () => {
    const items = [{ id: 1 }, { id: 2 }];
    expect(nextPosition(items)).toBe(1);
  });

  it('применяет predicate — фильтрует по условию', () => {
    const items = [
      { position: 0, category_id: 'cat-1' },
      { position: 1, category_id: 'cat-1' },
      { position: 5, category_id: 'cat-2' },
    ];
    const result = nextPosition(items, (item) => item.category_id === 'cat-1');
    expect(result).toBe(2);
  });

  it('возвращает 0 если predicate не пропускает ни одного элемента', () => {
    const items = [{ position: 3, category_id: 'cat-1' }];
    const result = nextPosition(items, (item) => item.category_id === 'cat-2');
    expect(result).toBe(0);
  });
});

// buildVacancyGraphDTO 

describe('buildVacancyGraphDTO', () => {
  const VALID_UUID = '550e8400-e29b-41d4-a716-446655440000';
  const VALID_UUID_2 = '123e4567-e89b-12d3-a456-426614174000';
  const VALID_UUID_3 = '987fbc97-4bed-5078-af07-9141ba07c9f3';

  it('строит DTO для persisted категории с persisted компетенцией и sub', () => {
    const categories = [
      { category_id: VALID_UUID, _persisted: true },
    ];
    const competencies = [
      { competency_id: VALID_UUID_2, category_id: VALID_UUID, _persisted: true },
    ];
    const subs = [
      {
        sub_competency_id: VALID_UUID_3,
        competency_id: VALID_UUID_2,
        _persisted: true,
        target_level: 3,
        weight: 0.8,
      },
    ];

    const dto = buildVacancyGraphDTO(categories, competencies, subs);

    expect(dto.categories).toHaveLength(1);
    expect(dto.categories[0].mode).toBe('existing');
    expect(dto.categories[0].id).toBe(VALID_UUID);

    const comp = dto.categories[0].competencies[0];
    expect(comp.mode).toBe('existing');
    expect(comp.id).toBe(VALID_UUID_2);

    const sub = comp.sub_competencies[0];
    expect(sub.mode).toBe('existing');
    expect(sub.id).toBe(VALID_UUID_3);
    expect(sub.target_level).toBe(3);
    expect(sub.weight).toBe(0.8);
  });

  it('строит DTO для новой категории с новой компетенцией и sub', () => {
    const tempCatId = VALID_UUID;
    const tempCompId = VALID_UUID_2;
    const tempSubId = VALID_UUID_3;

    const categories = [
      {
        category_id: tempCatId,
        category_name: 'Новая категория',
        category_description: 'Описание',
        category_emoji: '🚀',
      },
    ];
    const competencies = [
      {
        competency_id: tempCompId,
        category_id: tempCatId,
        competency_name: 'Новая компетенция',
        competency_description: '',
        is_required: true,
      },
    ];
    const subs = [
      {
        sub_competency_id: tempSubId,
        competency_id: tempCompId,
        sub_competency_name: 'Новая субкомпетенция',
        sub_competency_description: '',
        target_level: 2,
        weight: 0.5,
      },
    ];

    const dto = buildVacancyGraphDTO(categories, competencies, subs);

    expect(dto.categories[0].mode).toBe('new');
    expect(dto.categories[0].name).toBe('Новая категория');
    expect(dto.categories[0].temp_id).toBeDefined();

    const comp = dto.categories[0].competencies[0];
    expect(comp.mode).toBe('new');
    expect(comp.name).toBe('Новая компетенция');

    const sub = comp.sub_competencies[0];
    expect(sub.mode).toBe('new');
    expect(sub.name).toBe('Новая субкомпетенция');
    expect(sub.target_level).toBe(2);
    expect(sub.weight).toBe(0.5);
  });

  it('бросает ошибку если у persisted категории нет category_id', () => {
    const categories = [{ _persisted: true, category_id: null }];
    expect(() => buildVacancyGraphDTO(categories, [], [])).toThrow(
      'category_id'
    );
  });

  it('бросает ошибку если у новой категории нет имени', () => {
    const categories = [{ category_name: '' }];
    expect(() => buildVacancyGraphDTO(categories, [], [])).toThrow(
      'category_name'
    );
  });

  it('бросает ошибку если у новой sub нет имени', () => {
    const tempCatId = VALID_UUID;
    const tempCompId = VALID_UUID_2;

    const categories = [{ category_id: tempCatId, category_name: 'Кат' }];
    const competencies = [
      {
        competency_id: tempCompId,
        category_id: tempCatId,
        competency_name: 'Комп',
      },
    ];
    const subs = [
      {
        competency_id: tempCompId,
        sub_competency_name: '',
      },
    ];

    expect(() => buildVacancyGraphDTO(categories, competencies, subs)).toThrow(
      'sub_competency_name'
    );
  });

  it('возвращает пустые categories для пустых входных данных', () => {
    const dto = buildVacancyGraphDTO([], [], []);
    expect(dto).toEqual({ categories: [] });
  });

  it('нормализует target_level и weight при сборке', () => {
    const tempCatId = VALID_UUID;
    const tempCompId = VALID_UUID_2;

    const categories = [{ category_id: tempCatId, category_name: 'Кат' }];
    const competencies = [
      {
        competency_id: tempCompId,
        category_id: tempCatId,
        competency_name: 'Комп',
      },
    ];
    const subs = [
      {
        competency_id: tempCompId,
        sub_competency_name: 'Саб',
        target_level: 99,
        weight: 99,
      },
    ];

    const dto = buildVacancyGraphDTO(categories, competencies, subs);
    const sub = dto.categories[0].competencies[0].sub_competencies[0];
    expect(sub.target_level).toBe(5);
    expect(sub.weight).toBe(1.0);
  });
});

// buildTaskGraphDTO 

describe('buildTaskGraphDTO', () => {
  it('идентичен buildVacancyGraphDTO по поведению', () => {
    const VALID_UUID = '550e8400-e29b-41d4-a716-446655440000';
    const categories = [
      { category_id: VALID_UUID, _persisted: true },
    ];
    const dto = buildTaskGraphDTO(categories, [], []);
    expect(dto.categories[0].mode).toBe('existing');
  });
});

// COMPETENCY_LEVEL_OPTIONS

describe('COMPETENCY_LEVEL_OPTIONS', () => {
  it('содержит 6 уровней от 0 до 5', () => {
    expect(COMPETENCY_LEVEL_OPTIONS).toHaveLength(6);
    const values = COMPETENCY_LEVEL_OPTIONS.map((o) => o.value);
    expect(values).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it('каждый элемент имеет value и label', () => {
    COMPETENCY_LEVEL_OPTIONS.forEach((option) => {
      expect(option).toHaveProperty('value');
      expect(option).toHaveProperty('label');
      expect(typeof option.label).toBe('string');
    });
  });
});