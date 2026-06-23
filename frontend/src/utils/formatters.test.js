import { describe, it, expect } from 'vitest';
import { formatDateTime, formatPercent } from './formatters.js';

// ─── formatDateTime ───────────────────────────────────────────────────────────

describe('formatDateTime', () => {
  it('возвращает — для null', () => {
    expect(formatDateTime(null)).toBe('—');
  });

  it('возвращает — для undefined', () => {
    expect(formatDateTime(undefined)).toBe('—');
  });

  it('возвращает — для пустой строки', () => {
    expect(formatDateTime('')).toBe('—');
  });

  it('возвращает строку для валидной даты', () => {
    const result = formatDateTime('2024-01-15T10:30:00Z');
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
    expect(result).not.toBe('—');
  });

  it('содержит год для валидной даты', () => {
    const result = formatDateTime('2024-06-01T00:00:00Z');
    expect(result).toContain('2024');
  });

  it('возвращает строку для timestamp числа', () => {
    const result = formatDateTime(0);
    expect(typeof result).toBe('string');
  });
});

// ─── formatPercent ────────────────────────────────────────────────────────────

describe('formatPercent', () => {
  // ─── normalized режим (по умолчанию) ─────────────────────────────────────

  it('форматирует 1.0 как 100%', () => {
    expect(formatPercent(1.0)).toBe('100%');
  });

  it('форматирует 0 как 0%', () => {
    expect(formatPercent(0)).toBe('0%');
  });

  it('форматирует 0.5 как 50%', () => {
    expect(formatPercent(0.5)).toBe('50%');
  });

  it('форматирует 0.756 как 76%', () => {
    expect(formatPercent(0.756)).toBe('76%');
  });

  it('округляет 0.555 до 56%', () => {
    expect(formatPercent(0.555)).toBe('56%');
  });

  // ─── normalized: false ────────────────────────────────────────────────────

  it('форматирует 100 как 100% в ненормализованном режиме', () => {
    expect(formatPercent(100, { normalized: false })).toBe('100%');
  });

  it('форматирует 75.6 как 76% в ненормализованном режиме', () => {
    expect(formatPercent(75.6, { normalized: false })).toBe('76%');
  });

  it('форматирует 0 как 0% в ненормализованном режиме', () => {
    expect(formatPercent(0, { normalized: false })).toBe('0%');
  });

  // ─── невалидные значения ──────────────────────────────────────────────────

  it('возвращает 0% для null', () => {
    expect(formatPercent(null)).toBe('0%');
  });

  it('возвращает 0% для undefined', () => {
    expect(formatPercent(undefined)).toBe('0%');
  });

  it('возвращает 0% для NaN', () => {
    expect(formatPercent(NaN)).toBe('0%');
  });

  it('возвращает 0% для строки', () => {
    expect(formatPercent('abc')).toBe('0%');
  });
});