import { api } from './base'

export const listAdminUsers = (params = {}) => api.get('/admin/users', { params })

export const createAdminUser = (payload) => api.post('/admin/users', payload)

export const updateAdminUserRole = (userId, role) =>
  api.patch(`/admin/users/${userId}/role`, { role })

export const updateAdminUserStatus = (userId, isActive) =>
  api.patch(`/admin/users/${userId}/status`, { is_active: isActive })
