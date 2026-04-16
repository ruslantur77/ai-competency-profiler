import { api } from './base'

export const listTasks = () => api.get('/admin/tasks')

export const getTask = (taskId) => api.get(`/admin/tasks/${taskId}`)

export const rebuildTaskMapping = (taskId) =>
  api.post(`/admin/tasks/${taskId}/mapping/rebuild`)

export const validateTaskMapping = (taskId) =>
  api.post(`/admin/tasks/${taskId}/mapping/validate`)
