import { api } from './api'
import type {
  AuthResponse,
  User,
  Workflow,
  WorkflowListResponse,
  AgentRun,
  ToolCall,
  Evidence,
  UsageSummary,
} from './types'

export const authApi = {
  register: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/register', { email, password }).then((r) => r.data),
  login: (email: string, password: string) =>
    api
      .post<AuthResponse>('/auth/login', new URLSearchParams({ username: email, password }), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .then((r) => r.data),
  me: () => api.get<User>('/auth/me').then((r) => r.data),
  refresh: (refreshToken: string) =>
    api
      .post<{ access_token: string; refresh_token: string; token_type: string }>(
        '/auth/refresh',
        { refresh_token: refreshToken }
      )
      .then((r) => r.data),
}

export const workflowApi = {
  list: (params: { page?: number; page_size?: number; status?: string } = {}) =>
    api
      .get<WorkflowListResponse>('/workflows', { params: { page: 1, page_size: 20, ...params } })
      .then((r) => r.data),
  get: (id: number) => api.get<Workflow>(`/workflows/${id}`).then((r) => r.data),
  create: (query: string, notes: string | null) =>
    api.post<{ workflow_id: number; task_id: string; status: string }>('/workflows', { query, notes }).then((r) => r.data),
  delete: (id: number) => api.delete(`/workflows/${id}`),
  runs: (id: number) => api.get<AgentRun[]>(`/workflows/${id}/runs`).then((r) => r.data),
  evidence: (id: number) => api.get<Evidence[]>(`/workflows/${id}/evidence`).then((r) => r.data),
  toolCalls: (workflowId: number, runId: number) =>
    api.get<ToolCall[]>(`/workflows/${workflowId}/runs/${runId}/tool_calls`).then((r) => r.data),
}

export const usageApi = {
  today: () => api.get<UsageSummary>('/usage/today').then((r) => r.data),
  month: () => api.get<UsageSummary>('/usage/month').then((r) => r.data),
}
