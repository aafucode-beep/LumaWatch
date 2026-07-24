"""企业数据服务：草稿入库、多维筛选、分面统计。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

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
    for tid in dict.fromkeys(tag_ids):
        if db.get(models.Tag, tid):
            db.add(models.CompanyTag(company_id=company.id, tag_id=tid, source="manual"))


# ---------- 草稿入库 ----------
def _add_product_lines(db: Session, company_id: int, items: list[dict], parent_id=None):
    for order, it in enumerate(items or []):
        name = (it.get("name") or "").strip()
        if not name:
            continue
        pl = models.ProductLine(
            company_id=company_id,
            parent_id=parent_id,
            name=name[:255],
            category=(it.get("category") or None),
            description=(it.get("description") or None),
            sort_order=order,
        )
        db.add(pl)
        db.flush()
        _add_product_lines(db, company_id, it.get("children") or [], pl.id)


def apply_draft(db: Session, draft: dict) -> models.Company:
    """把（可能被人工编辑过的）AI 草稿写入数据库，状态置为 confirmed。"""
    c = draft.get("company") or {}
    company = models.Company(
        name=(c.get("name") or "未命名企业")[:255],
        name_cn=c.get("name_cn"),
        website=c.get("website"),
        logo_url=c.get("logo_url"),
        hq_country=c.get("hq_country"),
        hq_city=c.get("hq_city"),
        founded_year=_safe_int(c.get("founded_year")),
        history=c.get("history"),
        philosophy=c.get("philosophy"),
        summary=c.get("summary"),
        is_key=bool(c.get("is_key", False)),
        status="confirmed",
    )
    db.add(company)
    db.flush()

    for o in draft.get("offices") or []:
        db.add(
            models.CompanyOffice(
                company_id=company.id,
                region=o.get("region"),
                country=o.get("country"),
                city=o.get("city"),
                office_type=o.get("office_type") or "office",
                address=o.get("address"),
                note=o.get("note"),
            )
        )

    _add_product_lines(db, company.id, draft.get("product_lines"))

    for d in draft.get("downloads") or []:
        if not d.get("url"):
            continue
        db.add(
            models.DownloadResource(
                company_id=company.id,
                title=(d.get("title") or d["url"])[:512],
                url=d["url"][:1024],
                resource_type=d.get("resource_type") or "other",
                file_ext=d.get("file_ext"),
                note=d.get("note"),
            )
        )

    for n in draft.get("news") or []:
        if not n.get("url"):
            continue
        db.add(
            models.NewsLink(
                company_id=company.id,
                title=(n.get("title") or n["url"])[:512],
                url=n["url"][:1024],
                source=n.get("source"),
                published_date=n.get("published_date"),
                summary=n.get("summary"),
            )
        )

    for t in draft.get("tags") or []:
        name = t.get("name") if isinstance(t, dict) else str(t)
        dim = t.get("dimension") if isinstance(t, dict) else "产品类型"
        if not name:
            continue
        tag = get_or_create_tag(db, name, dim or "产品类型")
        exists = db.scalar(
            select(models.CompanyTag).where(
                models.CompanyTag.company_id == company.id,
                models.CompanyTag.tag_id == tag.id,
            )
        )
        if not exists:
            db.add(
                models.CompanyTag(
                    company_id=company.id, tag_id=tag.id, source="ai", confidence=0.8
                )
            )

    db.commit()
    db.refresh(company)
    return company


def _safe_int(v):
    try:
        return int(v) if v not in (None, "") else None
    except (ValueError, TypeError):
        return None


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
