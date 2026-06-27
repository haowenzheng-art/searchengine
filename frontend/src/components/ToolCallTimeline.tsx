import { useState } from 'react'
import {
  Search,
  FileText,
  Gauge,
  Workflow as WorkflowIcon,
  AlertTriangle,
  Save,
  Brain,
  ChevronRight,
  ChevronDown,
  Clock,
  Coins,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import type { ToolCall } from '@/lib/types'
import { Badge } from '@/components/ui/badge'
import { cn, formatDuration, formatNumber, formatDate } from '@/lib/utils'

const toolIcon: Record<string, React.ComponentType<{ className?: string }>> = {
  search_web: Search,
  score_evidence: Gauge,
  fetch_page: FileText,
  extract_workflow: WorkflowIcon,
  identify_pain_points: AlertTriangle,
  design_agent_flow: WorkflowIcon,
  calculate_roi: Coins,
  save_report: Save,
  save_evidence: Save,
}

const toolLabel: Record<string, string> = {
  search_web: '搜索',
  score_evidence: '评分',
  fetch_page: '抓取',
  extract_workflow: '提取工作流',
  identify_pain_points: '识别痛点',
  design_agent_flow: '设计 Agent 流程',
  calculate_roi: '计算 ROI',
  save_report: '保存报告',
  save_evidence: '保存证据',
}

interface Props {
  toolCalls: ToolCall[]
  isLoading?: boolean
}

export function ToolCallTimeline({ toolCalls, isLoading }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  const toggle = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (isLoading && toolCalls.length === 0) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-md bg-muted animate-pulse" />
        ))}
      </div>
    )
  }

  if (toolCalls.length === 0) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <div>Agent 还没开始调用工具</div>
        <div className="text-xs mt-1">等待 LLM 决策第一步操作...</div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {toolCalls.map((tc, idx) => {
        const Icon = toolIcon[tc.tool_name] ?? Brain
        const label = toolLabel[tc.tool_name] ?? tc.tool_name
        const isExpanded = expanded.has(tc.id)
        const hasError = tc.error !== null && tc.error !== undefined
        const inputSummary = summarizeInput(tc.tool_name, tc.input_args)

        return (
          <div
            key={tc.id}
            className={cn(
              'rounded-md border bg-card transition-shadow',
              hasError && 'border-destructive/40 bg-destructive/5'
            )}
          >
            <button
              onClick={() => toggle(tc.id)}
              className="flex w-full items-start gap-3 p-3 text-left hover:bg-accent/30"
            >
              <div className="relative flex flex-col items-center">
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-full',
                    hasError
                      ? 'bg-destructive/15 text-destructive'
                      : 'bg-primary/15 text-primary'
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                {idx < toolCalls.length - 1 && (
                  <div className="absolute top-8 h-[calc(100%-1.5rem)] w-px bg-border" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm">{label}</span>
                  <Badge variant="outline" className="text-xs font-mono">
                    {tc.tool_name}
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    迭代 #{tc.iteration}
                  </Badge>
                  {hasError ? (
                    <Badge variant="destructive" className="text-xs gap-1">
                      <XCircle className="h-3 w-3" /> 失败
                    </Badge>
                  ) : (
                    <Badge variant="success" className="text-xs gap-1">
                      <CheckCircle2 className="h-3 w-3" /> 成功
                    </Badge>
                  )}
                </div>
                {inputSummary && (
                  <div className="text-sm text-muted-foreground mt-1 truncate">
                    {inputSummary}
                  </div>
                )}
                <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDuration(tc.duration_ms)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Coins className="h-3 w-3" />
                    {formatNumber(tc.input_tokens + tc.output_tokens)} tokens
                  </span>
                  <span>{formatDate(tc.created_at)}</span>
                </div>
              </div>
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground mt-1" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground mt-1" />
              )}
            </button>
            {isExpanded && (
              <div className="border-t bg-muted/30 p-3 space-y-3">
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">输入</div>
                  <pre className="text-xs bg-background rounded p-2 overflow-x-auto max-h-48">
                    {JSON.stringify(tc.input_args, null, 2)}
                  </pre>
                </div>
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">
                    {hasError ? '错误' : '输出'}
                  </div>
                  <pre className="text-xs bg-background rounded p-2 overflow-x-auto max-h-64">
                    {hasError
                      ? tc.error || '未知错误'
                      : JSON.stringify(tc.output_result, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function summarizeInput(toolName: string, input: Record<string, unknown>): string {
  if (!input) return ''
  switch (toolName) {
    case 'search_web':
      return `查询: ${input.query ?? ''}`.slice(0, 100)
    case 'fetch_page':
      return `URL: ${input.url ?? ''}`.slice(0, 100)
    case 'score_evidence':
      return `URL: ${input.url ?? ''}`.slice(0, 100)
    default:
      return ''
  }
}
