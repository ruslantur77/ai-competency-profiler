import { describe, it, expect } from 'vitest';
import {
  ROLES,
  canAccessVacancies,
  canCreateVacancy,
  canAccessTasks,
  canEditGraph,
  canUseSuggestions,
  canAccessRanking,
  canAccessOntology,
  canAccessCandidates,
  canAccessReviewQueue,
  canAccessAdminUsers,
  hasAllowedRole,
} from './roles.js';

// ─── ROLES константы ─────────────────────────────────────────────────────────

describe('ROLES', () => {
  it('содержит все четыре роли', () => {
    expect(ROLES.ADMIN).toBe('admin');
    expect(ROLES.EXPERT).toBe('expert');
    expect(ROLES.HR).toBe('hr');
    expect(ROLES.SYSTEM).toBe('system');
  });
});

// ─── canAccessVacancies ───────────────────────────────────────────────────────

describe('canAccessVacancies', () => {
  it('разрешает admin, expert, hr', () => {
    expect(canAccessVacancies(ROLES.ADMIN)).toBe(true);
    expect(canAccessVacancies(ROLES.EXPERT)).toBe(true);
    expect(canAccessVacancies(ROLES.HR)).toBe(true);
  });

  it('запрещает system', () => {
    expect(canAccessVacancies(ROLES.SYSTEM)).toBe(false);
  });

  it('запрещает неизвестную роль', () => {
    expect(canAccessVacancies('unknown')).toBe(false);
  });

  it('запрещает null и undefined', () => {
    expect(canAccessVacancies(null)).toBe(false);
    expect(canAccessVacancies(undefined)).toBe(false);
  });
});

// ─── canCreateVacancy ────────────────────────────────────────────────────────

describe('canCreateVacancy', () => {
  it('разрешает admin, expert, hr', () => {
    expect(canCreateVacancy(ROLES.ADMIN)).toBe(true);
    expect(canCreateVacancy(ROLES.EXPERT)).toBe(true);
    expect(canCreateVacancy(ROLES.HR)).toBe(true);
  });

  it('запрещает system', () => {
    expect(canCreateVacancy(ROLES.SYSTEM)).toBe(false);
  });
});

// ─── canAccessTasks ───────────────────────────────────────────────────────────

describe('canAccessTasks', () => {
  it('совпадает с canAccessVacancies для всех ролей', () => {
    Object.values(ROLES).forEach((role) => {
      expect(canAccessTasks(role)).toBe(canAccessVacancies(role));
    });
  });
});

// ─── canEditGraph ─────────────────────────────────────────────────────────────

describe('canEditGraph', () => {
  it('разрешает admin и expert', () => {
    expect(canEditGraph(ROLES.ADMIN)).toBe(true);
    expect(canEditGraph(ROLES.EXPERT)).toBe(true);
  });

  it('запрещает hr и system', () => {
    expect(canEditGraph(ROLES.HR)).toBe(false);
    expect(canEditGraph(ROLES.SYSTEM)).toBe(false);
  });

  it('запрещает null и undefined', () => {
    expect(canEditGraph(null)).toBe(false);
    expect(canEditGraph(undefined)).toBe(false);
  });
});

// ─── canUseSuggestions ───────────────────────────────────────────────────────

describe('canUseSuggestions', () => {
  it('разрешает admin и expert', () => {
    expect(canUseSuggestions(ROLES.ADMIN)).toBe(true);
    expect(canUseSuggestions(ROLES.EXPERT)).toBe(true);
  });

  it('запрещает hr и system', () => {
    expect(canUseSuggestions(ROLES.HR)).toBe(false);
    expect(canUseSuggestions(ROLES.SYSTEM)).toBe(false);
  });
});

// ─── canAccessRanking / canAccessOntology / canAccessCandidates ──────────────

describe('canAccessRanking, canAccessOntology, canAccessCandidates', () => {
  it('все три совпадают с canAccessVacancies', () => {
    Object.values(ROLES).forEach((role) => {
      expect(canAccessRanking(role)).toBe(canAccessVacancies(role));
      expect(canAccessOntology(role)).toBe(canAccessVacancies(role));
      expect(canAccessCandidates(role)).toBe(canAccessVacancies(role));
    });
  });
});

// ─── canAccessReviewQueue ────────────────────────────────────────────────────

describe('canAccessReviewQueue', () => {
  it('разрешает admin и expert', () => {
    expect(canAccessReviewQueue(ROLES.ADMIN)).toBe(true);
    expect(canAccessReviewQueue(ROLES.EXPERT)).toBe(true);
  });

  it('запрещает hr и system', () => {
    expect(canAccessReviewQueue(ROLES.HR)).toBe(false);
    expect(canAccessReviewQueue(ROLES.SYSTEM)).toBe(false);
  });
});

// ─── canAccessAdminUsers ─────────────────────────────────────────────────────

describe('canAccessAdminUsers', () => {
  it('разрешает admin и system', () => {
    expect(canAccessAdminUsers(ROLES.ADMIN)).toBe(true);
    expect(canAccessAdminUsers(ROLES.SYSTEM)).toBe(true);
  });

  it('запрещает expert и hr', () => {
    expect(canAccessAdminUsers(ROLES.EXPERT)).toBe(false);
    expect(canAccessAdminUsers(ROLES.HR)).toBe(false);
  });
});

// ─── hasAllowedRole ──────────────────────────────────────────────────────────

describe('hasAllowedRole', () => {
  it('возвращает true если роль в списке', () => {
    expect(hasAllowedRole(ROLES.ADMIN, [ROLES.ADMIN, ROLES.EXPERT])).toBe(true);
    expect(hasAllowedRole(ROLES.HR, [ROLES.HR])).toBe(true);
  });

  it('возвращает false если роль не в списке', () => {
    expect(hasAllowedRole(ROLES.HR, [ROLES.ADMIN, ROLES.EXPERT])).toBe(false);
    expect(hasAllowedRole(ROLES.SYSTEM, [ROLES.HR])).toBe(false);
  });

  it('возвращает true для пустого списка разрешённых ролей', () => {
    expect(hasAllowedRole(ROLES.HR, [])).toBe(true);
    expect(hasAllowedRole(ROLES.ADMIN, [])).toBe(true);
  });

  it('возвращает false для null роли', () => {
    expect(hasAllowedRole(null, [ROLES.ADMIN])).toBe(false);
    expect(hasAllowedRole(null, [])).toBe(false);
  });

  it('возвращает false для undefined роли', () => {
    expect(hasAllowedRole(undefined, [ROLES.ADMIN])).toBe(false);
  });

  it('возвращает false для пустой строки', () => {
    expect(hasAllowedRole('', [ROLES.ADMIN])).toBe(false);
  });
});