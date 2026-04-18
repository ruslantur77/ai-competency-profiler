import { api } from './base'

export const listCandidates = (params = {}) => api.get('/candidates', { params })

export const getCandidate = (candidateId) => api.get(`/candidates/${candidateId}`)

export const getCandidateProfile = (candidateId) =>
  api.get(`/candidates/${candidateId}/profile`)

export const deleteCandidate = (candidateId) => api.delete(`/candidates/${candidateId}`)
