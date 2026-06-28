import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import mermaid from 'mermaid'
import {
  ArrowLeft,
  Trash2,
  Loader2,
  FileText,
  ExternalLink,
  Link as LinkIcon,
  Clock,
  AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { WorkflowStatusBadge } from '@/components/WorkflowStatusBadge'
import { ToolCallTimeline } from '@/components/ToolCallTimeline'
import { workflowApi } from '@/lib/api-services'
import { formatDate, formatDuration, formatNumber } from '@/lib/utils'

export function WorkflowDetailPage() {
  const params = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const workflowId = Number(params.id)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const { data: wf, isLoading } = useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => workflowApi.get(workflowId),
    refetchInterval: (q) => {
      const status = q.state.data?.status
      return status === 'running' || status === 'pending' ? 2000 : false
    },
  })

  const { data: runs } = useQuery({
    queryKey: ['workflow-runs', workflowId],
    queryFn: () => workflowApi.runs(workflowId),
    refetchInterval: (q) => {
      const latest = q.state.data?.[0]
      return latest?.status === 'running' ? 2000 : false
    },
  })

  const latestRun = runs?.[0]
  const runId = latestRun?.id

  const { data: toolCalls, isLoading: tcLoading } = useQuery({
    queryKey: ['tool-calls', workflowId, runId],
    queryFn: () => workflowApi.toolCalls(workflowId, runId!),
    enabled: runId !== undefined,
    refetchInterval: () => {
      const wfStatus = qc.getQueryData<{ status: string }>(['workflow', workflowId])?.status
      return wfStatus === 'running' || wfStatus === 'pending' ? 2000 : false
    },
  })

  const { data: evidence } = useQuery({
    queryKey: ['evidence', workflowId],
    queryFn: () => workflowApi.evidence(workflowId),
    refetchInterval: () => {
      const wfStatus = qc.getQueryData<{ status: string }>(['workflow', workflowId])?.status
      return wfStatus === 'running' || wfStatus === 'pending' ? 5000 : false
    },
  })

  const handleDelete = async () => {
    try {
      await workflowApi.delete(workflowId)
      toast.success('工作流已删除')
      navigate('/dashboard')
    } catch {
      // toast 由拦截器处理
    } finally {
      setDeleteOpen(false)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
        <div className="h-32 bg-muted animate-pulse rounded" />
      </div>
    )
  }

  if (!wf) {
    return <div className="text-muted-foreground">工作流不存在或无权访问</div>
  }

  const isRunning = wf.status === 'running' || wf.status === 'pending'
  const progress = computeProgress(wf.status, latestRun?.current_iteration ?? 0, toolCalls?.length ?? 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-semibold tracking-tight truncate">{wf.query}</h1>
            <WorkflowStatusBadge status={wf.status} />
          </div>
          <div className="text-sm text-muted-foreground mt-1">
            #{wf.id} · 创建于 {formatDate(wf.created_at)}
            {wf.completed_at && ` · 完成于 ${formatDate(wf.completed_at)}`}
          </div>
        </div>
        <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" disabled={isRunning}>
              <Trash2 className="mr-2 h-4 w-4" />
              删除
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>删除工作流？</DialogTitle>
              <DialogDescription>
                确认删除工作流 #{wf.id}？将级联删除所有 agent runs、tool calls、evidence。此操作不可撤销。
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteOpen(false)}>
                取消
              </Button>
              <Button variant="destructive" onClick={handleDelete}>
                删除
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {wf.notes && (
        <Card>
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground mb-1">备注</div>
            <div className="text-sm whitespace-pre-wrap">{wf.notes}</div>
          </CardContent>
        </Card>
      )}

      {wf.error && (
        <Card className="border-destructive/50">
          <CardContent className="p-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
              <div>
                <div className="font-medium text-destructive">执行失败</div>
                <div className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">{wf.error}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {isRunning && (
        <Card>
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span className="text-sm font-medium">Agent 正在执行</span>
              </div>
              <span className="text-sm text-muted-foreground">{progress}%</span>
            </div>
            <Progress value={progress} />
            <div className="text-xs text-muted-foreground">
              迭代 {latestRun?.current_iteration ?? 0} · 已调用 {toolCalls?.length ?? 0} 次工具
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="timeline">
        <TabsList>
          <TabsTrigger value="timeline">
            时间线 ({toolCalls?.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="evidence">
            证据链 ({evidence?.length ?? 0})
          </TabsTrigger>
          {wf.status === 'completed' && latestRun?.final_output && (
            <TabsTrigger value="report">
              <FileText className="h-3 w-3 mr-1" />
              报告
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="timeline" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Agent 执行轨迹</CardTitle>
            </CardHeader>
            <CardContent>
              {latestRun ? (
                <>
                  <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
                    <span>Run #{latestRun.id}</span>
                    <Badge variant={latestRun.status === 'completed' ? 'success' : latestRun.status === 'failed' ? 'destructive' : 'secondary'}>
                      {latestRun.status}
                    </Badge>
                    <span>迭代 {latestRun.current_iteration}</span>
                    {latestRun.ended_at && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDuration(
                          new Date(latestRun.ended_at).getTime() - new Date(latestRun.started_at).getTime()
                        )}
                      </span>
                    )}
                  </div>
                  <ToolCallTimeline toolCalls={toolCalls ?? []} isLoading={tcLoading} />
                </>
              ) : (
                <div className="py-8 text-center text-muted-foreground">
                  Agent 尚未启动
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="evidence" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">证据链</CardTitle>
            </CardHeader>
            <CardContent>
              {evidence && evidence.length > 0 ? (
                <div className="space-y-3">
                  {evidence.map((e) => (
                    <div key={e.id} className="border rounded-md p-3">
                      <div className="flex items-start gap-2">
                        <LinkIcon className="h-4 w-4 mt-0.5 text-muted-foreground" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <a
                              href={e.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-sm hover:underline truncate"
                            >
                              {e.title || e.url}
                            </a>
                            <ExternalLink className="h-3 w-3 text-muted-foreground" />
                          </div>
                          <div className="text-xs text-muted-foreground mt-1 truncate">{e.url}</div>
                          {e.snippet && (
                            <div className="text-sm text-muted-foreground mt-1 line-clamp-2">{e.snippet}</div>
                          )}
                          <div className="flex items-center gap-2 mt-2 flex-wrap">
                            <Badge variant={e.score >= 7 ? 'success' : e.score >= 4 ? 'warning' : 'secondary'}>
                              score {e.score.toFixed(1)}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              Layer {e.score_layer}
                            </Badge>
                            {e.is_homepage && <Badge variant="warning" className="text-xs">首页</Badge>}
                            {e.is_disambiguation && <Badge variant="warning" className="text-xs">歧义</Badge>}
                            {e.word_count > 0 && (
                              <span className="text-xs text-muted-foreground">
                                {formatNumber(e.word_count)} 字
                              </span>
                            )}
                            {e.score_reason && (
                              <span className="text-xs text-muted-foreground italic">
                                {e.score_reason}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-muted-foreground">
                  还没有收集到证据
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {wf.status === 'completed' && latestRun?.final_output && (
          <TabsContent value="report" className="mt-4 space-y-4">
            <ReportView finalOutput={latestRun.final_output} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}

function buildWorkflowDiagram(finalOutput: Record<string, unknown>): string {
  const steps = (finalOutput.workflow as { steps?: Array<{ step_name: string }> })?.steps ?? []
  if (steps.length === 0) {
    return 'flowchart TD\n  empty["暂无工作流步骤"]'
  }
  const lines = ['flowchart TD']
  steps.forEach((step, idx) => {
    const id = `S${idx}`
    const label = step.step_name.replace(/"/g, '#quot;')
    lines.push(`  ${id}["${label}"]`)
    if (idx > 0) {
      lines.push(`  S${idx - 1} --> ${id}`)
    }
  })
  return lines.join('\n')
}

function ReportView({ finalOutput }: { finalOutput: Record<string, unknown> }) {
  const diagramRef = useRef<HTMLDivElement>(null)
  const diagram = buildWorkflowDiagram(finalOutput)

  useEffect(() => {
    if (!diagramRef.current) return
    mermaid.initialize({ startOnLoad: false, theme: 'default' })
    mermaid
      .render('workflow-report-diagram', diagram)
      .then(({ svg }) => {
        if (diagramRef.current) {
          diagramRef.current.innerHTML = svg
        }
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error('mermaid render failed', err)
        if (diagramRef.current) {
          diagramRef.current.textContent = '流程图渲染失败，请查看原始数据'
        }
      })
  }, [diagram])

  const summary = (finalOutput.summary as string) ?? ''
  const painPoints = (finalOutput.pain_points as Array<{ description: string; step_name?: string; time_pct?: number; root_cause?: string }>) ?? []
  const agentFlow = (finalOutput.agent_flow as { intervention_points?: Array<{ step_name: string; ai_action: string; human_approval: boolean; expected_effect: string }>; overall_strategy?: string }) ?? {}
  const roi = (finalOutput.roi as { annual_cost?: number; annual_savings?: number; roi_pct?: number; confidence?: string; assumptions?: string[] }) ?? {}

  return (
    <>
      {summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">整体结论</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{summary}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">工作流流程图</CardTitle>
        </CardHeader>
        <CardContent>
          <div ref={diagramRef} className="flex justify-center overflow-x-auto" />
        </CardContent>
      </Card>

      {painPoints.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">痛点分析</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {painPoints.map((p, idx) => (
                <div key={idx} className="border rounded-md p-3">
                  <div className="font-medium text-sm">{p.description}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    所在步骤：{p.step_name ?? '-'} · 耗时占比：{p.time_pct ?? 0}%
                  </div>
                  {p.root_cause && (
                    <div className="text-xs text-muted-foreground mt-1">根因：{p.root_cause}</div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {(agentFlow.intervention_points?.length ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">AI 介入方案</CardTitle>
          </CardHeader>
          <CardContent>
            {agentFlow.overall_strategy && (
              <p className="text-sm text-muted-foreground mb-3">{agentFlow.overall_strategy}</p>
            )}
            <div className="space-y-3">
              {agentFlow.intervention_points?.map((point, idx) => (
                <div key={idx} className="border rounded-md p-3">
                  <div className="font-medium text-sm">
                    {point.step_name}
                    {point.human_approval && (
                      <Badge variant="outline" className="ml-2 text-xs">需人工审批</Badge>
                    )}
                  </div>
                  <div className="text-sm mt-1">{point.ai_action}</div>
                  <div className="text-xs text-muted-foreground mt-1">预期效果：{point.expected_effect}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {roi.roi_pct !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">ROI 预估</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <div className="text-xs text-muted-foreground">年化成本</div>
                <div className="text-lg font-semibold">¥{formatNumber(roi.annual_cost ?? 0)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">年化收益</div>
                <div className="text-lg font-semibold">¥{formatNumber(roi.annual_savings ?? 0)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">ROI</div>
                <div className="text-lg font-semibold">{roi.roi_pct}%</div>
              </div>
            </div>
            {roi.assumptions && roi.assumptions.length > 0 && (
              <div className="mt-3">
                <div className="text-xs text-muted-foreground mb-1">关键假设</div>
                <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
                  {roi.assumptions.map((a, idx) => (
                    <li key={idx}>{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </>
  )
}

function computeProgress(status: string, iteration: number, toolCallCount: number): number {
  if (status === 'completed') return 100
  if (status === 'failed') return 100
  if (status === 'pending') return 5
  const iterProgress = Math.min((iteration / 20) * 80, 80)
  const tcProgress = Math.min(toolCallCount * 5, 15)
  return Math.min(iterProgress + tcProgress + 5, 95)
}
