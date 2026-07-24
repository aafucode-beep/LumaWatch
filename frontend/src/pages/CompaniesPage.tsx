import { useMemo, useState } from 'react'
import {
  Card,
  Checkbox,
  Col,
  Empty,
  Input,
  Pagination,
  Row,
  Segmented,
  Space,
  Spin,
  Switch,
  Tag as AntTag,
  Typography,
} from 'antd'
import { StarFilled } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { CompanyListItem } from '../api/types'

const { Text, Title } = Typography

// 维度配色，便于视觉区分
const DIM_COLORS: Record<string, string> = {
  产品类型: 'blue',
  应用场景: 'green',
  地区: 'orange',
  企业属性: 'purple',
}

export default function CompaniesPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<'updated' | 'name'>('updated')

  // 从 URL 读取筛选态，便于点击 tag 后可分享/刷新保持
  const selectedTags = useMemo(
    () => (params.get('tags') || '').split(',').filter(Boolean).map(Number),
    [params],
  )
  const isKey = params.get('is_key') === '1'
  const country = params.get('country') || undefined
  const q = params.get('q') || undefined

  const setFilter = (patch: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params)
    Object.entries(patch).forEach(([k, v]) => {
      if (v === undefined || v === '') next.delete(k)
      else next.set(k, v)
    })
    setParams(next)
    setPage(1)
  }

  const toggleTag = (id: number) => {
    const set = new Set(selectedTags)
    set.has(id) ? set.delete(id) : set.add(id)
    setFilter({ tags: Array.from(set).join(',') })
  }

  const facetsQ = useQuery({ queryKey: ['facets'], queryFn: api.facets })
  const listQ = useQuery({
    queryKey: ['companies', selectedTags, isKey, country, q, sort, page],
    queryFn: () =>
      api.listCompanies({
        tags: selectedTags,
        is_key: isKey || undefined,
        country,
        q,
        sort,
        page,
        page_size: 24,
      }),
  })

  const facets = facetsQ.data

  return (
    <Row gutter={16}>
      {/* 左侧多维筛选栏 */}
      <Col xs={24} md={7} lg={6} xl={5}>
        <Card size="small" title="筛选" style={{ position: 'sticky', top: 8 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Input.Search
              placeholder="搜索企业名/简介"
              defaultValue={q}
              allowClear
              onSearch={(v) => setFilter({ q: v || undefined })}
            />

            <div>
              <Space>
                <StarFilled style={{ color: '#faad14' }} />
                <Text strong>仅看重点企业</Text>
                <Switch
                  checked={isKey}
                  onChange={(v) => setFilter({ is_key: v ? '1' : undefined })}
                />
              </Space>
              {facets && (
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  ({facets.key_count})
                </Text>
              )}
            </div>

            {/* 各维度 tag 分面 */}
            {facets?.dimensions.map((dim) => (
              <div key={dim.dimension}>
                <Text type="secondary">{dim.dimension}</Text>
                <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {dim.tags.map((t) => (
                    <AntTag.CheckableTag
                      key={t.id}
                      checked={selectedTags.includes(t.id)}
                      onChange={() => toggleTag(t.id)}
                    >
                      {t.name} <Text type="secondary">({t.company_count})</Text>
                    </AntTag.CheckableTag>
                  ))}
                  {dim.tags.length === 0 && <Text type="secondary">暂无</Text>}
                </div>
              </div>
            ))}

            {/* 国家分面 */}
            {facets && facets.countries.length > 0 && (
              <div>
                <Text type="secondary">总部国家</Text>
                <div style={{ marginTop: 6 }}>
                  <Checkbox.Group
                    value={country ? [country] : []}
                    onChange={(vals) =>
                      setFilter({ country: (vals[vals.length - 1] as string) || undefined })
                    }
                  >
                    <Space direction="vertical">
                      {facets.countries.map((c) => (
                        <Checkbox key={c.value} value={c.value}>
                          {c.value} ({c.count})
                        </Checkbox>
                      ))}
                    </Space>
                  </Checkbox.Group>
                </div>
              </div>
            )}
          </Space>
        </Card>
      </Col>

      {/* 右侧结果区 */}
      <Col xs={24} md={17} lg={18} xl={19}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
          <Title level={5} style={{ margin: 0, flex: 1 }}>
            企业库 {listQ.data ? `· 共 ${listQ.data.total} 家` : ''}
          </Title>
          <Segmented
            value={sort}
            onChange={(v) => setSort(v as any)}
            options={[
              { label: '最近更新', value: 'updated' },
              { label: '名称', value: 'name' },
            ]}
          />
        </div>

        {/* 已选筛选条件 */}
        {(selectedTags.length > 0 || isKey || country) && (
          <Space wrap style={{ marginBottom: 12 }}>
            {isKey && <AntTag color="gold" closable onClose={() => setFilter({ is_key: undefined })}>重点企业</AntTag>}
            {country && <AntTag color="orange" closable onClose={() => setFilter({ country: undefined })}>{country}</AntTag>}
            {selectedTags.map((id) => {
              const t = facets?.dimensions.flatMap((d) => d.tags).find((x) => x.id === id)
              return (
                <AntTag key={id} color={t ? DIM_COLORS[t.dimension] : 'default'} closable onClose={() => toggleTag(id)}>
                  {t?.name || id}
                </AntTag>
              )
            })}
          </Space>
        )}

        {listQ.isLoading ? (
          <Spin />
        ) : !listQ.data || listQ.data.items.length === 0 ? (
          <Empty description="没有匹配的企业" />
        ) : (
          <>
            <Row gutter={[12, 12]}>
              {listQ.data.items.map((c) => (
                <Col xs={24} sm={12} lg={8} key={c.id}>
                  <CompanyCard c={c} onOpen={() => navigate(`/companies/${c.id}`)} onTag={toggleTag} />
                </Col>
              ))}
            </Row>
            <div style={{ textAlign: 'right', marginTop: 16 }}>
              <Pagination
                current={page}
                pageSize={24}
                total={listQ.data.total}
                showSizeChanger={false}
                onChange={setPage}
              />
            </div>
          </>
        )}
      </Col>
    </Row>
  )
}

function CompanyCard({
  c,
  onOpen,
  onTag,
}: {
  c: CompanyListItem
  onOpen: () => void
  onTag: (id: number) => void
}) {
  return (
    <Card
      size="small"
      hoverable
      className="company-card"
      onClick={onOpen}
      title={
        <Space>
          {c.is_key && <StarFilled style={{ color: '#faad14' }} />}
          <span>{c.name}</span>
        </Space>
      }
      extra={c.status === 'draft' ? <AntTag color="warning">草稿</AntTag> : null}
    >
      <div style={{ minHeight: 64 }}>
        {c.name_cn && <Text type="secondary">{c.name_cn}</Text>}
        <div>
          <Text type="secondary">
            {[c.hq_country, c.hq_city].filter(Boolean).join(' · ') || '地区未知'}
          </Text>
        </div>
        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {c.tags.slice(0, 6).map((t) => (
            <AntTag
              key={t.id}
              color={DIM_COLORS[t.dimension]}
              className="tag-clickable"
              onClick={(e) => {
                e.stopPropagation()
                onTag(t.id)
              }}
            >
              {t.name}
            </AntTag>
          ))}
        </div>
      </div>
    </Card>
  )
}
