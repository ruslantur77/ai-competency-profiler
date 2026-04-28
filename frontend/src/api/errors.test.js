import { describe, it, expect } from 'vitest';
import { getErrorMessage } from './errors.js';

const makeError = (status, data = {}, message = '') => ({
  response: { status, data },
  message,
});

describe('getErrorMessage', () => {
  // ─── статус коды ──────────────────────────────────────────────────────────

  it('возвращает сообщение для 400', () => {
    expect(getErrorMessage(makeError(400))).toBe('Некорректный запрос');
  });

  it('возвращает сообщение для 401', () => {
    expect(getErrorMessage(makeError(401))).toBe('Сессия истекла. Войдите снова');
  });

  it('возвращает сообщение для 403', () => {
    expect(getErrorMessage(makeError(403))).toBe('Недостаточно прав для выполнения операции');
  });

  it('возвращает сообщение для 404', () => {
    expect(getErrorMessage(makeError(404))).toBe('Ресурс не найден');
  });

  it('возвращает сообщение для 409', () => {
    expect(getErrorMessage(makeError(409))).toBe(
      'Конфликт данных. Обновите страницу и повторите'
    );
  });

  it('возвращает сообщение для 500', () => {
    expect(getErrorMessage(makeError(500))).toBe('Внутренняя ошибка сервера');
  });

  it('возвращает сообщение для 502', () => {
    expect(getErrorMessage(makeError(502))).toBe('Сервер временно недоступен');
  });

  it('возвращает сообщение для 503', () => {
    expect(getErrorMessage(makeError(503))).toBe('Сервис временно недоступен');
  });

  it('возвращает сообщение для 504', () => {
    expect(getErrorMessage(makeError(504))).toBe('Сервер не ответил вовремя');
  });

  // ─── envelope message ─────────────────────────────────────────────────────

  it('возвращает envelope message для 4xx если есть payload.message', () => {
    const error = makeError(400, { message: 'Вакансия не найдена' });
    expect(getErrorMessage(error)).toBe('Вакансия не найдена');
  });

  it('не возвращает envelope message для 5xx', () => {
    const error = makeError(500, { message: 'Internal error detail' });
    expect(getErrorMessage(error)).toBe('Внутренняя ошибка сервера');
  });

  // ─── 422 валидация ────────────────────────────────────────────────────────

  it('возвращает детали валидации для 422 с details массивом строк', () => {
    const error = makeError(422, {
      details: ['Поле name обязательно', 'Поле weight невалидно'],
    });
    expect(getErrorMessage(error)).toBe(
      'Поле name обязательно; Поле weight невалидно'
    );
  });

  it('возвращает детали валидации для 422 с loc и msg', () => {
    const error = makeError(422, {
      details: [{ loc: ['body', 'name'], msg: 'field required' }],
    });
    expect(getErrorMessage(error)).toBe('body.name: field required');
  });

  it('возвращает envelope message для 422 если details отсутствуют', () => {
    const error = makeError(422, { message: 'Validation failed' });
    expect(getErrorMessage(error)).toBe('Validation failed');
  });

  it('возвращает дефолтное сообщение для 422 если нет details и message', () => {
    const error = makeError(422, {});
    expect(getErrorMessage(error)).toBe('Ошибка валидации данных');
  });

  // ─── detail поле (FastAPI стиль) ──────────────────────────────────────────

  it('использует payload.detail строкой для 4xx', () => {
    const error = makeError(404, { detail: 'Not found in database' });
    expect(getErrorMessage(error)).toBe('Not found in database');
  });

  it('использует payload.detail массивом для 4xx', () => {
    const error = makeError(400, {
      detail: [{ loc: ['query', 'id'], msg: 'invalid value' }],
    });
    expect(getErrorMessage(error)).toBe('query.id: invalid value');
  });

  // ─── overrides ────────────────────────────────────────────────────────────

  it('применяет override для конкретного статуса', () => {
    const error = makeError(404);
    const result = getErrorMessage(error, { overrides: { 404: 'Вакансия удалена' } });
    expect(result).toBe('Вакансия удалена');
  });

  it('override имеет приоритет над envelope message', () => {
    const error = makeError(400, { message: 'envelope message' });
    const result = getErrorMessage(error, { overrides: { 400: 'Мой текст' } });
    expect(result).toBe('Мой текст');
  });

  // ─── сетевые ошибки ───────────────────────────────────────────────────────

  it('возвращает сообщение для ECONNABORTED', () => {
    const error = { code: 'ECONNABORTED', message: 'timeout' };
    expect(getErrorMessage(error)).toBe(
      'Превышено время ожидания ответа сервера'
    );
  });

  it('возвращает сообщение о сети если нет статуса и нет message', () => {
    const error = {};
    expect(getErrorMessage(error)).toBe(
      'Ошибка сети. Проверьте подключение и повторите'
    );
  });

  it('возвращает localMessage если нет статуса но есть message', () => {
    const error = { message: 'Network Error' };
    expect(getErrorMessage(error)).toBe('Network Error');
  });

  // ─── fallback ─────────────────────────────────────────────────────────────

  it('возвращает дефолтный fallback', () => {
    const error = makeError(418);
    expect(getErrorMessage(error)).toBe('Ошибка запроса');
  });

  it('применяет кастомный fallback', () => {
    const error = makeError(418);
    expect(getErrorMessage(error, { fallback: 'Что-то пошло не так' })).toBe(
      'Что-то пошло не так'
    );
  });

  // ─── граничные случаи ─────────────────────────────────────────────────────

  it('не падает для null', () => {
    expect(() => getErrorMessage(null)).not.toThrow();
  });

  it('не падает для undefined', () => {
    expect(() => getErrorMessage(undefined)).not.toThrow();
  });
});