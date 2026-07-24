import axios from 'axios'
import type {
  CompanyDetail,
  CompanyFilters,
  CompanyListResponse,
  FacetsResponse,
  ProbeJob,
  ProbeJobDetail,
  Tag,
} from './types'

// Web（含 dev 代理）用相对路径；Android/独立部署用 VITE_API_BASE 指向服务器域名
const BASE = import.meta.env.VITE_API_BASE || ''

const TOKEN_KEY = 'li_token'
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export const http = axios.create({ baseURL: BASE })

http.interceptors.request.use((config) => {
  const t = tokenStore.get()
  if (t) config.headers.Authorization = `Bearer ${t}`
  return config
})

// 401 时清理登录态并跳转
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      tokenStore.clear()
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    return Promise.reject(err)
  },
)

export const api = {
  async login(password: string): Promise<string> {
    const { data } = await http.post('/api/auth/login-json', { password })
    return data.access_token
  },
  async me() {
    const { data } = await http.get('/api/auth/me')
    return data
  },
  async health() {
    const { data } = await http.get('/api/health')
    return data as { status: string; llm_configured: boolean; llm_model: string }
  },

  async listCompanies(f: CompanyFilters): Promise<CompanyListResponse> {
    const params: Record<string, any> = {}
    if (f.tags?.length) params.tags = f.tags.join(',')
    if (f.is_key) params.is_key = true
    if (f.country) params.country = f.country
    if (f.status) params.status = f.status
    if (f.q) params.q = f.q
    if (f.sort) params.sort = f.sort
    params.page = f.page ?? 1
    params.page_size = f.page_size ?? 30
    const { data } = await http.get('/api/companies', { params })
    return data
  },
  async facets(): Promise<FacetsResponse> {
    const { data } = await http.get('/api/companies/facets')
    return data
  },
  async getCompany(id: number): Promise<CompanyDetail> {
    const { data } = await http.get(`/api/companies/${id}`)
    return data
  },
  async updateCompany(id: number, body: any): Promise<CompanyDetail> {
    const { data } = await http.put(`/api/companies/${id}`, body)
    return data
  },
  async deleteCompany(id: number) {
    await http.delete(`/api/companies/${id}`)
  },

  async listTags(): Promise<Tag[]> {
    const { data } = await http.get('/api/tags')
    return data
  },
  async createTag(body: { name: string; dimension: string; description?: string }): Promise<Tag> {
    const { data } = await http.post('/api/tags', body)
    return data
  },
  async updateTag(id: number, body: any): Promise<Tag> {
    const { data } = await http.put(`/api/tags/${id}`, body)
    return data
  },
  async deleteTag(id: number) {
    await http.delete(`/api/tags/${id}`)
  },
  async mergeTags(sourceIds: number[], targetId: number) {
    const { data } = await http.post('/api/tags/merge', {
      source_tag_ids: sourceIds,
      target_tag_id: targetId,
    })
    return data
  },

  async startProbe(urls: string[]): Promise<ProbeJob[]> {
    const { data } = await http.post('/api/probe', { urls })
    return data
  },
  async listJobs(): Promise<ProbeJob[]> {
    const { data } = await http.get('/api/probe')
    return data
  },
  async getJob(id: number): Promise<ProbeJobDetail> {
    const { data } = await http.get(`/api/probe/${id}`)
    return data
  },
  async confirmJob(id: number, draft: any): Promise<CompanyDetail> {
    const { data } = await http.post(`/api/probe/${id}/confirm`, { draft })
    return data
  },
  async deleteJob(id: number) {
    await http.delete(`/api/probe/${id}`)
  },
}
