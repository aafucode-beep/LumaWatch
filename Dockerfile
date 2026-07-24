# syntax=docker/dockerfile:1

# ---------- 阶段 1：构建前端 ----------
FROM node:20-bookworm AS frontend
WORKDIR /web
# 同源部署时前端用相对路径 /api，故 VITE_API_BASE 默认留空
ARG VITE_API_BASE=""
ENV VITE_API_BASE=${VITE_API_BASE}
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：Python 后端 + Playwright ----------
# Playwright 官方镜像已内置 Chromium 及系统依赖，省去手动装库
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# 将前端构建产物放入 backend/static，由 FastAPI 直接托管 SPA
COPY --from=frontend /web/dist ./static

# 数据目录（SQLite + 抓取缓存），部署时挂载到宿主机
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
