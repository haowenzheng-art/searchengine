import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

type Health = { status: string; version: string; app: string }

function HealthCheck() {
  const { data, isLoading, error } = useQuery<Health>({
    queryKey: ['health'],
    queryFn: () => api.get<Health>('/health').then(res => res.data),
    refetchInterval: 10000,
  })

  if (isLoading) return <div className="text-gray-500 text-sm">检查后端状态中...</div>
  if (error) return (
    <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-700">
      后端连接失败：{error.message}
    </div>
  )
  return (
    <div className="rounded-lg border border-green-300 bg-green-50 p-4">
      <div className="text-sm text-gray-600">后端状态</div>
      <div className="text-lg font-semibold text-green-700">
        {data!.status} · v{data!.version}
      </div>
      <div className="text-xs text-gray-500 mt-1">{data!.app}</div>
    </div>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Workflow Discovery Agent</h1>
          <p className="text-gray-600 mt-2">企业级多 Agent 工作流发现 SaaS</p>
        </div>
        <HealthCheck />
        <div className="text-xs text-gray-400 border-t pt-4">
          Phase 0：工程骨架已就绪 · Phase 1/2 将实现真 Agent 和证据链
        </div>
      </div>
    </div>
  )
}
