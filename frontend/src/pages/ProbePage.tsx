import { useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Popconfirm,
  Progress,
  Row,
  Space,
  Table,
  Tag as AntTag,
  Typography,
  message,
} from 'antd'
import {
  DeleteOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ProbeJob, ProbeJobDetail } from '../api/types'

const { Text, Paragraph, Title } = Typography

// 任务状态 → 展示样式
const STATUS_META: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '排队中' },
  crawling: { color: 'processing', label: '抓取中' },
  extracting: { color: 'processing', label: 'AI 提取中' },
  done: { color: 'success', label: '待校对' },
  confirmed: { color: 'green', label: '已入库' },
  failed: { color: 'error', label: '失败' },
}

function statusTag(status: string) {
  const m = STATUS_META[status] || { color: 'default', label: status }
  return <AntTag color={m.color}>{m.label}</AntTag>
}

export default function ProbePage() {
  const qc = useQueryClient()
  const [urlText, setUrlText] = useState('')
  const [activeId, setActiveId] = useState<number | null>(null)

  const jobsQ = useQuery({
    queryKey: ['probe-jobs'],
    queryFn: api.listJobs,
    // 有任务在跑时自动轮询进度
    refetchInterval: (query) => {
      const data = query.state.data as ProbeJob[] | undefined
      const running = data?.some((j) =>
        ['pending', 'crawling', 'extracting'].includes(j.status),
      )
      return running ? 2500 : false
    },
  })

  const startMut = useMutation({
    mutationFn: (urls: string[]) => api.startProbe(urls),
    onSuccess: () => {
      message.success('已提交探测任务')
      setUrlText('')
      qc.invalidateQueries({ queryKey: ['probe-jobs'] })
    },
    onError: (e: any) => message.error(e?.response?.data?.detail || '提交失败'),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.deleteJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['probe-jobs'] }),
  })

  const submit = () => {
    const urls = urlText
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    if (!urls.length) {
      message.warning('请粘贴至少一个网址')
      return
    }
    startMut.mutate(urls)
  }

  const jobs = jobsQ.data || []

  return (
    <Row gutter={16}>
      <Col xs={24} md={9} lg={8}>
        <Card size="small" title="发起探测">
          <Paragraph type="secondary" style={{ fontSize: 12 }}>
            粘贴企业官网网址，每行一个（或用逗号分隔）。系统将抓取关键页面并用 AI
            生成结构化草稿，供你校对后入库。
          </Paragraph>
          <Input.TextArea
            rows={6}
            value={urlText}
            onChange={(e) => setUrlText(e.target.value)}
            placeholder={'https://www.example-lighting.com\nhttps://www.another.com'}
          />
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            block
            style={{ marginTop: 12 }}
            loading={startMut.isPending}
            onClick={submit}
          >
            开始探测
          </Button>
        </Card>
      </Col>

      <Col xs={24} md={15} lg={16}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
          <Title level={5} style={{ margin: 0, flex: 1 }}>
            探测任务
          </Title>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => qc.invalidateQueries({ queryKey: ['probe-jobs'] })}
          >
            刷新
          </Button>
        </div>

        {jobs.length === 0 ? (
          <Empty description="暂无任务" />
        ) : (
          <List
            dataSource={jobs}
            bordered
            renderItem={(j) => (
              <List.Item
                actions={[
                  <Button
                    key="review"
                    type="link"
                    disabled={!['done', 'confirmed'].includes(j.status)}
                    onClick={() => setActiveId(j.id)}
                  >
                    {j.status === 'confirmed' ? '查看' : '校对'}
                  </Button>,
                  <Popconfirm
                    key="del"
                    title="删除该任务？"
                    onConfirm={() => deleteMut.mutate(j.id)}
                  >
                    <Button type="link" danger icon={<DeleteOutlined />} />
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      {statusTag(j.status)}
                      <Text ellipsis style={{ maxWidth: 320 }}>
                        {j.url}
                      </Text>
                    </Space>
                  }
                  description={
                    <div>
                      <Progress
                        percent={j.progress}
                        size="small"
                        status={j.status === 'failed' ? 'exception' : undefined}
                      />
                      {j.message && <Text type="secondary">{j.message}</Text>}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Col>

      {activeId != null && (
        <DraftDrawer jobId={activeId} onClose={() => setActiveId(null)} />
      )}
    </Row>
  )
}

// ---------- 草稿校对抽屉 ----------
function DraftDrawer({ jobId, onClose }: { jobId: number; onClose: () => void }) {
  const qc = useQueryClient()
  const [form] = Form.useForm()
  const [rawArrays, setRawArrays] = useState('')

  const { data: job, isLoading } = useQuery<ProbeJobDetail>({
    queryKey: ['probe-job', jobId],
    queryFn: () => api.getJob(jobId),
  })

  // 载入草稿到表单 + 数组 JSON 编辑区
  const draft = job?.draft || {}
  useMemo(() => {
    if (!job) return
    const c = draft.company || {}
    form.setFieldsValue({
      name: c.name,
      name_cn: c.name_cn,
      website: c.website,
      hq_country: c.hq_country,
      hq_city: c.hq_city,
      founded_year: c.founded_year,
      summary: c.summary,
      philosophy: c.philosophy,
      history: c.history,
    })
    setRawArrays(
      JSON.stringify(
        {
          tags: draft.tags || [],
          product_lines: draft.product_lines || [],
          offices: draft.offices || [],
          downloads: draft.downloads || [],
          news: draft.news || [],
        },
        null,
        2,
      ),
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job])

  const confirmMut = useMutation({
    mutationFn: (payload: any) => api.confirmJob(jobId, payload),
    onSuccess: () => {
      message.success('已入库')
      qc.invalidateQueries({ queryKey: ['probe-jobs'] })
      qc.invalidateQueries({ queryKey: ['companies'] })
      qc.invalidateQueries({ queryKey: ['facets'] })
      onClose()
    },
    onError: (e: any) => message.error(e?.response?.data?.detail || '入库失败'),
  })

  const onConfirm = async () => {
    const values = await form.validateFields()
    let arrays: any = {}
    try {
      arrays = JSON.parse(rawArrays || '{}')
    } catch {
      message.error('标签/产品线等 JSON 格式有误，请检查')
      return
    }
    const payload = {
      company: {
        ...(draft.company || {}),
        ...values,
      },
      tags: arrays.tags || [],
      product_lines: arrays.product_lines || [],
      offices: arrays.offices || [],
      downloads: arrays.downloads || [],
      news: arrays.news || [],
    }
    confirmMut.mutate(payload)
  }

  const confirmed = job?.status === 'confirmed'
  const dl = draft.downloads || []
  const news = draft.news || []

  return (
    <Drawer
      open
      width={640}
      title="校对 AI 草稿"
      onClose={onClose}
      extra={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button
            type="primary"
            loading={confirmMut.isPending}
            disabled={confirmed}
            onClick={onConfirm}
          >
            {confirmed ? '已入库' : '确认入库'}
          </Button>
        </Space>
      }
    >
      {isLoading ? (
        <Empty description="加载中…" />
      ) : !job?.draft ? (
        <Alert type="info" message="该任务暂无可用草稿" />
      ) : (
        <>
          {confirmed && (
            <Alert
              type="success"
              showIcon
              style={{ marginBottom: 12 }}
              message="该任务草稿已入库，可前往企业库查看。"
            />
          )}
          <Form form={form} layout="vertical">
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item name="name" label="名称" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="name_cn" label="中文名">
                  <Input />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="website" label="官网">
              <Input />
            </Form.Item>
            <Row gutter={12}>
              <Col span={8}>
                <Form.Item name="hq_country" label="总部国家">
                  <Input />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="hq_city" label="总部城市">
                  <Input />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="founded_year" label="成立年份">
                  <InputNumber style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="summary" label="概述">
              <Input.TextArea rows={2} />
            </Form.Item>
            <Form.Item name="philosophy" label="企业理念">
              <Input.TextArea rows={2} />
            </Form.Item>
            <Form.Item name="history" label="企业历史">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>

          <Card size="small" title={`可下载资源（${dl.length}）`} style={{ marginBottom: 12 }}>
            <Table
              size="small"
              rowKey={(_, i) => String(i)}
              pagination={false}
              dataSource={dl}
              columns={[
                { title: '标题', dataIndex: 'title', ellipsis: true },
                { title: '类型', dataIndex: 'resource_type', width: 90 },
                {
                  title: '链接',
                  dataIndex: 'url',
                  ellipsis: true,
                  render: (v: string) => (
                    <a href={v} target="_blank" rel="noreferrer">
                      {v}
                    </a>
                  ),
                },
              ]}
              locale={{ emptyText: '无' }}
            />
          </Card>
          <Card size="small" title={`相关新闻（${news.length}）`} style={{ marginBottom: 12 }}>
            <List
              size="small"
              dataSource={news}
              locale={{ emptyText: '无' }}
              renderItem={(n: any) => (
                <List.Item>
                  <a href={n.url} target="_blank" rel="noreferrer">
                    {n.title || n.url}
                  </a>
                </List.Item>
              )}
            />
          </Card>

          <Typography.Text type="secondary">
            标签 / 产品线 / 机构 / 下载 / 新闻（可直接编辑 JSON 后入库）
          </Typography.Text>
          <Input.TextArea
            value={rawArrays}
            onChange={(e) => setRawArrays(e.target.value)}
            autoSize={{ minRows: 8, maxRows: 20 }}
            style={{ marginTop: 6, fontFamily: 'monospace', fontSize: 12 }}
          />

          {job.log && (
            <Card size="small" title="抓取日志" style={{ marginTop: 12 }}>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, margin: 0 }}>{job.log}</pre>
            </Card>
          )}
        </>
      )}
    </Drawer>
  )
}
