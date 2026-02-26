// frontend/src/api/client.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export const parseVacancy = (url) =>
  api.post('/vacancy/parse', { url })

export const getGraph = (sessionId) =>
  api.get(`/graph/${sessionId}`)

export const updateSubCompetency = (sessionId, data) =>
  api.put(`/graph/${sessionId}/sub-competency`, data)

export const deleteSubCompetency = (sessionId, data) =>
  api.delete(`/graph/${sessionId}/sub-competency`, { data })

export const addSubCompetency = (sessionId, data) =>
  api.post(`/graph/${sessionId}/sub-competency`, data)

export const aiFixCompetency = (sessionId, data) =>
  api.post(`/graph/${sessionId}/ai-fix`, data)

export default api