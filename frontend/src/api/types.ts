// 与后端 schemas 对应的前端类型

export interface Tag {
  id: number
  name: string
  dimension: string
  description?: string | null
  company_count: number
}

export interface Office {
  id?: number
  region?: string | null
  country?: string | null
  city?: string | null
  office_type: string
  address?: string | null
  note?: string | null
}

export interface ProductLine {
  id?: number
  name: string
  category?: string | null
  description?: string | null
  parent_id?: number | null
  sort_order?: number
  children?: ProductLine[]
}

export interface DownloadResource {
  id?: number
  title: string
  url: string
  resource_type: string
  file_ext?: string | null
  note?: string | null
}

export interface NewsLink {
  id?: number
  title: string
  url: string
  source?: string | null
  published_date?: string | null
  summary?: string | null
  company_id?: number | null
}

export interface ProjectCase {
  id?: number
  name: string
  location?: string | null
  country?: string | null
  application?: string | null
  architect?: string | null
  lighting_designer?: string | null
  completion_year?: number | null
  products?: string | null
  summary?: string | null
  source_url?: string | null
}

export interface IntelligenceInsight {
  id?: number
  category: string
  title: string
  summary: string
  relevance?: string | null
  source_url?: string | null
}

export interface SourceEvidence {
  id?: number
  field: string
  source_url?: string | null
  snippet?: string | null
}
export interface CompanyListItem {
  id: number
  name: string
  name_cn?: string | null
  website?: string | null
  logo_url?: string | null
  hq_country?: string | null
  hq_city?: string | null
  is_key: boolean
  status: string
  tags: Tag[]
}

export interface CompanyDetail extends CompanyListItem {
  founded_year?: number | null
  history?: string | null
  philosophy?: string | null
  summary?: string | null
  created_at: string
  updated_at: string
  offices: Office[]
  product_lines: ProductLine[]
  downloads: DownloadResource[]
  news: NewsLink[]
  projects: ProjectCase[]
  insights: IntelligenceInsight[]
  evidence: SourceEvidence[]
}

export interface CompanyListResponse {
  total: number
  items: CompanyListItem[]
}

export interface FacetValue {
  value: string
  count: number
}
export interface DimensionFacet {
  dimension: string
  tags: Tag[]
}
export interface FacetsResponse {
  dimensions: DimensionFacet[]
  countries: FacetValue[]
  key_count: number
  total: number
}

export interface ProbeJob {
  id: number
  url: string
  company_id?: number | null
  status: string
  progress: number
  message?: string | null
  created_at: string
  updated_at: string
}

export interface ProbeJobDetail extends ProbeJob {
  log?: string | null
  draft?: any
}

export interface CompanyFilters {
  tags?: number[]
  is_key?: boolean
  country?: string
  status?: string
  q?: string
  sort?: string
  page?: number
  page_size?: number
}
