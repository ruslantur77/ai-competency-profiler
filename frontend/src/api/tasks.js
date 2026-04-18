import { api } from './base';

export const listTasks = (params = {}) => api.get('/tasks', { params });

export const getTask = (taskId) => api.get(`/tasks/${taskId}`);

export const updateTaskGraph = (taskId, data) => api.patch(`/tasks/${taskId}/graph`, data);

export const finalizeTaskGraph = (taskId) => api.post(`/tasks/${taskId}/graph/finalize`);

export const updateTaskStatus = (taskId, status) =>
  api.patch(`/tasks/${taskId}/status`, { status });
