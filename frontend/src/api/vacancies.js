import { api } from './base'

export const listVacancies = (status_filter) =>
  api.get('/vacancies', { params: { status_filter } })

export const listVacanciesForReview = (limit = 200, offset = 0) =>
  api.get('/vacancies/review-queue', { params: { limit, offset } })

export const createVacancy = (data) => api.post('/vacancies', data)

export const getVacancy = (id) => api.get(`/vacancies/${id}`)

export const getGraph = (id) => api.get(`/vacancies/${id}/graph`)

export const updateGraph = (id, data) => api.patch(`/vacancies/${id}/graph`, data)

export const finalizeVacancyGraph = (id) =>
  api.post(`/vacancies/${id}/graph/finalize`)

export const updateVacancyStatus = (id, status) =>
  api.patch(`/vacancies/${id}/status`, { status })

export const deleteVacancy = (id) => api.delete(`/vacancies/${id}`)
export const restoreVacancy = (id) => api.post(`/vacancies/${id}/restore`)
export const hardDeleteVacancy = (id) => api.delete(`/vacancies/${id}/hard`)
