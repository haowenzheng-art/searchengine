import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Loader2, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { workflowApi } from '@/lib/api-services'

const schema = z.object({
  query: z
    .string()
    .min(3, '查询至少 3 个字符')
    .max(255, '查询最多 255 个字符'),
  notes: z.string().max(2000, '备注最多 2000 个字符').optional(),
})
type FormData = z.infer<typeof schema>

const EXAMPLES = [
  '招聘筛选流程',
  '保险理赔流程',
  '电商售后处理',
  '客服退款流程',
  '入职办理流程',
]

export function NewWorkflowPage() {
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
    watch,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { query: '', notes: '' },
  })

  const queryValue = watch('query')

  const onSubmit = async (data: FormData) => {
    try {
      const res = await workflowApi.create(data.query, data.notes || null)
      toast.success('工作流已创建，Agent 开始执行')
      navigate(`/workflows/${res.workflow_id}`)
    } catch {
      // toast 由拦截器处理
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">新建工作流</h1>
          <p className="text-sm text-muted-foreground">描述你想分析的流程，Agent 会自动搜索、抓取、评估证据并生成报告</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>查询</CardTitle>
          <CardDescription>用一句话描述你想分析的业务流程</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="query">流程描述</Label>
              <Input
                id="query"
                placeholder="例如：招聘筛选流程"
                {...register('query')}
              />
              {errors.query && <p className="text-sm text-destructive">{errors.query.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">备注（可选）</Label>
              <Textarea
                id="notes"
                placeholder="补充上下文，比如目标行业、特殊关注点"
                rows={4}
                {...register('notes')}
              />
              {errors.notes && <p className="text-sm text-destructive">{errors.notes.message}</p>}
            </div>

            <div className="space-y-2">
              <div className="text-sm text-muted-foreground">或者从示例开始：</div>
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((ex) => (
                  <Button
                    key={ex}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setValue('query', ex)}
                    className={queryValue === ex ? 'border-primary' : ''}
                  >
                    {ex}
                  </Button>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                取消
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                创建并启动
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Agent 会做什么？</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-2 text-sm text-muted-foreground">
            <li>1. 搜索流程相关的真实文章（DuckDuckGo）</li>
            <li>2. 评估每个 URL 的相关度（规则 + LLM 三层评分）</li>
            <li>3. 抓取高分证据的正文（Playwright + BS4）</li>
            <li>4. 提取结构化工作流、痛点、Agent 介入点</li>
            <li>5. 计算 ROI 并保存报告</li>
          </ol>
          <div className="text-xs text-muted-foreground mt-3 pt-3 border-t">
            耗时约 5-10 分钟。可在工作流详情页查看实时进度。
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
