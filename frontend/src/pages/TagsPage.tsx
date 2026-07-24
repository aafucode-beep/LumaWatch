import { useMemo, useState } from 'react'
import {
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag as AntTag,
  Typography,
  message,
} from 'antd'
import {
  DeleteOutlined,
  EditOutlined,
  MergeCellsOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Tag } from '../api/types'

const { Text, Title } = Typography

const DIMENSIONS = ['产品类型', '应用场景', '地区', '企业属性']
const DIM_COLORS: Record<string, string> = {
  产品类型: 'blue',
  应用场景: 'green',
  地区: 'orange',
  企业属性: 'purple',
}

export default function TagsPage() {
  const qc = useQueryClient()
  const [editForm] = Form.useForm()
  const [createForm] = Form.useForm()
  const [mergeForm] = Form.useForm()
  const [editing, setEditing] = useState<Tag | null>(null)
  const [creating, setCreating] = useState(false)
  const [merging, setMerging] = useState(false)
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const tagsQ = useQuery({ queryKey: ['tags'], queryFn: api.listTags })
  const tags = tagsQ.data || []

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['tags'] })
    qc.invalidateQueries({ queryKey: ['facets'] })
    qc.invalidateQueries({ queryKey: ['companies'] })
  }

  const createMut = useMutation({
    mutationFn: (body: any) => api.createTag(body),
    onSuccess: () => {
      message.success('已创建')
      setCreating(false)
      createForm.resetFields()
      invalidate()
    },
    onError: (e: any) => message.error(e?.response?.data?.detail || '创建失败'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: number; body: any }) => api.updateTag(id, body),
    onSuccess: () => {
      message.success('已保存')
      setEditing(null)
      invalidate()
    },
    onError: (e: any) => message.error(e?.response?.data?.detail || '保存失败'),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.deleteTag(id),
    onSuccess: () => {
      message.success('已删除')
      invalidate()
    },
  })

  const mergeMut = useMutation({
    mutationFn: ({ sources, target }: { sources: number[]; target: number }) =>
      api.mergeTags(sources, target),
    onSuccess: () => {
      message.success('已合并')
      setMerging(false)
      setSelectedIds([])
      mergeForm.resetFields()
      invalidate()
    },
    onError: (e: any) => message.error(e?.response?.data?.detail || '合并失败'),
  })

  // 按维度分组
  const grouped = useMemo(() => {
    const map: Record<string, Tag[]> = {}
    for (const t of tags) (map[t.dimension] ||= []).push(t)
    return map
  }, [tags])

  const openEdit = (t: Tag) => {
    editForm.setFieldsValue({ name: t.name, dimension: t.dimension, description: t.description })
    setEditing(t)
  }

  const selectedTags = tags.filter((t) => selectedIds.includes(t.id))

  const columns = [
    {
      title: '标签',
      dataIndex: 'name',
      render: (_: any, t: Tag) => (
        <AntTag color={DIM_COLORS[t.dimension]}>{t.name}</AntTag>
      ),
    },
    { title: '关联企业', dataIndex: 'company_count', width: 100 },
    { title: '描述', dataIndex: 'description', ellipsis: true, render: (v: string) => v || <Text type="secondary">—</Text> },
    {
      title: '操作',
      width: 120,
      render: (_: any, t: Tag) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(t)} />
          <Popconfirm title="删除该标签？（会解除与企业的关联）" onConfirm={() => deleteMut.mutate(t.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0, flex: 1 }}>
          标签管理 · 共 {tags.length} 个
        </Title>
        <Space>
          <Button
            icon={<MergeCellsOutlined />}
            disabled={selectedIds.length < 2}
            onClick={() => {
              mergeForm.setFieldsValue({ target: selectedIds[0] })
              setMerging(true)
            }}
          >
            合并所选（{selectedIds.length}）
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>
            新建标签
          </Button>
        </Space>
      </div>

      <Text type="secondary">
        勾选两个及以上标签可合并去重（清理 AI 产生的重复/噪点标签）。合并后所有企业关联会迁移到目标标签。
      </Text>

      <Row gutter={16} style={{ marginTop: 12 }}>
        {DIMENSIONS.concat(
          Object.keys(grouped).filter((d) => !DIMENSIONS.includes(d)),
        ).map((dim) => {
          const list = grouped[dim] || []
          return (
            <Col xs={24} lg={12} key={dim} style={{ marginBottom: 16 }}>
              <Card
                size="small"
                title={
                  <Space>
                    <AntTag color={DIM_COLORS[dim] || 'default'}>{dim}</AntTag>
                    <Text type="secondary">{list.length}</Text>
                  </Space>
                }
              >
                {list.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无" />
                ) : (
                  <Table
                    size="small"
                    rowKey="id"
                    dataSource={list}
                    columns={columns as any}
                    pagination={false}
                    rowSelection={{
                      selectedRowKeys: selectedIds,
                      onChange: (keys) => setSelectedIds(keys as number[]),
                      preserveSelectedRowKeys: true,
                    }}
                  />
                )}
              </Card>
            </Col>
          )
        })}
      </Row>

      {/* 新建 */}
      <Modal
        title="新建标签"
        open={creating}
        onCancel={() => setCreating(false)}
        onOk={() => createForm.submit()}
        confirmLoading={createMut.isPending}
      >
        <Form form={createForm} layout="vertical" onFinish={(v) => createMut.mutate(v)}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="dimension" label="维度" initialValue="产品类型" rules={[{ required: true }]}>
            <Select options={DIMENSIONS.map((d) => ({ label: d, value: d }))} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑 */}
      <Modal
        title="编辑标签"
        open={!!editing}
        onCancel={() => setEditing(null)}
        onOk={() => editForm.submit()}
        confirmLoading={updateMut.isPending}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={(v) => editing && updateMut.mutate({ id: editing.id, body: v })}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="dimension" label="维度" rules={[{ required: true }]}>
            <Select options={DIMENSIONS.map((d) => ({ label: d, value: d }))} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 合并 */}
      <Modal
        title="合并标签"
        open={merging}
        onCancel={() => setMerging(false)}
        onOk={() => mergeForm.submit()}
        confirmLoading={mergeMut.isPending}
      >
        <Text type="secondary">将所选标签合并为一个目标标签，其余标签会被删除。</Text>
        <div style={{ margin: '12px 0' }}>
          <Space wrap>
            {selectedTags.map((t) => (
              <AntTag key={t.id} color={DIM_COLORS[t.dimension]}>
                {t.name}（{t.company_count}）
              </AntTag>
            ))}
          </Space>
        </div>
        <Divider style={{ margin: '8px 0' }} />
        <Form
          form={mergeForm}
          layout="vertical"
          onFinish={(v) =>
            mergeMut.mutate({
              sources: selectedIds.filter((id) => id !== v.target),
              target: v.target,
            })
          }
        >
          <Form.Item name="target" label="保留为（目标标签）" rules={[{ required: true }]}>
            <Select
              options={selectedTags.map((t) => ({
                label: `${t.name}（${t.dimension}）`,
                value: t.id,
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
