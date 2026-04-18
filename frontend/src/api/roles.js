export const ROLES = {
  ADMIN: 'admin',
  EXPERT: 'expert',
  HR: 'hr',
  SYSTEM: 'system',
}

export const canCreateVacancy = (role) =>
  role === ROLES.ADMIN || role === ROLES.EXPERT || role === ROLES.HR

export const canAccessTasks = (role) => role === ROLES.ADMIN || role === ROLES.EXPERT
export const canEditGraph = (role) => role === ROLES.ADMIN || role === ROLES.EXPERT
export const canUseSuggestions = (role) => role === ROLES.ADMIN || role === ROLES.EXPERT

export const hasAllowedRole = (role, allowedRoles = []) => {
  if (!role) return false
  return allowedRoles.length === 0 || allowedRoles.includes(role)
}
