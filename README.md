# LumaWatch

LumaWatch 是一个面向建筑照明行业的私有网站情报工具。它从用户明确提供的企业官网开始，在遵守站点规则和限速设置的前提下抓取公开页面，再通过兼容 OpenAI API 的大模型提取企业、产品线、办公地点、资料下载和行业动态等结构化信息，供人工复核、检索和标记。

> 当前阶段聚焦核心采集、整理与检索流程。每日定时监测（daily scheduled monitoring）已明确延期，待第一阶段稳定完成后再设计和启用。

## 当前能力

- 单用户口令登录与 JWT 会话
- 企业官网探测、页面发现和正文清洗
- 静态抓取优先，必要时使用 Playwright 渲染 JavaScript 页面
- `robots.txt` 遵循、抓取间隔、页数上限和超时控制
- 大模型结构化提取；未配置模型密钥时可降级到规则处理
- SQLite 存储与 FTS5 全文检索
- 多维标签筛选：同一维度 OR、跨维度 AND
- 企业列表、详情、探测工作台和标签管理界面
- React Web/PWA 前端，并预留 Capacitor Android 配置
- Docker、Caddy 和 HTTPS 部署基础

## 技术结构

```text
backend/                 FastAPI 后端
  app/
    ai/                  模型调用、提示词与提取流程
    crawler/             页面发现、抓取、清洗与 robots.txt
    routers/             鉴权、企业、探测和标签 API
    services/            业务服务
frontend/                React + TypeScript + Vite + Ant Design
  src/pages/             登录、企业、详情、探测和标签页面
docs/                    部署说明、状态、增强建议与路线图
Dockerfile               前端构建与后端运行镜像
docker-compose.yml       后端与 Caddy 编排
Caddyfile                静态资源、API 反向代理和 HTTPS
```

## 安全启动

### 1. 准备后端配置

复制示例文件，但不要把真实配置提交到 Git：

```powershell
Copy-Item backend/.env.example backend/.env
```

至少替换以下值：

- `APP_PASSWORD`：仅供本实例管理员使用的强口令
- `SECRET_KEY`：独立生成的高熵随机字符串，用于 JWT 签名
- `LLM_API_KEY`：需要启用模型提取时再配置

`backend/.env` 已被 `.gitignore` 排除。不要把密钥放入 README、截图、日志、Issue、聊天记录或前端代码；浏览器端的任何值都应视为可公开读取。

### 2. 本地开发

后端要求 Python 3.11+：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload
```

前端要求 Node.js 20+：

```powershell
Set-Location frontend
npm ci
npm run dev
```

开发环境默认前端地址为 `http://localhost:5173`。生产环境应使用 HTTPS，并把 `CORS_ORIGINS` 限制为实际受信任的前端域名。

### 3. Docker 部署

根目录 `.env` 只用于设置 Caddy 域名，后端敏感配置仍放在 `backend/.env`：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

正式部署前请阅读 [部署说明](docs/DEPLOYMENT.md)，确认端口、磁盘空间、反向代理、TLS 证书和持久化目录符合目标服务器环境。

## 数据与隐私边界

- 仅输入你有权处理的网站和数据源。
- 默认抓取公开网页；登录后内容、付费内容和个人数据不应在没有明确授权时采集。
- 尊重 `robots.txt`、网站条款、版权、访问频率限制和适用法律。
- 抓取内容会进入本地数据库和缓存；部署者负责其访问控制、备份、保留周期与删除。
- 发送给模型提供商的页面文本受该提供商的数据政策约束。处理敏感内容前，应选择合适的服务、区域和保留策略。
- 模型输出可能不准确。入库或用于业务判断前应人工复核，并保留来源链接以便追溯。

## 当前阶段与路线

第一阶段的重点是验证核心产品链路：安全登录、受控抓取、结构化提取、人工复核、检索与标签管理。真实站点和真实模型调用仍需在受控环境中验证。

每日定时监测暂不启用。后续设计需要先明确任务调度、失败重试、去重、变更检测、通知、成本上限、访问频率和审计日志，避免在核心流程尚未稳定时扩大数据、费用与运行风险。

更多信息见：

- [项目状态](docs/PROJECT_STATUS.md)
- [部署说明](docs/DEPLOYMENT.md)
- [增强建议](docs/ENHANCEMENTS.md)
- [后续路线图](docs/ROADMAP.md)

## 重要安全说明

仓库安全检查发现一项需要后续单独处理的凭据风险。本阶段按项目所有者决定暂不修改相关记录，也不执行撤销、轮换或 Git 历史重写。任何历史清理都需要先评估协作者影响，并可能涉及强制推送，因此必须作为独立、明确授权的维护操作进行。
