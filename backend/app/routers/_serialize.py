"""ORM -> Pydantic 序列化辅助。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas


def tag_out(tag: models.Tag, count: int = 0) -> schemas.TagOut:
    return schemas.TagOut(
        id=tag.id,
        name=tag.name,
        dimension=tag.dimension,
        description=tag.description,
        company_count=count,
    )


def _build_pl_tree(pls: list[models.ProductLine]) -> list[schemas.ProductLineOut]:
    by_parent: dict[int | None, list[models.ProductLine]] = {}
    for pl in pls:
        by_parent.setdefault(pl.parent_id, []).append(pl)

    def build(parent_id) -> list[schemas.ProductLineOut]:
        items = sorted(by_parent.get(parent_id, []), key=lambda x: x.sort_order)
        return [
            schemas.ProductLineOut(
                id=pl.id,
                name=pl.name,
                category=pl.category,
                description=pl.description,
                parent_id=pl.parent_id,
                sort_order=pl.sort_order,
                children=build(pl.id),
            )
            for pl in items
        ]

    return build(None)


def company_tags(company: models.Company) -> list[schemas.TagOut]:
    return [tag_out(link.tag) for link in company.tag_links]


def to_list_item(company: models.Company) -> schemas.CompanyListItem:
    return schemas.CompanyListItem(
        id=company.id,
        name=company.name,
        name_cn=company.name_cn,
        website=company.website,
        logo_url=company.logo_url,
        hq_country=company.hq_country,
        hq_city=company.hq_city,
        is_key=company.is_key,
        status=company.status,
        tags=company_tags(company),
    )


def to_detail(
    company: models.Company,
    evidence: list[models.SourceEvidence] | None = None,
) -> schemas.CompanyDetail:
    return schemas.CompanyDetail(
        id=company.id,
        name=company.name,
        name_cn=company.name_cn,
        website=company.website,
        logo_url=company.logo_url,
        hq_country=company.hq_country,
        hq_city=company.hq_city,
        founded_year=company.founded_year,
        history=company.history,
        philosophy=company.philosophy,
        summary=company.summary,
        is_key=company.is_key,
        status=company.status,
        created_at=company.created_at,
        updated_at=company.updated_at,
        offices=[schemas.OfficeOut.model_validate(o) for o in company.offices],
        product_lines=_build_pl_tree(company.product_lines),
        downloads=[schemas.DownloadOut.model_validate(d) for d in company.downloads],
        news=[schemas.NewsOut.model_validate(n) for n in company.news],
        projects=[schemas.ProjectCaseOut.model_validate(p) for p in company.projects],
        insights=[schemas.IntelligenceInsightOut.model_validate(i) for i in company.insights],
        evidence=[schemas.SourceEvidenceOut.model_validate(e) for e in (evidence or [])],
        tags=company_tags(company),
    )


def tag_company_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(models.CompanyTag.tag_id, func.count(models.CompanyTag.company_id)).group_by(
            models.CompanyTag.tag_id
        )
    ).all()
    return {r[0]: r[1] for r in rows}
