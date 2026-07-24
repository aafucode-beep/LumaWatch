"""标签路由：列表、增改删、合并（清理 AI 噪点）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services import company_service
from . import _serialize

router = APIRouter(prefix="/api/tags", tags=["tags"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[schemas.TagOut])
def list_tags(dimension: str | None = None, db: Session = Depends(get_db)):
    counts = _serialize.tag_company_counts(db)
    stmt = select(models.Tag).order_by(models.Tag.dimension, models.Tag.name)
    if dimension:
        stmt = stmt.where(models.Tag.dimension == dimension)
    return [_serialize.tag_out(t, counts.get(t.id, 0)) for t in db.scalars(stmt).all()]


@router.post("", response_model=schemas.TagOut)
def create_tag(body: schemas.TagCreate, db: Session = Depends(get_db)):
    tag = company_service.get_or_create_tag(db, body.name, body.dimension)
    if body.description:
        tag.description = body.description
    db.commit()
    db.refresh(tag)
    return _serialize.tag_out(tag)


@router.put("/{tag_id}", response_model=schemas.TagOut)
def update_tag(tag_id: int, body: schemas.TagUpdate, db: Session = Depends(get_db)):
    tag = db.get(models.Tag, tag_id)
    if not tag:
        raise HTTPException(404, "标签不存在")
    if body.name is not None:
        tag.name = body.name.strip()
    if body.dimension is not None:
        tag.dimension = body.dimension.strip()
    if body.description is not None:
        tag.description = body.description
    db.commit()
    db.refresh(tag)
    return _serialize.tag_out(tag)


@router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.get(models.Tag, tag_id)
    if not tag:
        raise HTTPException(404, "标签不存在")
    db.delete(tag)
    db.commit()
    return {"ok": True}


@router.post("/merge")
def merge_tags(body: schemas.TagMergeRequest, db: Session = Depends(get_db)):
    """把 source_tag_ids 的企业关联迁移到 target_tag_id，然后删除源标签。"""
    target = db.get(models.Tag, body.target_tag_id)
    if not target:
        raise HTTPException(404, "目标标签不存在")

    sources = [s for s in body.source_tag_ids if s != body.target_tag_id]
    # 目标已关联的企业，避免重复
    existing = {
        r[0]
        for r in db.execute(
            select(models.CompanyTag.company_id).where(
                models.CompanyTag.tag_id == target.id
            )
        ).all()
    }
    links = db.scalars(
        select(models.CompanyTag).where(models.CompanyTag.tag_id.in_(sources))
    ).all()
    for link in links:
        if link.company_id in existing:
            db.delete(link)
        else:
            link.tag_id = target.id
            existing.add(link.company_id)
    db.flush()
    db.execute(delete(models.Tag).where(models.Tag.id.in_(sources)))
    db.commit()
    return {"ok": True, "merged": len(sources), "target": target.id}
