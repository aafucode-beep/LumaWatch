"""FastAPI 应用入口。"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, SessionLocal, engine
from .fts import init_fts
from .routers import auth, companies, probe, tags


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表 + 初始化 FTS
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_fts(db)
    finally:
        db.close()
    yield


app = FastAPI(title="建筑照明网站情报库 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(tags.router)
app.include_router(probe.router)


@app.get("/api/health")
def health():
    from .ai.client import is_configured

    return {
        "status": "ok",
        "llm_configured": is_configured(),
        "llm_model": settings.llm_model,
    }


# 生产环境：托管前端静态文件（构建产物放到 backend/static）
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(_STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # 未命中 API 时返回前端入口，交给前端路由
        index = os.path.join(_STATIC_DIR, "index.html")
        target = os.path.join(_STATIC_DIR, full_path)
        if full_path and os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(index)
