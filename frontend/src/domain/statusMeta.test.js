import { describe, it, expect } from 'vitest';
import {
  CANDIDATE_STATUS_META,
  getCandidateStatusMeta,
} from './statusMeta.js';

describe('CANDIDATE_STATUS_META', () => {
  it('содержит все три статуса', () => {
    expect(CANDIDATE_STATUS_META).toHaveProperty('pending');
    expect(CANDIDATE_STATUS_META).toHaveProperty('completed');
    expect(CANDIDATE_STATUS_META).toHaveProperty('failed');
  });

  it('каждый статус имеет label и badge', () => {
    Object.values(CANDIDATE_STATUS_META).forEach((meta) => {
      expect(meta).toHaveProperty('label');
      expect(meta).toHaveProperty('badge');
      expect(typeof meta.label).toBe('string');
      expect(typeof meta.badge).toBe('string');
    });
  });
});

describe('getCandidateStatusMeta', () => {
  it('возвращает мету для pending', () => {
    const result = getCandidateStatusMeta('pending');
    expect(result.label).toBe('Ожидает оценки');
    expect(result.badge).toBe('pending');
  });

  it('возвращает мету для completed', () => {
    const result = getCandidateStatusMeta('completed');
    expect(result.label).toBe('Оценен');
    expect(result.badge).toBe('completed');
  });

  it('возвращает мету для failed', () => {
    const result = getCandidateStatusMeta('failed');
    expect(result.label).toBe('Ошибка оценки');
    expect(result.badge).toBe('failed');
  });

  it('возвращает pending для неизвестного статуса', () => {
    const result = getCandidateStatusMeta('unknown_status');
    expect(result).toEqual(CANDIDATE_STATUS_META.pending);
  });

  it('возвращает pending для undefined', () => {
    const result = getCandidateStatusMeta(undefined);
    expect(result).toEqual(CANDIDATE_STATUS_META.pending);
  });

  it('возвращает pending для пустой строки', () => {
    const result = getCandidateStatusMeta('');
    expect(result).toEqual(CANDIDATE_STATUS_META.pending);
  });

  it('возвращает pending для null', () => {
    const result = getCandidateStatusMeta(null);
    expect(result).toEqual(CANDIDATE_STATUS_META.pending);
  });
});