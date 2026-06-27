export type UserRole = 'admin' | 'member' | 'viewer'

export interface User {
  id: number
  email: string
  role: UserRole
  created_at?: string
}

export interface AuthResponse {
  user: User
  access_token: string
  refresh_token: string
  token_type: string
}

export type WorkflowStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface Workflow {
  id: number
  user_id: number
  query: string
  notes: string | null
  status: WorkflowStatus
  error: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface WorkflowListResponse {
  items: Workflow[]
  total: number
  page: number
  page_size: number
}

export interface AgentRun {
  id: number
  workflow_id: number
  status: string
  current_iteration: number
  messages: unknown
  final_output: Record<string, unknown> | null
  started_at: string
  ended_at: string | null
  created_at: string
}

export interface ToolCall {
  id: number
  tool_name: string
  iteration: number
  input_args: Record<string, unknown>
  output_result: Record<string, unknown> | null
  error: string | null
  input_tokens: number
  output_tokens: number
  duration_ms: number
  created_at: string
}

export interface Evidence {
  id: number
  url: string
  title: string | null
  snippet: string | null
  score: number
  score_reason: string | null
  is_homepage: boolean
  is_disambiguation: boolean
  score_layer: number
  word_count: number
  fetched_at: string | null
}

export interface UsageSummary {
  workflows_started: number
  workflows_completed: number
  workflows_failed: number
  tool_calls: number
  input_tokens: number
  output_tokens: number
  search_queries: number
  evidence_fetched: number
}
