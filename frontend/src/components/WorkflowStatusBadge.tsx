import { Badge } from '@/components/ui/badge'
import type { WorkflowStatus } from '@/lib/types'
import { Loader2, CheckCircle2, XCircle, Clock, Ban } from 'lucide-react'

const config: Record<WorkflowStatus, { label: string; variant: 'default' | 'success' | 'destructive' | 'secondary' | 'warning'; icon: React.ComponentType<{ className?: string }> }> = {
  pending: { label: '排队中', variant: 'secondary', icon: Clock },
  running: { label: '运行中', variant: 'default', icon: Loader2 },
  completed: { label: '已完成', variant: 'success', icon: CheckCircle2 },
  failed: { label: '失败', variant: 'destructive', icon: XCircle },
  cancelled: { label: '已取消', variant: 'warning', icon: Ban },
}

export function WorkflowStatusBadge({ status }: { status: WorkflowStatus }) {
  const c = config[status] ?? config.pending
  return (
    <Badge variant={c.variant} className="gap-1">
      <c.icon className={c.icon === Loader2 ? 'h-3 w-3 animate-spin' : 'h-3 w-3'} />
      {c.label}
    </Badge>
  )
}
