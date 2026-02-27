// frontend/src/api/client.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Вакансия
export const parseVacancy = (url) =>
  api.post('/vacancy/parse', { url })

// Граф
export const getGraph = (sessionId) =>
  api.get(`/graph/${sessionId}`)

// Категории
export const updateCategory = (sessionId, data) =>
  api.put(`/graph/${sessionId}/category`, data)

export const addCategory = (sessionId, data) =>
  api.post(`/graph/${sessionId}/category`, data)

export const deleteCategory = (sessionId, data) =>
  api.delete(`/graph/${sessionId}/category`, { data })

export const aiFixCategory = (sessionId, data) =>
  api.post(`/graph/${sessionId}/ai-fix-category`, data)

// Компетенции
export const updateCompetency = (sessionId, data) =>
  api.put(`/graph/${sessionId}/competency`, data)

export const addCompetency = (sessionId, data) =>
  api.post(`/graph/${sessionId}/competency`, data)

export const deleteCompetency = (sessionId, data) =>
  api.delete(`/graph/${sessionId}/competency`, { data })

export const aiFixCompetencyFull = (sessionId, data) =>
  api.post(`/graph/${sessionId}/ai-fix-competency`, data)

// Подкомпетенции
export const updateSubCompetency = (sessionId, data) =>
  api.put(`/graph/${sessionId}/sub-competency`, data)

export const deleteSubCompetency = (sessionId, data) =>
  api.delete(`/graph/${sessionId}/sub-competency`, { data })

export const addSubCompetency = (sessionId, data) =>
  api.post(`/graph/${sessionId}/sub-competency`, data)

export const aiFixCompetency = (sessionId, data) =>
  api.post(`/graph/${sessionId}/ai-fix`, data)

export default api