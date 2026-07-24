# 项目状态明细

> 建筑照明网站情报库（websiteinfodetection）· 状态快照
> 更新于 2026-07-24

## 一、一句话概述

输入照明企业官网 URL → 自动爬取 → AI 大模型提取结构化情报（企业信息 / 产品线 / 全球办公网点 / 可下载资料链接 / 行业新闻）→ 人工校对入库 → **多维 tag 检索与反查**、重点企业标记。个人自用，Web + Android。

## 二、GitHub 推送状态

| 项 | 值 |
|----|----|
| 是否已推送 | ✅ **已推送** |
| 仓库 | `yjhkrepo/websiteinfodetection`（Private） |
| 默认分支 | `main` |
| 首次提交 | `44ad7e5` |
| 跟踪文件数 | 56 |
| 本地与远端 | 已同步（`main` ↔ `origin/main`） |
| 安全扫描 | L3 深度审查通过，0 findings |

## 三、完成度总览

| 模块 | 状态 | 说明 |
|------|------|------|
| 后端 API（FastAPI） | ✅ 完成 | 鉴权 / 企业 / 探测 / 标签 四组路由 |
| 爬虫（httpx + Playwright） | ✅ 完成 | 静态优先，JS 渲染兜底；遵守 robots、限速 |
| AI 提取（OpenAI 兼容 / MiniMax） | ✅ 完成 | JSON schema 提取，防 URL 幻觉，无 key 时规则降级 |
| 存储（SQLite + FTS5 全文检索） | ✅ 完成 | 触发器同步全文索引 |
| 前端（React + Vite + AntD） | ✅ 完成 | 登录 / 企业列表 / 企业详情 / 探测工作台 / 标签管理 |
| 多维 tag 筛选（核心价值） | ✅ 完成 | 同维度 OR、跨维度 AND；点击 tag 反查企业 |
| PWA | ✅ 完成 | manifest + service worker（SVG 图标） |
| Android（Capacitor） | ✅ 配置就绪 | 需在本地开发机出包（未打 APK） |
| 部署物（Docker/Caddy） | ✅ 完成 | 多阶段 Dockerfile + compose + Caddyfile |
| 文档 | ✅ 完成 | 部署指导 / 增强路线图 / 本状态文档 |

## 四、已验证 vs 未验证

**已验证：**
- 前端构建通过（`tsc --noEmit && vite build`，产出 dist + PWA sw.js/manifest）。
- 后端可正常 import 启动，路由注册正常。
- 核心端到端冒烟测试通过：鉴权 401→登录→tag 反查→跨维度 AND 筛选→国家分面→FTS 全文→下载链接存在性→tag 合并去重。

**未验证（需在目标服务器完成）：**
- `docker compose build` 实际构建。
- 真实网站爬取 + 真实 MiniMax 大模型调用。
- Android APK 实际打包。

## 五、目录结构（顶层）

```
├── backend/          FastAPI 后端（app/ 下含 ai/ crawler/ routers/ services/）
│   ├── requirements.txt
│   └── .env.example
├── frontend/         React 前端
│   ├── src/pages/    Login/Companies/CompanyDetail/Probe/Tags
│   ├── capacitor.config.ts
│   └── vite.config.ts
├── docs/             DEPLOYMENT.md / ENHANCEMENTS.md / PROJECT_STATUS.md
├── Dockerfile        多阶段：node 构建前端 → playwright-python 运行时
├── docker-compose.yml
├── Caddyfile
└── .env.example
```

## 六、部署目标服务器（vpsDYB）注意事项

> 详见 `docs/DEPLOYMENT.md`。以下为针对现有服务器的关键约束：

- 🔴 **磁盘接近满** —— 部署前需清理/扩容，否则 Docker + Playwright 镜像放不下。
- 🟠 **Nginx 已占用 80/443** —— 不要启用方案中的 Caddy，改用现有 Nginx 反代到后端本地端口（如 `127.0.0.1:8000`），子域名 + certbot 上证书。
- 🟢 服务器已有 PostgreSQL（5432），可选；个人自用 **SQLite 更省事，建议先用**。

## 七、后续可选增强

见 `docs/ENHANCEMENTS.md`：导出 Excel/Markdown、新闻自动归集、相似企业去重合并、来源可溯源展示、批量探测增强、切换 PostgreSQL。
