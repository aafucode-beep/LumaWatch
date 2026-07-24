"""探测任务服务：后台执行 抓取 -> AI 提取 -> 存草稿；以及草稿确认入库。"""
from __future__ import annotations

import asyncio
import datetime as dt
import json

from sqlalchemy.orm import Session

from .. import ai, models
from ..crawler import crawl_site
from ..database import SessionLocal


def create_jobs(db: Session, urls: list[str]) -> list[models.ProbeJob]:
    jobs = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        job = models.ProbeJob(url=url, status="pending", progress=0)
        db.add(job)
        jobs.append(job)
    db.commit()
    for j in jobs:
        db.refresh(j)
    return jobs


def _append_log(job: models.ProbeJob, line: str) -> None:
    ts = dt.datetime.now().strftime("%H:%M:%S")
    job.log = (job.log or "") + f"[{ts}] {line}\n"


def run_probe_job(job_id: int) -> None:
    """后台入口（同步）。在独立会话中执行，防止阻塞请求会话。"""
    db = SessionLocal()
    try:
        job = db.get(models.ProbeJob, job_id)
        if not job:
            return

        def progress(pct: int, msg: str):
            job.progress = min(95, pct)
            job.message = msg
            _append_log(job, msg)
            db.commit()

        job.status = "crawling"
        job.message = "开始抓取"
        db.commit()

        crawl = asyncio.run(crawl_site(job.url, progress))
        job.pages_json = json.dumps(
            [
                {"url": p.url, "category": p.category, "title": p.title}
                for p in crawl.pages
            ],
            ensure_ascii=False,
        )
        for err in crawl.errors:
            _append_log(job, "警告: " + err)

        if not crawl.pages:
            job.status = "failed"
            job.message = "未抓取到有效页面"
            job.progress = 100
            db.commit()
            return

        job.status = "extracting"
        job.message = "AI 提取中…"
        db.commit()

        draft = ai.extract(crawl)
        job.draft_json = json.dumps(draft, ensure_ascii=False)
        if draft.get("_ai_note"):
            _append_log(job, draft["_ai_note"])
        job.status = "done"
        job.progress = 100
        job.message = "完成，等待人工校对"
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        job = db.get(models.ProbeJob, job_id)
        if job:
            job.status = "failed"
            job.message = f"任务异常: {e}"
            job.progress = 100
            _append_log(job, f"异常: {e}")
            db.commit()
    finally:
        db.close()
