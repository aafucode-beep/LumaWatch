# 后续路线图（ROADMAP）

> 建筑照明网站情报库 · 2026-07-24
> 本文是真正的「下一步该做什么」，区别于 `ENHANCEMENTS.md`（功能级建议）和 `PROJECT_STATUS.md`（已完成项）。

## 一、立即可做（今天/明天）

| # | 事项 | 说明 | 阻塞/前置 |
|---|------|------|-----------|
| 1 | **撤销 GitHub token** | `[REDACTED_GITHUB_PAT]` 经聊天传输过，必须撤销 | 无 |
| 2 | **修本机 `git push` 的 schannel 失败** | `git.exe` 在你这台机器上 TLS 握手失败，导致本地 git 推送走不通（不得不绕路 Contents API） | 排查方向：① git 版本 vs Windows 10/11 schannel 兼容 ② 是否有企业代理/防火墙劫持 TLS ③ `git config --global http.sslBackend openssl` |
| 3 | **清理 `%TEMP%\vpsinfo\`** | 之前为读取参考仓库解码出来的服务器文件副本 | 手动 `Remove-Item` |
| 4 | **本地 `docs/PROJECT_STATUS.md` 暂不入库** | 当前远端 SHA `c515e43` 是通过 Contents API 建的；本地这文件是 untracked 状态，**不要 git commit**，否则会与远端产生分叉；如要入本地库，先 `git reset --hard origin/main` 后再决定 | 等 git push 修好后再统一提交 |

## 二、本周可做

| # | 事项 | 说明 |
|---|------|------|
| 5 | **磁盘清理/扩容** | vpsDYB 磁盘 76G/79G = 100%。部署照明情报库前必须清掉旧 Docker 镜像、journald 日志、apt 缓存，或直接扩容云盘 |
| 6 | **部署到 vpsDYB** | 用我之前给的 Nginx 集成版步骤：清盘 → DNS A 记录 `intel.rvs-lighting.com` → 克隆到 `/root/tokenHUB/tokenDYB/websiteinfodetection` → 仅跑后端容器 `127.0.0.1:8000:8000` → 现有 Nginx 反代 → certbot 上证书。前端 dist 直接走 Nginx 静态站点 |
| 7 | **首次真实爬取冒烟** | 在服务器上跑一次端到端：随便挑 1 个照明企业官网（如 Erco、iGuzzini）→ 提交探测 → 看 AI 提取是否合理 → 修正 JSON schema 提示词（如需要） |
| 8 | **真实环境变量配置** | 在服务器上填 `backend/.env`：`APP_PASSWORD` / `SECRET_KEY`（openssl rand -hex 32）/ `LLM_API_KEY`（MiniMax）/ `LLM_BASE_URL` / `LLM_MODEL` |

## 三、短期（1-2 周）

| # | 事项 | 价值 |
|---|------|------|
| 9 | **打 Android APK** | 当前 Capacitor 已配好但未出包。流程：`VITE_API_BASE=https://intel.rvs-lighting.com npm run build` → `npx cap add android` → `npm run cap:sync` → `npm run cap:open` → Android Studio 出包 |
| 10 | **启用 PG 替代 SQLite**（可选） | vpsDYB 已有 PostgreSQL；多设备/并发写场景更稳。`backend/app/services/fts.py` 已有 `IS_SQLITE` 分支可平滑切换 |
| 11 | **去重合并功能落地** | `docs/ENHANCEMENTS.md` 第 3 项：探测时不同 URL 命中同一企业的自动合并（rapidfuzz 相似度） |
| 12 | **导出 Excel/Markdown** | `docs/ENHANCEMENTS.md` 第 1 项：方便线下分享/汇报 |

## 四、中期（1-2 月）

| # | 事项 | 价值 |
|---|------|------|
| 13 | **新闻自动归集** | 周期性任务把企业「最新动态」拉成时间线（`docs/ENHANCEMENTS.md` 第 2 项） |
| 14 | **来源可溯源展示** | 每条提取数据点关联到具体网页段落，详情页可点击跳转原文（`docs/ENHANCEMENTS.md` 第 4 项） |
| 15 | **批量探测队列增强** | 失败重试、限速、按 tag 批量提交（`docs/ENHANCEMENTS.md` 第 5 项） |
| 16 | **备份策略** | SQLite 文件 `/data/app.db` 每日 cron 打包 + 异地存（或推回 GitHub 私有备份仓库）。当前没做，存在硬盘故障丢数据风险 |
| 17 | **访问审计日志** | 后端记录每次登录、探测、编辑的企业+时间，便于回溯「谁动了什么」 |

## 五、长期/可选

| # | 事项 | 说明 |
|---|------|------|
| 18 | **多用户/角色** | 现在是单密码登录；如未来要给同事/外包用，加 RBAC |
| 19 | **企业图谱/关系网** | 在多维 tag 基础上做「同集团子公司」「上下游供应商」关系图（爬母公司/品牌矩阵站点自动识别） |
| 20 | **数据可视化大屏** | 把「全球办公网点地理分布」「产品线覆盖度」做成可视化页面（可考虑 AntV / Deck.gl） |
| 21 | **CI/CD** | GitHub Actions：push 触发 → build docker image → 自动部署到 vpsDYB（需先打通本机 git push + 服务器 ssh 公钥） |

## 六、明确**不做**的事

- ❌ **不要把 `vpsinfo` 的功能合进来**——vpsinfo 是服务器状态监控，与照明情报库目的不同。
- ❌ **不要在生产环境启用 Caddy**——vpsDYB 的 Nginx 已占 80/443。
- ❌ **不要把 `APP_PASSWORD` 提交进 git**——目前 `.env.example` 是占位，真实密钥只能放服务器或本地密钥管理器。

---

## 附：当前 git/远端一致性速查

- 本地分支 `main` HEAD：`44ad7e5`
- 远端分支 `origin/main` HEAD：`c515e43`（含 `docs/PROJECT_STATUS.md`）
- 本地 working tree 有 untracked：`docs/PROJECT_STATUS.md`（不提交，等 git push 修好再说）
- 本次路线图文档将通过 Contents API 推至远端，新提交后远端 HEAD 会再 +1