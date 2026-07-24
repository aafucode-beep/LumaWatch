# 部署指导（Docker + Caddy）

建筑照明网站情报库的生产部署说明。后端（FastAPI）在容器内同时托管前端 SPA 静态资源与 `/api` 接口，Caddy 负责反向代理与自动 HTTPS。

## 一、前置条件

- 一台海外服务器（可直连国际网站与大模型 API），已安装 **Docker** 与 **Docker Compose 插件**。
- 一个域名，其 A 记录已指向服务器公网 IP（Caddy 申请 Let's Encrypt 证书需要域名解析生效）。
- 一个 OpenAI 兼容的大模型 API Key（默认 MiniMax CN）。

## 二、部署步骤

### 1. 拉取代码

```bash
git clone <你的仓库地址> lighting-intel
cd lighting-intel
```

### 2. 配置后端环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，**务必修改**以下项：

| 变量 | 说明 |
|------|------|
| `APP_PASSWORD` | 登录口令（单用户鉴权） |
| `SECRET_KEY` | JWT 签名密钥，建议 `openssl rand -hex 32` 生成 |
| `LLM_API_KEY` | 你的大模型 API Key |
| `LLM_BASE_URL` / `LLM_MODEL` | 如非默认 MiniMax，按供应商调整 |

其余爬取参数（页数、限速、是否遵守 robots、是否启用 Playwright）可按需调整。

### 3. 配置域名（Caddy 自动 HTTPS）

```bash
cp .env.example .env
```

编辑根目录 `.env`，把 `DOMAIN` 改成你的真实域名：

```
DOMAIN=intel.yourdomain.com
```

> 本地/无域名调试可用 `DOMAIN=localhost`，Caddy 会签发本地自签证书。

### 4. 启动

```bash
docker compose up -d --build
```

首次构建会拉取 Playwright/Chromium 镜像、安装依赖并编译前端，耗时数分钟。

### 5. 验证

浏览器访问 `https://你的域名`，使用 `APP_PASSWORD` 登录，跑通完整链路：

> 提交 URL → 探测抓取 → AI 生成草稿 → 人工校对入库 → tag 多重筛选 → 点击 tag 反查企业。

## 三、数据与运维

- **数据持久化**：SQLite 数据库位于宿主机 `./data/`（`docker-compose.yml` 已挂载卷），重建容器不会丢数据。
- **日志**：`docker compose logs -f backend` / `docker compose logs -f caddy`。
- **升级**：

  ```bash
  git pull
  docker compose up -d --build
  ```

- **备份**：直接备份宿主机 `./data/app.db` 文件即可。

## 四、安卓 APK 打包（可选，在本地开发机执行）

APK 与网站不同源，必须通过 `VITE_API_BASE` 指向后端 HTTPS 域名。

```bash
cd frontend
# 1. 用服务器域名构建前端
VITE_API_BASE=https://intel.yourdomain.com npm run build
# 2. 首次初始化安卓平台
npx cap add android
# 3. 同步产物
npm run cap:sync
# 4. 打开 Android Studio 出包（或用 gradlew assembleRelease）
npm run cap:open
```

## 五、故障排查

| 现象 | 排查方向 |
|------|----------|
| HTTPS 证书申请失败 | 确认域名 A 记录已生效、服务器 80/443 端口对外开放 |
| 登录失败 | 检查 `backend/.env` 的 `APP_PASSWORD` 是否已生效（改后需重建后端容器） |
| AI 提取返回空/降级草稿 | 检查 `LLM_API_KEY`、`LLM_BASE_URL` 是否正确，容器能否访问外网 |
| 抓取失败 | 目标站可能有反爬或超时，调大 `CRAWL_TIMEOUT`；确认 `CRAWL_USE_PLAYWRIGHT=true` |
