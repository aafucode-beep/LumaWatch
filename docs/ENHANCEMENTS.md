# 补充功能指导（增强路线图）

本项目已完成核心闭环（探测 → AI 提取 → 人工校对 → 多维 tag 检索与反查）。以下为计划中的可选增强项（对应原计划「阶段 7」及扩展），按实现难度与价值排序，供后续迭代参考。

## 1. 导出 Excel / Markdown

**价值**：把结构化情报导出为可分享/归档文件。

- 后端新增 `GET /api/companies/export?format=xlsx|md`，复用现有筛选参数（tags / is_key / country / q）。
- xlsx 用 `openpyxl` 生成；Markdown 手工拼接表格，流式返回。
- 前端企业列表页加「导出」按钮，携带当前筛选条件。

**涉及**：`backend/app/routers/companies.py`、新增 `backend/app/services/export_service.py`、前端 `CompaniesPage.tsx`。

## 2. 新闻自动归集

**价值**：持续跟踪重点企业动态，减少人工。

- 引入 APScheduler 定时任务，对重点企业（`is_key`）域名周期性重跑新闻页抓取。
- `NewsLink` 已支持 `company_id` 归集；新增 URL 规范化去重，避免重复入库。

**涉及**：`backend/app/crawler/`、新增调度模块、`probe_service.py`。

## 3. 相似企业去重 / 合并

**价值**：清理重复录入，保持库整洁。

- 按 `website` 域名 + 名称相似度（`rapidfuzz`）给出候选重复企业对。
- 新增 `POST /api/companies/merge`，迁移子表（office/product_line/download/news）与 tag 关联到目标企业。

**涉及**：`backend/app/services/company_service.py`（已有 tag 合并逻辑可参考）。

## 4. 来源可溯源展示

**价值**：防幻觉、可核查，提升数据可信度。

- `source_evidence` 表已记录每个 AI 字段的 `source_url` 与 `snippet`。
- 前端详情页在每个 AI 生成字段旁加「出处」气泡，显示原始片段与链接。

**涉及**：前端 `CompanyDetailPage.tsx`、后端序列化补充 evidence 输出。

## 5. 批量探测队列增强

**价值**：大批量导入时更稳、更可控。

- 探测工作台已轮询进度；可加并发限流、失败重试按钮、批量导入 URL（CSV/文本）。

**涉及**：`backend/app/services/probe_service.py`、前端 `ProbePage.tsx`。

## 6. 切换 PostgreSQL（数据量增大时）

**价值**：单表数据量大或需要并发写入时的平滑升级。

- 数据层已做抽象：将 `DATABASE_URL` 改为 `postgresql+psycopg://user:pass@host/db`。
- 全文检索需从 SQLite FTS5 切换到 PostgreSQL 的 `tsvector`/`GIN` 索引；`backend/app/fts.py` 已预留 `IS_SQLITE` 分支。

**涉及**：`backend/.env`、`backend/app/fts.py`、`requirements.txt`（加 `psycopg`）。

---

> 需要实现其中任一项时，可作为新的开发阶段单独推进；建议每项完成后跑一遍端到端验证（探测→草稿→入库→筛选→反查）。
