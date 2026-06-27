import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

let isRefreshing = false
let refreshPromise: Promise<string> | null = null

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refreshToken = useAuthStore.getState().refreshToken
      if (!refreshToken) {
        useAuthStore.getState().logout()
        redirectToLogin()
        return Promise.reject(error)
      }
      try {
        if (!isRefreshing) {
          isRefreshing = true
          refreshPromise = (async () => {
            const res = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
            const { access_token, refresh_token: new_refresh } = res.data
            useAuthStore.getState().updateTokens(access_token, new_refresh)
            return access_token
          })()
        }
        const newToken = await refreshPromise!
        isRefreshing = false
        refreshPromise = null
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
        }
        return api(originalRequest)
      } catch (refreshError) {
        isRefreshing = false
        refreshPromise = null
        useAuthStore.getState().logout()
        redirectToLogin()
        return Promise.reject(refreshError)
      }
    }
    const detail = (error.response?.data as { detail?: string })?.detail || error.message
    if (typeof detail === 'string') {
      toast.error(detail)
    }
    return Promise.reject(error)
  }
)

function redirectToLogin() {
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}
