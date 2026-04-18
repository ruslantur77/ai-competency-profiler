import { api } from './base'

export const listVacancies = (params = {}) => api.get('/vacancies', { params })

export const listVacanciesForReview = (params = {}) =>
  api.get('/vacancies/review-queue', { params })

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
