# 后端 API（FastAPI）

## 配置 MySQL

不要把数据库密码写入代码。复制项目根目录的 `.env.example` 为 `.env`，填写实际值：

```dotenv
MYSQL_DATABASE=your_database_name
MYSQL_USER=your_database_user
MYSQL_PASSWORD=your_database_password
MYSQL_ROOT_PASSWORD=your_mysql_root_password
DB_HOST=your-rds-host.example.com
DB_PORT=3306
```

RDS 或其他 MySQL 连接参数由未跟踪的 `.env` 提供。文档不记录具体主机、数据库名、用户名或密码；密码只填写在本机 `.env`，不要提交到 Git。

直接运行后端时，FastAPI 会自动读取项目根目录 `.env`，并把 `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` 传给 SQLAlchemy。如果你使用已有的 MySQL 服务，请确保网络白名单已放行当前客户端 IP，且账号拥有目标数据库的读写及建表权限。

Docker Compose 默认仍会启动项目内置 MySQL，适合本地完整演示。使用上述 RDS 时，建议直接在 `backend` 目录启动 API，避免同时启动不需要的本地 MySQL：

```bash
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

如果从 Linux/macOS 启动，将虚拟环境路径替换为 `.venv/bin/uvicorn`。
后端使用 SQLAlchemy 的 `URL.create` 组装连接串，因此密码中的 `@` 不需要手动改成 `%40`。

## 启动

```bash
docker compose up --build
```

首次创建 MySQL 数据卷时，Compose 会依次执行：

1. `database/schema.sql`
2. `database/V1_1__monitoring_messages_history.sql`
3. `database/V1_2__assessment_questionnaire_v1_1.sql`
4. `database/seed_v1.sql`

已有数据卷不会重复执行初始化脚本。正式环境请使用 Flyway/Liquibase，并先在预发布环境验证。

## 已实现接口

- `GET /api/health`
- `GET /api/patients`
- `GET /api/patients/{patient_id}`
- `GET/PUT /api/patients/{patient_id}/assessment`
- `POST/GET /api/patients/{patient_id}/plans/draft`、`/plan`
- `POST /api/patients/{patient_id}/plans/review`
- `GET/POST /api/patients/{patient_id}/records`
- `GET/POST /api/patients/{patient_id}/measurements`
- `GET /api/consultations`
- `POST /api/patients/{patient_id}/consultations`
- `GET/POST /api/consultations/{consultation_id}/messages`
- `GET /api/education`
- `POST /api/education/{education_id}/publish`
- `GET /api/dashboard/summary`

方案、评估、记录、咨询消息和业务事件均按 `patient_id` 关联。当前未接正式登录、GPT、文件对象存储和生产级权限控制。

评估正式版本为 `Assessment Questionnaire V1.1`（Q1-Q55）。全局缺失数据约束位于 `app/missing_data_policy.py`，确定性规则和未来 AI 入口都应复用该约束。
