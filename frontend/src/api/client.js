// frontend/src/api/client.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 3000000,
})

// ===== Вакансии =====
export const listVacancies = () =>
  api.get('/vacancies')

export const createVacancy = (data) =>
  api.post('/vacancies', data)

export const importFromHH = (url) =>
  api.post('/vacancies/import-hh', { url })

export const getVacancy = (id) =>
  api.get(`/vacancies/${id}`)

export const updateVacancy = (id, data) =>
  api.put(`/vacancies/${id}`, data)

export const deleteVacancy = (id) =>
  api.delete(`/vacancies/${id}`)

export const getVacancyStatus = (id) =>
  api.get(`/vacancies/${id}/status`)

// ===== Граф =====
export const getGraph = (id) =>
  api.get(`/vacancies/${id}/graph`)

// ===== Категории =====
export const updateCategory = (id, data) =>
  api.put(`/vacancies/${id}/category`, data)

export const addCategory = (id, data) =>
  api.post(`/vacancies/${id}/category`, data)

export const deleteCategory = (id, data) =>
  api.request({ method: 'DELETE', url: `/vacancies/${id}/category`, data })

export const aiFixCategory = (id, data) =>
  api.post(`/vacancies/${id}/ai-fix-category`, data)

// ===== Компетенции =====
export const updateCompetency = (id, data) =>
  api.put(`/vacancies/${id}/competency`, data)

export const addCompetency = (id, data) =>
  api.post(`/vacancies/${id}/competency`, data)

export const deleteCompetency = (id, data) =>
  api.request({ method: 'DELETE', url: `/vacancies/${id}/competency`, data })

export const aiFixCompetencyFull = (id, data) =>
  api.post(`/vacancies/${id}/ai-fix-competency`, data)

// ===== Подкомпетенции =====
export const updateSubCompetency = (id, data) =>
  api.put(`/vacancies/${id}/sub-competency`, data)

export const addSubCompetency = (id, data) =>
  api.post(`/vacancies/${id}/sub-competency`, data)

export const deleteSubCompetency = (id, data) =>
  api.request({ method: 'DELETE', url: `/vacancies/${id}/sub-competency`, data })

export const aiFixCompetency = (id, data) =>
  api.post(`/vacancies/${id}/ai-fix`, data)

export default api