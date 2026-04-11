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

// ===== REQUEST INTERCEPTOR — подставляем токен =====
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ===== RESPONSE INTERCEPTOR — обновляем токен при 401 =====
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

    // Если 401 и это не повторный запрос и не сам логин/рефреш
    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url?.includes('/auth/login') &&
      !original.url?.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        // Ждём пока другой запрос обновит токен
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
        // Редиректим на логин
        window.location.href = '/login'
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

// ===== SUGGESTIONS (AI правки) =====
export const getSuggestions = (vacancyId) =>
  api.get(`/vacancies/${vacancyId}/suggestions`)

export const decideSuggestion = (vacancyId, suggestionId, status) =>
  api.post(`/vacancies/${vacancyId}/suggestions/decision`, {
    suggestion_id: suggestionId,
    status,
  })

// ===== КАНДИДАТЫ =====
export const getCandidateProfile = (candidateId) =>
  api.get(`/candidates/${candidateId}/profile`)

export const getVacancyRankings = (vacancyId) =>
  api.get(`/vacancies/${vacancyId}/rankings`)

// ===== HEALTH =====
export const healthCheck = () =>
  api.get('/health')

export default api