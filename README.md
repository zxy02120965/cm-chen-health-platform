# CM Chen 肺结节术前代谢健康管理平台

第一版工程骨架：

- `frontend/`：Vue 3 + Vite 患者端/医护端原型
- `backend/`：Python FastAPI 业务 API（先采用 Python，后续可按同一 API 契约替换为 Java）
- `database/`：MySQL 表结构和初始化演示账号
- `.gitlab-ci.yml`：GitLab CI 测试、构建、镜像和部署模板

## 本地启动

首次启动前请复制 `.env.example` 为 `.env`，填写本地或部署环境的数据库连接参数；密码只保存在本机 `.env`，不要提交到 Git。

使用 RDS 时，请在未跟踪的 `.env` 中配置 `DB_HOST`、`DB_PORT`、`DB_NAME`、`DB_USER` 和 `DB_PASSWORD`，建议直接启动 `backend`，然后单独启动前端：

```bash
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

如需使用 Docker 内置 MySQL 演示，请在 `.env` 中将 `DB_HOST` 改为 `mysql`，并另外填写 `MYSQL_ROOT_PASSWORD`，再执行下面的 Compose 命令。

```bash
cp .env.example .env
docker compose up --build
```

前端默认访问 `http://localhost:5173`，API 文档访问 `http://localhost:8000/docs`。

没有 Docker 时，也可以分别启动：

```bash
cd frontend
corepack enable
pnpm install
pnpm run dev

cd backend
python -m venv .venv
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 当前实现边界

当前版本用于开发和流程验证，不连接真实小程序账号、真实患者数据或真实 AI 服务。方案生成接口会先使用可审计的规则草稿，后续在后端把 `generate_plan_draft` 接到经批准的模型服务；发布前始终保留一名医护审核。

### 前端原型入口（V1.0）

- 患者端：`/patient/home`，健康档案按 8 个页面承载 Assessment Questionnaire V1.1 的 Q1–Q55，数据可通过 API 持久化。
- 医护端：`/care/dashboard`，可进入患者列表和患者360；跨患者评估、方案、监测、咨询等菜单先以原型状态展示。
- 首次评估字段唯一配置：`frontend/src/config/assessmentQuestions.js`。当前图片资料只上传、保存和查看，不做识别。

## GitLab 部署变量

流水线的正式部署任务需要在 GitLab CI/CD Variables 中配置：`DEPLOY_HOST`、`DEPLOY_USER`、`DEPLOY_PATH`、`SSH_PRIVATE_KEY`，以及生产环境的数据库和 AI 服务变量。不要把密钥写入仓库。
