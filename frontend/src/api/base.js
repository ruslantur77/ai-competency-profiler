import axios from 'axios';

const DEFAULT_API_BASE_URL = '/api/v1';
const runtimeApiBaseUrl = window.__APP_CONFIG__?.API_BASE_URL || DEFAULT_API_BASE_URL;
const apiBaseUrl = runtimeApiBaseUrl.replace(/\/+$/, '') || DEFAULT_API_BASE_URL;

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 3000000,
  withCredentials: true,
});

const getAccessToken = () => localStorage.getItem('access_token');
const setAccessToken = (token) => localStorage.setItem('access_token', token);
const clearAccessToken = () => localStorage.removeItem('access_token');

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url?.includes('/auth/login') &&
      !original.url?.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        });
      }

      original._retry = true;
      isRefreshing = true;

      try {
        const { data } = await api.post('/auth/refresh');
        setAccessToken(data.access_token);
        window.dispatchEvent(new CustomEvent('auth:refreshed'));
        processQueue(null, data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch (refreshError) {
        processQueue(refreshError, null);
        clearAccessToken();
        window.dispatchEvent(new CustomEvent('auth:logout'));
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
