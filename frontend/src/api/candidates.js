import { api } from './base'

export const listCandidates = () => api.get('/candidates')

export const getCandidate = (candidateId) => api.get(`/candidates/${candidateId}`)

export const getCandidateProfile = (candidateId) =>
  api.get(`/candidates/${candidateId}/profile`)

export const deleteCandidate = (candidateId) => api.delete(`/candidates/${candidateId}`)
