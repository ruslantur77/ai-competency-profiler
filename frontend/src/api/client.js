// frontend/src/api/client.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 3000000,
  withCredentials: true,
})

// ===== AUTH HELPERS =====
const getAccessToken = () => localStorage.getItem('access_token')
const setAccessToken = (token) => localStorage.setItem('access_token', token)
const clearAccessToken = () => localStorage.removeItem('access_token')

// ===== REQUEST INTERCEPTOR =====
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ===== RESPONSE INTERCEPTOR =====
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url?.includes('/auth/login') &&
      !original.url?.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          original.headers.Authorization = `Bearer ${token}`
          return api(original)
        })
      }

      original._retry = true
      isRefreshing = true

      try {
        const { data } = await api.post('/auth/refresh')
        setAccessToken(data.access_token)
        processQueue(null, data.access_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return api(original)
      } catch (refreshError) {
        processQueue(refreshError, null)
        clearAccessToken()
        window.dispatchEvent(new CustomEvent('auth:logout'))
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// ===== AUTH =====
export const login = (email, password) =>
  api.post('/auth/login', new URLSearchParams({ username: email, password }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  )

export const logout = () =>
  api.post('/auth/logout')

// ===== ВАКАНСИИ =====
export const listVacancies = (status_filter) =>
  api.get('/vacancies', { params: { status_filter } })

export const createVacancy = (data) =>
  api.post('/vacancies', data)

export const getVacancy = (id) =>
  api.get(`/vacancies/${id}`)

export const getGraph = (id) =>
  api.get(`/vacancies/${id}/graph`)

export const updateGraph = (id, data) =>
  api.patch(`/vacancies/${id}/graph`, data)

export const updateVacancyStatus = (id, status) =>
  api.patch(`/vacancies/${id}/status`, { status })

// ===== SUGGESTIONS =====
export const getSuggestions = (vacancyId) =>
  api.get(`/vacancies/${vacancyId}/suggestions`)

export const decideSuggestion = (vacancyId, suggestionId, status) =>
  api.post(`/vacancies/${vacancyId}/suggestions/decision`, {
    suggestion_id: suggestionId,
    status,
  })

// ===== РАНЖИРОВАНИЕ =====
export const getVacancyRankings = (vacancyId) =>
  api.get(`/vacancies/${vacancyId}/rankings`)

// ===== КАНДИДАТЫ =====
export const getCandidateProfile = (candidateId) =>
  api.get(`/candidates/${candidateId}/profile`)

// ===== ЗАДАНИЯ =====
export const listTasks = () =>
  api.get('/admin/tasks')

export const getTask = (taskId) =>
  api.get(`/admin/tasks/${taskId}`)

export const rebuildTaskMapping = (taskId) =>
  api.post(`/admin/tasks/${taskId}/mapping/rebuild`)

export const validateTaskMapping = (taskId) =>
  api.post(`/admin/tasks/${taskId}/mapping/validate`)

// ===== HEALTH =====
export const healthCheck = () =>
  api.get('/health')

// ===== ЗАГЛУШКИ =====
export const importFromHH = () => Promise.reject(new Error('Недоступно'))
export const deleteVacancy = () => Promise.reject(new Error('Недоступно'))
export const updateVacancy = () => Promise.reject(new Error('Недоступно'))
export const getVacancyStatus = () => Promise.reject(new Error('Недоступно'))
export const updateCategory = () => Promise.reject(new Error('Недоступно'))
export const addCategory = () => Promise.reject(new Error('Недоступно'))
export const deleteCategory = () => Promise.reject(new Error('Недоступно'))
export const aiFixCategory = () => Promise.reject(new Error('Недоступно'))
export const updateCompetency = () => Promise.reject(new Error('Недоступно'))
export const addCompetency = () => Promise.reject(new Error('Недоступно'))
export const deleteCompetency = () => Promise.reject(new Error('Недоступно'))
export const aiFixCompetencyFull = () => Promise.reject(new Error('Недоступно'))
export const updateSubCompetency = () => Promise.reject(new Error('Недоступно'))
export const addSubCompetency = () => Promise.reject(new Error('Недоступно'))
export const deleteSubCompetency = () => Promise.reject(new Error('Недоступно'))
export const aiFixCompetency = () => Promise.reject(new Error('Недоступно'))

export default api