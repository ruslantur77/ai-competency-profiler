import { api } from './base'

export const listTasks = (status_filter) =>
  api.get('/tasks', { params: { status_filter } })

export const getTask = (taskId) => api.get(`/tasks/${taskId}`)

export const updateTaskGraph = (taskId, data) =>
  api.patch(`/tasks/${taskId}/graph`, data)

export const finalizeTaskGraph = (taskId) =>
  api.post(`/tasks/${taskId}/graph/finalize`)

export const updateTaskStatus = (taskId, status) =>
  api.patch(`/tasks/${taskId}/status`, { status })
