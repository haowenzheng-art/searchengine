import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { WorkflowStatusBadge } from '@/components/WorkflowStatusBadge'
import { workflowApi, usageApi } from '@/lib/api-services'
import { formatDate } from '@/lib/utils'
import { useState } from 'react'

export function DashboardPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('')

  const { data, isLoading } = useQuery({
    queryKey: ['workflows', page, statusFilter],
    queryFn: () => workflowApi.list({ page, page_size: 20, status: statusFilter || undefined }),
    refetchInterval: 5000,
  })

  const { data: usage } = useQuery({
    queryKey: ['usage', 'today'],
    queryFn: usageApi.today,
    refetchInterval: 10000,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">工作流</h1>
          <p className="text-sm text-muted-foreground">创建、查看、管理你的 Agent 工作流</p>
        </div>
        <Button onClick={() => navigate('/workflows/new')}>
          <Plus className="mr-2 h-4 w-4" />
          新建工作流
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">今日工作流</div>
            <div className="text-2xl font-semibold mt-1">{usage?.workflows_started ?? '-'}</div>
            <div className="text-xs text-muted-foreground mt-1">完成 {usage?.workflows_completed ?? 0} · 失败 {usage?.workflows_failed ?? 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">今日工具调用</div>
            <div className="text-2xl font-semibold mt-1">{usage?.tool_calls ?? '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">今日输入 tokens</div>
            <div className="text-2xl font-semibold mt-1">{usage?.input_tokens?.toLocaleString('zh-CN') ?? '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">今日输出 tokens</div>
            <div className="text-2xl font-semibold mt-1">{usage?.output_tokens?.toLocaleString('zh-CN') ?? '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input placeholder="按 query 搜索（仅本地过滤）" className="pl-8" />
            </div>
            <select
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={statusFilter}
              onChange={(e) => {
                setPage(1)
                setStatusFilter(e.target.value)
              }}
            >
              <option value="">全部状态</option>
              <option value="pending">排队中</option>
              <option value="running">运行中</option>
              <option value="completed">已完成</option>
              <option value="failed">失败</option>
            </select>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : data && data.items.length > 0 ? (
            <>
              <div className="divide-y rounded-md border">
                {data.items.map((wf) => (
                  <button
                    key={wf.id}
                    onClick={() => navigate(`/workflows/${wf.id}`)}
                    className="flex w-full items-center gap-4 p-4 text-left hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{wf.query}</span>
                        <WorkflowStatusBadge status={wf.status} />
                      </div>
                      {wf.notes && (
                        <div className="text-sm text-muted-foreground mt-1 truncate">{wf.notes}</div>
                      )}
                      <div className="text-xs text-muted-foreground mt-1">
                        {formatDate(wf.created_at)} · #{wf.id}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
              {data.total > 20 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-muted-foreground">
                    共 {data.total} 条，第 {data.page} 页
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      上一页
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page * 20 >= data.total}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      下一页
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="py-16 text-center">
              <div className="text-muted-foreground">还没有工作流</div>
              <Button className="mt-4" onClick={() => navigate('/workflows/new')}>
                <Plus className="mr-2 h-4 w-4" />
                创建第一个
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
