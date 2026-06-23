import { describe, it, expect, vi } from 'vitest';
import { fetchAllPages } from './pagination.js';

describe('fetchAllPages', () => {
  // ─── базовые сценарии ─────────────────────────────────────────────────────

  it('возвращает все элементы за одну страницу', async () => {
    const fetchPage = vi.fn().mockResolvedValue({
      items: [{ id: 1 }, { id: 2 }],
      total: 2,
      limit: 100,
      offset: 0,
    });

    const result = await fetchAllPages({ fetchPage });

    expect(result.items).toEqual([{ id: 1 }, { id: 2 }]);
    expect(result.total).toBe(2);
    expect(fetchPage).toHaveBeenCalledTimes(1);
  });

  it('собирает элементы с нескольких страниц', async () => {
    const fetchPage = vi.fn()
      .mockResolvedValueOnce({
        items: [{ id: 1 }, { id: 2 }],
        total: 4,
        limit: 2,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [{ id: 3 }, { id: 4 }],
        total: 4,
        limit: 2,
        offset: 2,
      });

    const result = await fetchAllPages({ fetchPage, limit: 2 });

    expect(result.items).toHaveLength(4);
    expect(result.items).toEqual([{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }]);
    expect(fetchPage).toHaveBeenCalledTimes(2);
  });

  it('останавливается на пустой странице', async () => {
    const fetchPage = vi.fn()
      .mockResolvedValueOnce({
        items: [{ id: 1 }],
        total: 10,
        limit: 1,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [],
        total: 10,
        limit: 1,
        offset: 1,
      });

    const result = await fetchAllPages({ fetchPage, limit: 1 });

    expect(result.items).toEqual([{ id: 1 }]);
    expect(fetchPage).toHaveBeenCalledTimes(2);
  });

  it('останавливается когда собрано total элементов', async () => {
    const fetchPage = vi.fn()
      .mockResolvedValueOnce({
        items: [{ id: 1 }, { id: 2 }],
        total: 2,
        limit: 2,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [{ id: 3 }],
        total: 2,
        limit: 2,
        offset: 2,
      });

    const result = await fetchAllPages({ fetchPage, limit: 2 });

    expect(result.items).toHaveLength(2);
    expect(fetchPage).toHaveBeenCalledTimes(1);
  });

  // ─── параметры запросов ───────────────────────────────────────────────────

  it('передаёт корректные offset и limit в fetchPage', async () => {
    const fetchPage = vi.fn()
      .mockResolvedValueOnce({
        items: [{ id: 1 }],
        total: 2,
        limit: 1,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [{ id: 2 }],
        total: 2,
        limit: 1,
        offset: 1,
      });

    await fetchAllPages({ fetchPage, limit: 1 });

    expect(fetchPage).toHaveBeenNthCalledWith(1, { limit: 1, offset: 0 });
    expect(fetchPage).toHaveBeenNthCalledWith(2, { limit: 1, offset: 1 });
  });

  it('учитывает initialOffset', async () => {
    const fetchPage = vi.fn().mockResolvedValue({
      items: [{ id: 5 }],
      total: 1,
      limit: 100,
      offset: 50,
    });

    const result = await fetchAllPages({ fetchPage, initialOffset: 50 });

    expect(fetchPage).toHaveBeenCalledWith({ limit: 100, offset: 50 });
    expect(result.offset).toBe(50);
  });

  // ─── maxPages ─────────────────────────────────────────────────────────────

  it('останавливается после maxPages итераций', async () => {
    const fetchPage = vi.fn().mockResolvedValue({
      items: [{ id: 1 }],
      total: 999,
      limit: 1,
      offset: 0,
    });

    const result = await fetchAllPages({ fetchPage, limit: 1, maxPages: 3 });

    expect(fetchPage).toHaveBeenCalledTimes(3);
    expect(result.items).toHaveLength(3);
  });

  // ─── граничные случаи ─────────────────────────────────────────────────────

  it('возвращает пустой результат если первая страница пустая', async () => {
    const fetchPage = vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
    });

    const result = await fetchAllPages({ fetchPage });

    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
    expect(fetchPage).toHaveBeenCalledTimes(1);
  });

  it('использует items.length как total если total не пришёл', async () => {
    const fetchPage = vi.fn().mockResolvedValue({
      items: [{ id: 1 }, { id: 2 }],
    });

    const result = await fetchAllPages({ fetchPage });

    expect(result.total).toBe(2);
  });

  it('пробрасывает ошибку fetchPage наверх', async () => {
    const fetchPage = vi.fn().mockRejectedValue(new Error('Network error'));

    await expect(fetchAllPages({ fetchPage })).rejects.toThrow('Network error');
  });
});