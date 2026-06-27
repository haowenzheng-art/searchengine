import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { usageApi } from '@/lib/api-services'
import { formatNumber } from '@/lib/utils'
import { Activity, Clock, Coins, Search, FileText, CheckCircle2, XCircle, Zap } from 'lucide-react'

export function UsagePage() {
  const { data: today, isLoading: todayLoading } = useQuery({
    queryKey: ['usage', 'today'],
    queryFn: usageApi.today,
    refetchInterval: 10000,
  })

  const { data: month } = useQuery({
    queryKey: ['usage', 'month'],
    queryFn: usageApi.month,
    refetchInterval: 30000,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">用量统计</h1>
        <p className="text-sm text-muted-foreground">查看今日和本月的 Agent 执行用量</p>
      </div>

      <div>
        <h2 className="text-lg font-medium mb-3">今日</h2>
        <div className="grid gap-4 md:grid-cols-4">
          <UsageCard
            title="工作流"
            value={today?.workflows_started}
            sub={`完成 ${today?.workflows_completed ?? 0} · 失败 ${today?.workflows_failed ?? 0}`}
            icon={Activity}
            loading={todayLoading}
          />
          <UsageCard
            title="工具调用"
            value={today?.tool_calls}
            icon={Zap}
            loading={todayLoading}
          />
          <UsageCard
            title="搜索查询"
            value={today?.search_queries}
            icon={Search}
            loading={todayLoading}
          />
          <UsageCard
            title="证据抓取"
            value={today?.evidence_fetched}
            icon={FileText}
            loading={todayLoading}
          />
          <UsageCard
            title="输入 tokens"
            value={today?.input_tokens}
            icon={Coins}
            loading={todayLoading}
          />
          <UsageCard
            title="输出 tokens"
            value={today?.output_tokens}
            icon={Coins}
            loading={todayLoading}
          />
          <UsageCard
            title="完成工作流"
            value={today?.workflows_completed}
            icon={CheckCircle2}
            loading={todayLoading}
          />
          <UsageCard
            title="失败工作流"
            value={today?.workflows_failed}
            icon={XCircle}
            loading={todayLoading}
          />
        </div>
      </div>

      <div>
        <h2 className="text-lg font-medium mb-3">本月</h2>
        <div className="grid gap-4 md:grid-cols-4">
          <UsageCard
            title="工作流"
            value={month?.workflows_started}
            sub={`完成 ${month?.workflows_completed ?? 0} · 失败 ${month?.workflows_failed ?? 0}`}
            icon={Clock}
          />
          <UsageCard
            title="工具调用"
            value={month?.tool_calls}
            icon={Zap}
          />
          <UsageCard
            title="输入 tokens"
            value={month?.input_tokens}
            icon={Coins}
          />
          <UsageCard
            title="输出 tokens"
            value={month?.output_tokens}
            icon={Coins}
          />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">关于计费</CardTitle>
          <CardDescription>当前为 Beta 阶段，所有用量免费</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            usage_records 表已记录每日用量（工作流数、工具调用、token 消耗）。
            正式计费上线后，将按 plan 配额限制：免费 10 次/天，Pro 100 次/月，Team 500 次/月。
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

interface UsageCardProps {
  title: string
  value: number | null | undefined
  sub?: string
  icon: React.ComponentType<{ className?: string }>
  loading?: boolean
}

function UsageCard({ title, value, sub, icon: Icon, loading }: UsageCardProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">{title}</div>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="text-2xl font-semibold mt-2">
          {loading ? '...' : formatNumber(value ?? 0)}
        </div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </CardContent>
    </Card>
  )
}
