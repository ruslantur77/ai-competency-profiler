import { api } from './base'

export const login = (email, password) =>
  api.post('/auth/login', new URLSearchParams({ username: email, password }), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })

export const logout = () => api.post('/auth/logout')
