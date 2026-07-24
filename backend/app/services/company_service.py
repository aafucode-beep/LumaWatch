"""企业数据服务：草稿入库、多维筛选、分面统计。"""
from __future__ import annotations

from urllib.parse import urlsplit

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models


# ---------- Tag ----------
def get_or_create_tag(db: Session, name: str, dimension: str = "产品类型") -> models.Tag:
    name = (name or "").strip()
    dimension = (dimension or "产品类型").strip()
    if not name:
        raise ValueError("tag name 不能为空")
    tag = db.scalar(
        select(models.Tag).where(models.Tag.name == name, models.Tag.dimension == dimension)
    )
    if tag:
        return tag
    tag = models.Tag(name=name, dimension=dimension)
    db.add(tag)
    db.flush()
    return tag


def set_company_tags(db: Session, company: models.Company, tag_ids: list[int]) -> None:
    company.tag_links.clear()
    db.flush()
    for tag_id in dict.fromkeys(tag_ids):
        if db.get(models.Tag, tag_id):
            db.add(models.CompanyTag(company_id=company.id, tag_id=tag_id, source="manual"))


# ---------- 草稿入库 ----------
def _safe_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (ValueError, TypeError):
        return None


def _website_key(url: str | None) -> str:
    if not url:
        return ""
    host = urlsplit(url).netloc.lower().split(":", 1)[0]
    return host.removeprefix("www.")


def _find_existing_company(db: Session, website: str | None) -> models.Company | None:
    key = _website_key(website)
    if not key:
        return None
    companies = db.scalars(
        select(models.Company).where(models.Company.website.is_not(None))
    ).all()
    return next((company for company in companies if _website_key(company.website) == key), None)


def _clear_company_intelligence(db: Session, company: models.Company) -> None:
    company.offices.clear()
    company.product_lines.clear()
    company.downloads.clear()
    company.news.clear()
    company.projects.clear()
    company.insights.clear()
    company.tag_links.clear()
    db.execute(
        delete(models.SourceEvidence).where(
            models.SourceEvidence.entity_type == "company",
            models.SourceEvidence.entity_id == company.id,
        )
    )
    db.flush()


def _add_product_lines(
    db: Session,
    company_id: int,
    items: list[dict],
    parent_id: int | None = None,
) -> None:
    for order, item in enumerate(items or []):
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        product_line = models.ProductLine(
            company_id=company_id,
            parent_id=parent_id,
            name=name[:255],
            category=(item.get("category") or None),
            description=(item.get("description") or None),
            sort_order=order,
        )
        db.add(product_line)
        db.flush()
        if item.get("source_url"):
            db.add(
                models.SourceEvidence(
                    entity_type="company",
                    entity_id=company_id,
                    field=f"product_line:{name}"[:64],
                    source_url=str(item["source_url"])[:1024],
                    snippet=(str(item.get("source_snippet"))[:300] if item.get("source_snippet") else None),
                )
            )
        _add_product_lines(db, company_id, item.get("children") or [], product_line.id)


