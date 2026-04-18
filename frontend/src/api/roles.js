export const ROLES = {
  ADMIN: 'admin',
  EXPERT: 'expert',
  HR: 'hr',
  SYSTEM: 'system',
}

export const canAccessVacancies = (role) =>
  role === ROLES.ADMIN || role === ROLES.EXPERT || role === ROLES.HR

export const canCreateVacancy = (role) =>
  role === ROLES.ADMIN || role === ROLES.EXPERT || role === ROLES.HR

export const canAccessTasks = (role) => canAccessVacancies(role)
export const canEditGraph = (role) => role === ROLES.ADMIN || role === ROLES.EXPERT
export const canUseSuggestions = (role) => role === ROLES.ADMIN || role === ROLES.EXPERT

export const canAccessRanking = (role) => canAccessVacancies(role)
export const canAccessOntology = (role) => canAccessVacancies(role)
export const canAccessCandidates = (role) => canAccessVacancies(role)

export const canAccessAdminUsers = (role) =>
  role === ROLES.ADMIN || role === ROLES.SYSTEM

export const hasAllowedRole = (role, allowedRoles = []) => {
  if (!role) return false
  return allowedRoles.length === 0 || allowedRoles.includes(role)
}
