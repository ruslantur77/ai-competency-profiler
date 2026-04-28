import { describe, it, expect } from 'vitest';
import { normalizePageResponse, extractItems } from './adapters.js';

describe('normalizePageResponse', () => {
  // массив напрямую 

  it('принимает массив напрямую', () => {
    const payload = [{ id: 1 }, { id: 2 }];
    const result = normalizePageResponse(payload);
    expect(result.items).toEqual(payload);
    expect(result.total).toBe(2);
    expect(result.limit).toBe(2);
    expect(result.offset).toBe(0);
  });

  it('возвращает корректный результат для пустого массива', () => {
    const result = normalizePageResponse([]);
    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
    expect(result.limit).toBe(0);
    expect(result.offset).toBe(0);
  });

  // ─── стандартный paginated ответ ──────────────────────────────────────────

  it('обрабатывает стандартный paginated ответ с items', () => {
    const payload = {
      items: [{ id: 1 }],
      total: 10,
      limit: 5,
      offset: 0,
    };
    const result = normalizePageResponse(payload);
    expect(result.items).toEqual([{ id: 1 }]);
    expect(result.total).toBe(10);
    expect(result.limit).toBe(5);
    expect(result.offset).toBe(0);
  });

  it('обрабатывает ответ с results вместо items', () => {
    const payload = {
      results: [{ id: 2 }],
      total: 20,
      limit: 10,
      offset: 5,
    };
    const result = normalizePageResponse(payload);
    expect(result.items).toEqual([{ id: 2 }]);
    expect(result.total).toBe(20);
    expect(result.limit).toBe(10);
    expect(result.offset).toBe(5);
  });

  // ─── вложенный data ───────────────────────────────────────────────────────

  it('разворачивает вложенный data объект', () => {
    const payload = {
      data: {
        items: [{ id: 3 }],
        total: 30,
        limit: 15,
        offset: 10,
      },
    };
    const result = normalizePageResponse(payload);
    expect(result.items).toEqual([{ id: 3 }]);
    expect(result.total).toBe(30);
    expect(result.limit).toBe(15);
    expect(result.offset).toBe(10);
  });

  it('не разворачивает data если data является массивом — items берётся из корня', () => {
    const payload = {
      data: [{ id: 4 }],
      total: 1,
      limit: 1,
      offset: 0,
    };
    const result = normalizePageResponse(payload);
    // data — массив, source = payload, items ищется в payload.items → []
    expect(result.items).toEqual([]);
    expect(result.total).toBe(1);
  });

  // ─── альтернативные поля ─────────────────────────────────────────────────

  it('использует count если total отсутствует', () => {
    const payload = { items: [{ id: 1 }], count: 99 };
    const result = normalizePageResponse(payload);
    expect(result.total).toBe(99);
  });

  it('использует page_size если limit отсутствует', () => {
    const payload = { items: [{ id: 1 }], total: 1, page_size: 25 };
    const result = normalizePageResponse(payload);
    expect(result.limit).toBe(25);
  });

  it('использует skip если offset отсутствует', () => {
    const payload = { items: [{ id: 1 }], total: 1, limit: 1, skip: 7 };
    const result = normalizePageResponse(payload);
    expect(result.offset).toBe(7);
  });

  // ─── fallback значения ────────────────────────────────────────────────────

  it('возвращает items.length как total если total не указан', () => {
    const payload = { items: [{ id: 1 }, { id: 2 }] };
    const result = normalizePageResponse(payload);
    expect(result.total).toBe(2);
  });

  it('возвращает пустые items если нет items и results', () => {
    const payload = { total: 0, limit: 10, offset: 0 };
    const result = normalizePageResponse(payload);
    expect(result.items).toEqual([]);
  });

  it('возвращает offset 0 по умолчанию', () => {
    const payload = { items: [] };
    const result = normalizePageResponse(payload);
    expect(result.offset).toBe(0);
  });

  // ─── граничные случаи ─────────────────────────────────────────────────────

  it('возвращает пустой результат для null', () => {
    const result = normalizePageResponse(null);
    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
    expect(result.offset).toBe(0);
  });

  it('возвращает пустой результат для undefined', () => {
    const result = normalizePageResponse(undefined);
    expect(result.items).toEqual([]);
  });

  it('возвращает пустой результат для пустого объекта', () => {
    const result = normalizePageResponse({});
    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
  });
});

describe('extractItems', () => {
  it('возвращает items из paginated ответа', () => {
    const payload = { items: [{ id: 1 }], total: 1 };
    expect(extractItems(payload)).toEqual([{ id: 1 }]);
  });

  it('возвращает массив напрямую', () => {
    const payload = [{ id: 1 }, { id: 2 }];
    expect(extractItems(payload)).toEqual(payload);
  });

  it('возвращает пустой массив для пустого объекта', () => {
    expect(extractItems({})).toEqual([]);
  });

  it('возвращает пустой массив для null', () => {
    expect(extractItems(null)).toEqual([]);
  });
});