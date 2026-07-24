import { useState } from 'react'
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tag as AntTag,
  Tree,
  Typography,
  message,
} from 'antd'
import { EditOutlined, StarFilled, DeleteOutlined, LinkOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { CompanyDetail, ProductLine, Tag } from '../api/types'

const { Text, Paragraph, Title } = Typography
const DIM_COLORS: Record<string, string> = {
  产品类型: 'blue',
  应用场景: 'green',
  地区: 'orange',
  企业属性: 'purple',
}

function plToTree(items: ProductLine[]): any[] {
  return items.map((p) => ({
    title: (
      <div>
        <Text strong>{p.name}</Text>
        {p.category && <AntTag style={{ marginLeft: 8 }}>{p.category}</AntTag>}
        {p.description && (
          <div><Text type="secondary">{p.description}</Text></div>
        )}
      </div>
    ),
    key: p.id ?? p.name,
    children: p.children && p.children.length ? plToTree(p.children) : undefined,
  }))
}

export default function CompanyDetailPage() {
  const { id } = useParams()
  const cid = Number(id)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [form] = Form.useForm()

  const { data: company, isLoading } = useQuery({
    queryKey: ['company', cid],
    queryFn: () => api.getCompany(cid),
  })
  const { data: allTags } = useQuery({ queryKey: ['tags'], queryFn: api.listTags })

  const updateMut = useMutation({
    mutationFn: (body: any) => api.updateCompany(cid, body),
    onSuccess: () => {
      message.success('已保存')
      setEditing(false)
      qc.invalidateQueries({ queryKey: ['company', cid] })
      qc.invalidateQueries({ queryKey: ['companies'] })
      qc.invalidateQueries({ queryKey: ['facets'] })
    },
    onError: (e: any) => message.error(e?.response?.data?.detail || '保存失败'),
  })

  const deleteMut = useMutation({
    mutationFn: () => api.deleteCompany(cid),
    onSuccess: () => {
      message.success('已删除')
      navigate('/')
    },
  })

  if (isLoading) return <Spin />
  if (!company) return <Empty description="企业不存在" />

  const openEdit = () => {
    form.setFieldsValue({
      ...company,
      tag_ids: company.tags.map((t) => t.id),
    })
    setEditing(true)
  }

  const submitEdit = async () => {
    const values = await form.validateFields()
    updateMut.mutate(values)
  }

  const toggleKey = (v: boolean) => updateMut.mutate({ is_key: v })

  return (
    <div>
      <Breadcrumb
        items={[
          { title: <a onClick={() => navigate('/')}>企业库</a> },
          { title: company.name },
        ]}
        style={{ marginBottom: 12 }}
      />

      <Card
        title={
          <Space>
            {company.is_key && <StarFilled style={{ color: '#faad14' }} />}
            <Title level={4} style={{ margin: 0 }}>
              {company.name}
            </Title>
            {company.name_cn && <Text type="secondary">{company.name_cn}</Text>}
            {company.status === 'draft' && <AntTag color="warning">草稿</AntTag>}
          </Space>
        }
        extra={
          <Space>
            <Space size={4}>
              <Text type="secondary">重点</Text>
              <Switch checked={company.is_key} onChange={toggleKey} />
            </Space>
            <Button icon={<EditOutlined />} onClick={openEdit}>
              编辑
            </Button>
            <Popconfirm title="确认删除该企业？" onConfirm={() => deleteMut.mutate()}>
              <Button danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        }
      >
        <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered>
          <Descriptions.Item label="官网">
            {company.website ? (
              <a href={company.website} target="_blank" rel="noreferrer">
                {company.website}
              </a>
            ) : (
              '—'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="总部">
            {[company.hq_country, company.hq_city].filter(Boolean).join(' · ') || '—'}
          </Descriptions.Item>
          <Descriptions.Item label="成立年份">{company.founded_year || '—'}</Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {new Date(company.updated_at).toLocaleString()}
          </Descriptions.Item>
        </Descriptions>

        <div style={{ marginTop: 12 }}>
          {company.tags.map((t) => (
            <AntTag
              key={t.id}
              color={DIM_COLORS[t.dimension]}
              className="tag-clickable"
              onClick={() => navigate(`/?tags=${t.id}`)}
            >
              {t.name}
            </AntTag>
          ))}
        </div>

        {company.summary && (
          <Paragraph style={{ marginTop: 12 }}>{company.summary}</Paragraph>
        )}
      </Card>

      {company.insights.length > 0 && (
        <Card size="small" title={`关键情报（${company.insights.length}）`} style={{ marginTop: 16 }}>
          <List
            dataSource={company.insights}
            renderItem={(insight) => (
              <List.Item>
                <div style={{ width: '100%' }}>
                  <Space>
                    <AntTag color="geekblue">{insight.category}</AntTag>
                    <Text strong>{insight.title}</Text>
                  </Space>
                  <Paragraph style={{ margin: '8px 0 4px' }}>{insight.summary}</Paragraph>
                  {insight.relevance && (
                    <Paragraph type="secondary" style={{ marginBottom: 4 }}>
                      研究价值：{insight.relevance}
                    </Paragraph>
                  )}
                  {insight.source_url && (
                    <a href={insight.source_url} target="_blank" rel="noreferrer">
                      <LinkOutlined /> 查看来源
                    </a>
                  )}
                </div>
              </List.Item>
            )}
          />
        </Card>
      )}

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card size="small" title="企业理念" style={{ marginBottom: 16 }}>
            <Paragraph>{company.philosophy || <Text type="secondary">暂无</Text>}</Paragraph>
          </Card>
          <Card size="small" title="企业历史" style={{ marginBottom: 16 }}>
            <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
              {company.history || <Text type="secondary">暂无</Text>}
            </Paragraph>
          </Card>
          <Card size="small" title={`代表项目（${company.projects.length}）`} style={{ marginBottom: 16 }}>
            {company.projects.length ? (
              <List
                size="small"
                dataSource={company.projects}
                renderItem={(project) => (
                  <List.Item>
                    <div style={{ width: '100%' }}>
                      <Space wrap>
                        <Text strong>{project.name}</Text>
                        {project.application && <AntTag color="cyan">{project.application}</AntTag>}
                        {project.completion_year && <Text type="secondary">{project.completion_year}</Text>}
                      </Space>
                      {(project.location || project.country) && (
                        <div><Text type="secondary">{[project.country, project.location].filter(Boolean).join(' · ')}</Text></div>
                      )}
                      {project.summary && <Paragraph style={{ margin: '6px 0' }}>{project.summary}</Paragraph>}
                      {project.products && <div><Text>涉及产品：{project.products}</Text></div>}
                      {project.source_url && (
                        <a href={project.source_url} target="_blank" rel="noreferrer"><LinkOutlined /> 来源</a>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            ) : (
              <Text type="secondary">暂无</Text>
            )}
          </Card>
          <Card size="small" title="产品线架构">
            {company.product_lines.length ? (
              <Tree treeData={plToTree(company.product_lines)} defaultExpandAll selectable={false} />
            ) : (
              <Text type="secondary">暂无</Text>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card size="small" title="国际网络机构" style={{ marginBottom: 16 }}>
            {company.offices.length ? (
              <List
                size="small"
                dataSource={company.offices}
                renderItem={(o) => (
                  <List.Item>
                    <Space>
                      <AntTag>{o.office_type}</AntTag>
                      <Text>{[o.region, o.country, o.city].filter(Boolean).join(' / ')}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Text type="secondary">暂无</Text>
            )}
          </Card>

          <Card size="small" title={`可下载资源（${company.downloads.length}）`} style={{ marginBottom: 16 }}>
            <Table
              size="small"
              rowKey={(r) => r.id ?? r.url}
              pagination={false}
              dataSource={company.downloads}
              columns={[
                { title: '标题', dataIndex: 'title', ellipsis: true },
                { title: '类型', dataIndex: 'resource_type', width: 90, render: (v) => <AntTag>{v}</AntTag> },
                {
                  title: '链接',
                  width: 60,
                  render: (_, r) => (
                    <a href={r.url} target="_blank" rel="noreferrer">
                      <LinkOutlined />
                    </a>
                  ),
                },
              ]}
              locale={{ emptyText: '暂无' }}
            />
          </Card>

          <Card size="small" title={`相关新闻（${company.news.length}）`}>
            {company.news.length ? (
              <List
                size="small"
                dataSource={company.news}
                renderItem={(n) => (
                  <List.Item>
                    <div>
                      <a href={n.url} target="_blank" rel="noreferrer">
                        {n.title}
                      </a>
                      {n.published_date && <Text type="secondary"> · {n.published_date}</Text>}
                      {n.summary && <div><Text type="secondary">{n.summary}</Text></div>}
                    </div>
                  </List.Item>
                )}
              />
            ) : (
              <Text type="secondary">暂无</Text>
            )}
          </Card>

          <Card size="small" title={`来源证据（${company.evidence.length}）`} style={{ marginTop: 16 }}>
            {company.evidence.length ? (
              <List
                size="small"
                dataSource={company.evidence}
                renderItem={(evidence) => (
                  <List.Item>
                    <div>
                      <Text strong>{evidence.field}</Text>
                      {evidence.snippet && (
                        <Paragraph style={{ margin: '4px 0' }}>“{evidence.snippet}”</Paragraph>
                      )}
                      {evidence.source_url && (
                        <a href={evidence.source_url} target="_blank" rel="noreferrer"><LinkOutlined /> 原始页面</a>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            ) : (
              <Text type="secondary">暂无可核验引用</Text>
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        title="编辑企业信息"
        open={editing}
        onCancel={() => setEditing(false)}
        onOk={submitEdit}
        confirmLoading={updateMut.isPending}
        width={640}
      >
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
          <Form.Item name="tag_ids" label="标签">
            <Select
              mode="multiple"
              allowClear
              placeholder="选择标签"
              options={(allTags || []).map((t: Tag) => ({
                label: `${t.name}（${t.dimension}）`,
                value: t.id,
              }))}
              filterOption={(input, opt) =>
                (opt?.label as string).toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item name="summary" label="概述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="philosophy" label="企业理念">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="history" label="企业历史">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="is_key" label="重点企业" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
