"""ORM 数据模型。

设计要点：
- company 为核心实体；office / product_line / download / news 均挂在 company 下。
- tag 采用多维度（dimension）设计，company_tag 多对多，支持反向检索与多重筛选。
- source_evidence 记录每个 AI 提取字段的出处，用于溯源、防幻觉。
- probe_job 记录一次探测任务的状态与日志。
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Company(Base):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    name_cn: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    hq_country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    hq_city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    philosophy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_key: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # draft（AI 草稿待校对）/ confirmed（已确认）
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    offices: Mapped[list["CompanyOffice"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    product_lines: Mapped[list["ProductLine"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    downloads: Mapped[list["DownloadResource"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    news: Mapped[list["NewsLink"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    projects: Mapped[list["ProjectCase"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    insights: Mapped[list["IntelligenceInsight"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    tag_links: Mapped[list["CompanyTag"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class CompanyOffice(Base):
    """国际网络机构分布：分支/经销商/展厅等。"""

    __tablename__ = "company_office"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("company.id", ondelete="CASCADE"), index=True
    )
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # branch / distributor / showroom / office / other
    office_type: Mapped[str] = mapped_column(String(32), default="office")
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="offices")


class ProductLine(Base):
    """产品线架构，支持层级（parent_id 自关联）。"""

    __tablename__ = "product_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("company.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product_line.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    company: Mapped["Company"] = relationship(back_populates="product_lines")
    parent: Mapped[Optional["ProductLine"]] = relationship(
        back_populates="children", remote_side="ProductLine.id"
    )
    children: Mapped[list["ProductLine"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )


class DownloadResource(Base):
    """可公开下载内容——只存链接，不执行下载。"""

    __tablename__ = "download_resource"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("company.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024))
    # catalog / ies / datasheet / bim / certificate / manual / other
    resource_type: Mapped[str] = mapped_column(String(32), default="other")
    file_ext: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="downloads")


class NewsLink(Base):
    """行业新闻链接，可归集到企业（company_id 可空）。"""

    __tablename__ = "news_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("company.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024))
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company: Mapped[Optional["Company"]] = relationship(back_populates="news")


class ProjectCase(Base):
    """官网公开的代表项目或应用案例。"""

    __tablename__ = "project_case"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("company.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(512))
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    application: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    architect: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lighting_designer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    completion_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    products: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="projects")


class IntelligenceInsight(Base):
    """面向研究和决策的关键信息，而非官网宣传文本的简单复述。"""

    __tablename__ = "intelligence_insight"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("company.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(64), default="其他")
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    relevance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="insights")

class Tag(Base):
    """多维度标签。dimension 例：产品类型 / 应用场景 / 地区 / 企业属性。"""

    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("name", "dimension", name="uq_tag_name_dim"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    dimension: Mapped[str] = mapped_column(String(64), default="产品类型", index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    company_links: Mapped[list["CompanyTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class CompanyTag(Base):
    __tablename__ = "company_tag"
    __table_args__ = (
        UniqueConstraint("company_id", "tag_id", name="uq_company_tag"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("company.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tag.id", ondelete="CASCADE"), index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    # ai / manual
    source: Mapped[str] = mapped_column(String(16), default="manual")

    company: Mapped["Company"] = relationship(back_populates="tag_links")
    tag: Mapped["Tag"] = relationship(back_populates="company_links")


class SourceEvidence(Base):
    """字段级溯源：记录某实体某字段来自哪个页面及原文片段。"""

    __tablename__ = "source_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    field: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class ProbeJob(Base):
    __tablename__ = "probe_job"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1024))
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("company.id", ondelete="SET NULL"), nullable=True
    )
    # pending / crawling / extracting / done / failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 抓取到的原始页面（JSON 字符串）与 AI 草稿（JSON 字符串）
    pages_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class Setting(Base):
    """键值配置（如运行时可覆盖的 LLM 参数）。"""

    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
