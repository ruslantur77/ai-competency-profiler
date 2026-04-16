import { api } from './base'

export const listVacancies = (status_filter) =>
  api.get('/vacancies', { params: { status_filter } })

export const createVacancy = (data) => api.post('/vacancies', data)

export const getVacancy = (id) => api.get(`/vacancies/${id}`)

export const getGraph = (id) => api.get(`/vacancies/${id}/graph`)

export const updateGraph = (id, data) => api.patch(`/vacancies/${id}/graph`, data)

export const updateVacancyStatus = (id, status) =>
  api.patch(`/vacancies/${id}/status`, { status })
