"""企业路由：列表(多维筛选)、详情、编辑、删除、分面。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..fts import search_company_ids
from ..services import company_service
from . import _serialize

router = APIRouter(prefix="/api/companies", tags=["companies"], dependencies=[Depends(get_current_user)])


def _load_full(db: Session, company_id: int) -> models.Company | None:
    return db.scalar(
        select(models.Company)
        .where(models.Company.id == company_id)
        .options(
            selectinload(models.Company.offices),
            selectinload(models.Company.product_lines),
            selectinload(models.Company.downloads),
            selectinload(models.Company.news),
            selectinload(models.Company.projects),
            selectinload(models.Company.insights),
            selectinload(models.Company.tag_links).selectinload(models.CompanyTag.tag),
        )
    )


@router.get("", response_model=schemas.CompanyListResponse)
def list_companies(
    db: Session = Depends(get_db),
    tags: str | None = Query(None, description="逗号分隔的 tag id"),
    is_key: bool | None = None,
    country: str | None = None,
    status: str | None = None,
    q: str | None = None,
    sort: str = Query("updated", description="updated|name"),
    page: int = 1,
    page_size: int = 30,
):
    tag_ids = [int(x) for x in tags.split(",") if x.strip().isdigit()] if tags else []

    stmt = select(models.Company)
    id_constraint: set[int] | None = company_service.filter_company_ids(db, tag_ids)

    if q:
        matched = set(search_company_ids(db, q))
        id_constraint = matched if id_constraint is None else (id_constraint & matched)

    if id_constraint is not None:
        if not id_constraint:
            return schemas.CompanyListResponse(total=0, items=[])
        stmt = stmt.where(models.Company.id.in_(id_constraint))

    if is_key is not None:
        stmt = stmt.where(models.Company.is_key == is_key)
    if country:
        stmt = stmt.where(models.Company.hq_country == country)
    if status:
        stmt = stmt.where(models.Company.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    if sort == "name":
        stmt = stmt.order_by(models.Company.name.asc())
    else:
        stmt = stmt.order_by(models.Company.updated_at.desc())

    stmt = stmt.options(
        selectinload(models.Company.tag_links).selectinload(models.CompanyTag.tag)
    ).offset((page - 1) * page_size).limit(page_size)

    companies = db.scalars(stmt).all()
    return schemas.CompanyListResponse(
        total=total, items=[_serialize.to_list_item(c) for c in companies]
    )


@router.get("/facets", response_model=schemas.FacetsResponse)
def facets(db: Session = Depends(get_db)):
    """分面统计：各维度 tag、国家、重点企业数、总数。"""
    counts = _serialize.tag_company_counts(db)
    tags = db.scalars(select(models.Tag).order_by(models.Tag.dimension, models.Tag.name)).all()
    by_dim: dict[str, list[schemas.TagOut]] = {}
    for t in tags:
        by_dim.setdefault(t.dimension, []).append(_serialize.tag_out(t, counts.get(t.id, 0)))
    dimensions = [
        schemas.DimensionFacet(dimension=d, tags=ts) for d, ts in by_dim.items()
    ]

    country_rows = db.execute(
        select(models.Company.hq_country, func.count(models.Company.id))
        .where(models.Company.hq_country.is_not(None))
        .group_by(models.Company.hq_country)
        .order_by(func.count(models.Company.id).desc())
    ).all()
    countries = [schemas.FacetValue(value=r[0], count=r[1]) for r in country_rows if r[0]]

    key_count = db.scalar(
        select(func.count()).select_from(models.Company).where(models.Company.is_key.is_(True))
    ) or 0
    total = db.scalar(select(func.count()).select_from(models.Company)) or 0

    return schemas.FacetsResponse(
        dimensions=dimensions, countries=countries, key_count=key_count, total=total
    )


@router.get("/{company_id}", response_model=schemas.CompanyDetail)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = _load_full(db, company_id)
    if not company:
        raise HTTPException(404, "企业不存在")
    evidence = db.scalars(
        select(models.SourceEvidence)
        .where(
            models.SourceEvidence.entity_type == "company",
            models.SourceEvidence.entity_id == company.id,
        )
        .order_by(models.SourceEvidence.id)
    ).all()
    return _serialize.to_detail(company, evidence)


@router.put("/{company_id}", response_model=schemas.CompanyDetail)
def update_company(
    company_id: int, body: schemas.CompanyUpdate, db: Session = Depends(get_db)
):
    company = _load_full(db, company_id)
    if not company:
        raise HTTPException(404, "企业不存在")

    scalar_fields = [
        "name", "name_cn", "website", "logo_url", "hq_country", "hq_city",
        "founded_year", "history", "philosophy", "summary", "is_key", "status",
    ]
    for f in scalar_fields:
        val = getattr(body, f)
        if val is not None:
            setattr(company, f, val)

    if body.tag_ids is not None:
        company_service.set_company_tags(db, company, body.tag_ids)

    if body.offices is not None:
        company.offices.clear()
        db.flush()
        for o in body.offices:
            db.add(models.CompanyOffice(company_id=company.id, **o.model_dump()))

    if body.downloads is not None:
        company.downloads.clear()
        db.flush()
        for d in body.downloads:
            db.add(models.DownloadResource(company_id=company.id, **d.model_dump()))

    if body.news is not None:
        company.news.clear()
        db.flush()
        for n in body.news:
            data = n.model_dump()
            data["company_id"] = company.id
            db.add(models.NewsLink(**data))

    if body.product_lines is not None:
        company.product_lines.clear()
        db.flush()
        company_service._add_product_lines(
            db, company.id, [p.model_dump() for p in body.product_lines]
        )

    db.commit()
    company = _load_full(db, company_id)
    evidence = db.scalars(
        select(models.SourceEvidence).where(
            models.SourceEvidence.entity_type == "company",
            models.SourceEvidence.entity_id == company_id,
        )
    ).all()
    return _serialize.to_detail(company, evidence)


@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.get(models.Company, company_id)
    if not company:
        raise HTTPException(404, "企业不存在")
    db.execute(
        delete(models.SourceEvidence).where(
            models.SourceEvidence.entity_type == "company",
            models.SourceEvidence.entity_id == company_id,
        )
    )
    db.delete(company)
    db.commit()
    return {"ok": True}
