"""Pydantic 请求/响应模型。"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------- 通用 ----------
class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- 鉴权 ----------
class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Tag ----------
class TagBase(BaseModel):
    name: str
    dimension: str = "产品类型"
    description: Optional[str] = None


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    dimension: Optional[str] = None
    description: Optional[str] = None


class TagOut(ORMModel, TagBase):
    id: int
    company_count: int = 0


class TagMergeRequest(BaseModel):
    source_tag_ids: list[int]
    target_tag_id: int


# ---------- Office ----------
class OfficeBase(BaseModel):
    region: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    office_type: str = "office"
    address: Optional[str] = None
    note: Optional[str] = None


class OfficeOut(ORMModel, OfficeBase):
    id: int


# ---------- ProductLine ----------
class ProductLineBase(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 0


class ProductLineOut(ORMModel, ProductLineBase):
    id: int
    children: list["ProductLineOut"] = []


# ---------- Download ----------
class DownloadBase(BaseModel):
    title: str
    url: str
    resource_type: str = "other"
    file_ext: Optional[str] = None
    note: Optional[str] = None


class DownloadOut(ORMModel, DownloadBase):
    id: int


# ---------- News ----------
class NewsBase(BaseModel):
    title: str
    url: str
    source: Optional[str] = None
    published_date: Optional[str] = None
    summary: Optional[str] = None
    company_id: Optional[int] = None


class NewsOut(ORMModel, NewsBase):
    id: int


# ---------- Company ----------
class CompanyBase(BaseModel):
    name: str
    name_cn: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    hq_country: Optional[str] = None
    hq_city: Optional[str] = None
    founded_year: Optional[int] = None
    history: Optional[str] = None
    philosophy: Optional[str] = None
    summary: Optional[str] = None
    is_key: bool = False


class CompanyListItem(ORMModel):
    id: int
    name: str
    name_cn: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    hq_country: Optional[str] = None
    hq_city: Optional[str] = None
    is_key: bool = False
    status: str
    tags: list[TagOut] = []


class CompanyDetail(ORMModel, CompanyBase):
    id: int
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime
    offices: list[OfficeOut] = []
    product_lines: list[ProductLineOut] = []
    downloads: list[DownloadOut] = []
    news: list[NewsOut] = []
    tags: list[TagOut] = []


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    name_cn: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    hq_country: Optional[str] = None
    hq_city: Optional[str] = None
    founded_year: Optional[int] = None
    history: Optional[str] = None
    philosophy: Optional[str] = None
    summary: Optional[str] = None
    is_key: Optional[bool] = None
    status: Optional[str] = None
    # 直接覆盖式设置 tag / 产品线 / 下载 / office / news
    tag_ids: Optional[list[int]] = None
    offices: Optional[list[OfficeBase]] = None
    product_lines: Optional[list[ProductLineBase]] = None
    downloads: Optional[list[DownloadBase]] = None
    news: Optional[list[NewsBase]] = None


class CompanyListResponse(BaseModel):
    total: int
    items: list[CompanyListItem]


# ---------- Probe ----------
class ProbeRequest(BaseModel):
    urls: list[str]


class ProbeJobOut(ORMModel):
    id: int
    url: str
    company_id: Optional[int] = None
    status: str
    progress: int
    message: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime


class ProbeJobDetail(ProbeJobOut):
    log: Optional[str] = None
    draft: Optional[dict] = None


class ProbeConfirmRequest(BaseModel):
    """将 AI 草稿（可编辑后）确认入库。"""

    draft: dict


# ---------- Facets ----------
class FacetValue(BaseModel):
    value: str
    count: int


class DimensionFacet(BaseModel):
    dimension: str
    tags: list[TagOut]


class FacetsResponse(BaseModel):
    dimensions: list[DimensionFacet]
    countries: list[FacetValue]
    key_count: int
    total: int


ProductLineOut.model_rebuild()
