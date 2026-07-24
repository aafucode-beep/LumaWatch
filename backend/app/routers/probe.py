"""探测路由：发起任务、查询进度、确认草稿入库。"""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services import company_service, probe_service

router = APIRouter(prefix="/api/probe", tags=["probe"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=list[schemas.ProbeJobOut])
def start_probe(
    body: schemas.ProbeRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not body.urls:
        raise HTTPException(400, "请提供至少一个网址")
    jobs = probe_service.create_jobs(db, body.urls)
    for job in jobs:
        background.add_task(probe_service.run_probe_job, job.id)
    return [schemas.ProbeJobOut.model_validate(j) for j in jobs]


@router.get("", response_model=list[schemas.ProbeJobOut])
def list_jobs(limit: int = 50, db: Session = Depends(get_db)):
    jobs = db.scalars(
        select(models.ProbeJob).order_by(models.ProbeJob.created_at.desc()).limit(limit)
    ).all()
    return [schemas.ProbeJobOut.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=schemas.ProbeJobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(models.ProbeJob, job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    draft = json.loads(job.draft_json) if job.draft_json else None
    detail = schemas.ProbeJobDetail.model_validate(job)
    detail.draft = draft
    return detail


@router.post("/{job_id}/confirm", response_model=schemas.CompanyDetail)
def confirm_job(
    job_id: int, body: schemas.ProbeConfirmRequest, db: Session = Depends(get_db)
):
    """用（可能被前端编辑过的）草稿创建企业记录。"""
    job = db.get(models.ProbeJob, job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    company = company_service.apply_draft(db, body.draft)
    job.company_id = company.id
    db.commit()

    # 重新加载完整详情
    from .companies import _load_full
    from . import _serialize

    full = _load_full(db, company.id)
    return _serialize.to_detail(full)


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(models.ProbeJob, job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    db.delete(job)
    db.commit()
    return {"ok": True}