def apply_draft(db: Session, draft: dict) -> models.Company:
    """确认 AI 草稿；同一官网再次探测时更新原企业，避免重复记录。"""
    company_data = draft.get("company") or {}
    website = company_data.get("website") or draft.get("_source_url")
    company = _find_existing_company(db, website)

    if company:
        preserved_is_key = company.is_key
        _clear_company_intelligence(db, company)
    else:
        company = models.Company(name="未命名企业", status="confirmed")
        db.add(company)
        db.flush()
        preserved_is_key = False

    company.name = str(company_data.get("name") or "未命名企业")[:255]
    company.name_cn = company_data.get("name_cn")
    company.website = website
    company.logo_url = company_data.get("logo_url")
    company.hq_country = company_data.get("hq_country")
    company.hq_city = company_data.get("hq_city")
    company.founded_year = _safe_int(company_data.get("founded_year"))
    company.history = company_data.get("history")
    company.philosophy = company_data.get("philosophy")
    company.summary = company_data.get("summary")
    company.is_key = bool(company_data.get("is_key", preserved_is_key))
    company.status = "confirmed"
    db.flush()

    for office in draft.get("offices") or []:
        db.add(
            models.CompanyOffice(
                company_id=company.id,
                region=office.get("region"),
                country=office.get("country"),
                city=office.get("city"),
                office_type=office.get("office_type") or "office",
                address=office.get("address"),
                note=office.get("note"),
            )
        )

    _add_product_lines(db, company.id, draft.get("product_lines") or [])

    for download in draft.get("downloads") or []:
        if not download.get("url"):
            continue
        db.add(
            models.DownloadResource(
                company_id=company.id,
                title=str(download.get("title") or download["url"])[:512],
                url=str(download["url"])[:1024],
                resource_type=download.get("resource_type") or "other",
                file_ext=download.get("file_ext"),
                note=download.get("note"),
            )
        )

    for news_item in draft.get("news") or []:
        if not news_item.get("url"):
            continue
        db.add(
            models.NewsLink(
                company_id=company.id,
                title=str(news_item.get("title") or news_item["url"])[:512],
                url=str(news_item["url"])[:1024],
                source=news_item.get("source"),
                published_date=news_item.get("published_date"),
                summary=news_item.get("summary"),
            )
        )

    for project in draft.get("projects") or []:
        if not project.get("name"):
            continue
        db.add(
            models.ProjectCase(
                company_id=company.id,
                name=str(project["name"])[:512],
                location=project.get("location"),
                country=project.get("country"),
                application=project.get("application"),
                architect=project.get("architect"),
                lighting_designer=project.get("lighting_designer"),
                completion_year=_safe_int(project.get("completion_year")),
                products=project.get("products"),
                summary=project.get("summary"),
                source_url=(str(project["source_url"])[:1024] if project.get("source_url") else None),
            )
        )

    for insight in draft.get("insights") or []:
        if not insight.get("title") or not insight.get("summary"):
            continue
        db.add(
            models.IntelligenceInsight(
                company_id=company.id,
                category=str(insight.get("category") or "其他")[:64],
                title=str(insight["title"])[:255],
                summary=str(insight["summary"]),
                relevance=insight.get("relevance"),
                source_url=(str(insight["source_url"])[:1024] if insight.get("source_url") else None),
            )
        )

    for evidence in draft.get("evidence") or []:
        if not evidence.get("field") or not evidence.get("source_url"):
            continue
        db.add(
            models.SourceEvidence(
                entity_type="company",
                entity_id=company.id,
                field=str(evidence["field"])[:64],
                source_url=str(evidence["source_url"])[:1024],
                snippet=(str(evidence.get("snippet"))[:300] if evidence.get("snippet") else None),
            )
        )

    for tag_item in draft.get("tags") or []:
        name = tag_item.get("name") if isinstance(tag_item, dict) else str(tag_item)
        dimension = tag_item.get("dimension") if isinstance(tag_item, dict) else "产品类型"
        if not name:
            continue
        tag = get_or_create_tag(db, name, dimension or "产品类型")
        db.add(
            models.CompanyTag(
                company_id=company.id,
                tag_id=tag.id,
                source="ai",
                confidence=0.8,
            )
        )

    db.commit()
    db.refresh(company)
    return company

# ---------- 多维筛选 ----------
def filter_company_ids(
    db: Session,
    tag_ids: list[int] | None = None,
    is_key: bool | None = None,
    country: str | None = None,
    status: str | None = None,
) -> set[int] | None:
    """按 tag（同维度 OR、跨维度 AND）与其它条件求交集。

    返回匹配的 company id 集合；None 表示无 tag 约束（不限制）。
    """
    result: set[int] | None = None

    if tag_ids:
        # 取涉及的 tag 及其维度
        tags = db.scalars(select(models.Tag).where(models.Tag.id.in_(tag_ids))).all()
        by_dim: dict[str, list[int]] = {}
        for t in tags:
            by_dim.setdefault(t.dimension, []).append(t.id)
        # 每个维度内 OR，维度之间 AND
        for _dim, ids in by_dim.items():
            rows = db.execute(
                select(models.CompanyTag.company_id)
                .where(models.CompanyTag.tag_id.in_(ids))
                .distinct()
            ).all()
            dim_set = {r[0] for r in rows}
            result = dim_set if result is None else (result & dim_set)

    return result
