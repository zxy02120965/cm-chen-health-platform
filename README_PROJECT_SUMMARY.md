# CM Chen 肺结节术前代谢健康管理平台

> 项目状态：前端原型、真实后端基础闭环和 RDS 测试已完成；暂未接入真实 GPT、微信登录和生产部署。

## 1. 项目目标

面向高危肺结节合并营养不良或代谢疾病患者，提供患者端健康管理和医护端工作台。核心业务围绕同一个 `patient_id` 关联，患者端和医护端读取同一份业务数据，仅展示视图不同。

主要闭环：

```text
患者资料/评估 Q1-Q55
        ↓
评估结果与患者分型
        ↓
规则版结构化方案草稿
        ↓
医护编辑、审核
        ↓
PUBLISHED 方案
        ↓
plan_task
        ↓
患者每日执行记录
```

## 2. 当前技术栈

| 层级 | 技术 |
|---|---|
| 患者端/医护端 | Vue 3、Vite、Vue Router |
| 后端 | Python 3、FastAPI、SQLAlchemy 2 |
| 数据库 | MySQL 8 / 阿里云 RDS 测试库 `ai_zxy` |
| 本地兼容 | SQLite 开发回退 |
| 容器化 | Docker Compose |
| 流水线模板 | GitLab CI（当前不执行正式部署） |

## 3. 目录结构

```text
cm-chen-health-platform/
├─ frontend/
│  └─ src/
│     ├─ pages/patient/       患者端页面
│     ├─ pages/care/          医护端页面
│     ├─ components/          公共组件
│     ├─ layouts/             双端布局
│     ├─ router/              Vue Router
│     ├─ stores/              patientStore，共享前端状态/API缓存
│     ├─ config/              Q1-Q55评估配置
│     └─ mock/                原型阶段回退数据
├─ backend/
│  └─ app/
│     ├─ main.py              FastAPI 路由和 DTO
│     ├─ db.py                SQLAlchemy 模型、读写和任务生成
│     ├─ rules.py              当前规则版评估/方案生成器
│     ├─ plan_contract.py      Structured Plan Content Contract
│     └─ missing_data_policy.py 全局缺失数据规则
├─ database/
│  ├─ schema.sql              MySQL V1.0 基线
│  ├─ V1_1__monitoring_messages_history.sql
│  ├─ V1_2__assessment_questionnaire_v1_1.sql
│  ├─ seed_v1.sql
│  └─ *_commented.sql          带字段注释版本
├─ docker-compose.yml
├─ .gitlab-ci.yml
└─ .env                       本机配置，不应提交密码
```

## 4. 患者端页面

患者端为手机端卡片式设计，首页不使用底部导航，保留六宫格入口：

| 路由 | 页面 |
|---|---|
| `/patient/home` | 我的/患者首页 |
| `/patient/profile` | 个人资料（身份信息） |
| `/patient/archive` | 健康档案首页 |
| `/patient/archive/:sectionId` | 分组评估页面 |
| `/patient/assessment/result` | 综合评估结果 |
| `/patient/medical-files` | CT、病理、检验等医疗资料 |
| `/patient/plan` | 当前已发布专属方案 |
| `/patient/records` | 数据记录首页 |
| `/patient/records/body` | 体重、体脂率、腰围 |
| `/patient/records/diet` | 饮食记录 |
| `/patient/records/exercise` | 多运动项目记录 |
| `/patient/records/pulmonary` | 多肺预康复项目记录 |
| `/patient/records/trend` | 健康趋势 |
| `/patient/knowledge` | 知识科普列表 |
| `/patient/knowledge/:id` | 宣教内容详情/视频号二维码占位 |
| `/patient/consult` | 在线人工咨询 |
| `/patient/services` | 随访、提醒、预约等服务 |

首次评估使用集中配置 [assessmentQuestions.js](frontend/src/config/assessmentQuestions.js)，正式版本为 `Assessment Questionnaire V1.1`，题号为 Q1-Q55。Q1-Q4 从患者基础资料读取，不在健康评估中重复保存；Q50 为肝弹性成像，Q51-Q55 为执行能力、偏好、家属协助和健康目标。

## 5. 医护端页面

医护端为桌面后台，一级导航为：

- 工作台 `/care/dashboard`
- 患者管理 `/care/patients`
- 待办管理 `/care/todos`
- 监测与预警 `/care/alerts`
- 咨询管理 `/care/consults`
- 系统管理 `/care/settings`

患者详情路径：

```text
/care/patients
    → /care/patients/:id
    → 患者360：总览、患者档案、评估结果、方案管理、数据监测、咨询记录、历史记录
```

评估管理和方案管理已合并到待办管理 Tab；宣教内容管理放在系统管理。

## 6. 真实 API

基础接口：

- `GET /api/health`
- `GET /api/patients`
- `GET /api/patients/{patient_id}`
- `GET/PUT /api/patients/{patient_id}/profile`
- `GET/PUT /api/patients/{patient_id}/assessment`
- `GET /api/patients/{patient_id}/assessment/result`
- `POST /api/patients/{patient_id}/assessment/review`
- `POST /api/patients/{patient_id}/plans/draft`
- `GET /api/patients/{patient_id}/plan`
- `PUT /api/patients/{patient_id}/plan`
- `POST /api/patients/{patient_id}/plans/review`
- `GET /api/patients/{patient_id}/plan/tasks`
- `GET/POST /api/patients/{patient_id}/records`
- `GET/POST /api/patients/{patient_id}/measurements`
- `GET/POST /api/consultations`
- `GET/POST /api/consultations/{consultation_id}/messages`
- `GET /api/education`
- `GET /api/monitoring/alerts`
- `GET /api/dashboard/summary`
- `GET /api/todos`

患者端 `/plan` 默认只返回最新 `PUBLISHED` 版本。医护端审核页面可通过 `include_unpublished=true` 读取当前草稿/审核版本。

## 7. Structured Plan Content Contract

规则版生成器和未来 AI Gateway 共用同一结构，不建立两套方案模型：

```text
management_period
stage_goals
diet_plan
exercise_plan
pulmonary_prehab_plan
monitoring_plan
safety_rules
clinician_notes
missing_data
mdt_pending_items
```

当前规则生成器不会虚构菜谱、克重、能量、运动剂量或医学阈值。无法确定的内容保留 `null`、`unknown` 或“待医护/MDT确认”。肺预康复使用现有动作编号 P01-P05；当前示例至少输出 P01 缩唇呼吸和 P02 腹式呼吸，剂量可为空。

任务职责：

```text
plan = 医护审核发布的应该做什么
plan_task = 从 PUBLISHED plan 结构化出的执行任务
patient_record = 患者实际上完成了什么
```

重复读取同一发布版本不会重复生成任务；历史方案和历史任务保留，患者接口只读取当前有效版本。

## 8. 数据库状态

MySQL V1.0/V1.1 文件覆盖患者、评估、评估结果、患者分型、目标、方案版本、审核、任务、执行记录、咨询、宣教、监测预警、业务事件和审计等对象。

重要现实结构：当前真实 RDS 中评估答案使用：

```text
assessment.answers_json
```

Q1-Q55 通过 JSON 快照持久化；`assessment_answer` 属于旧设计/未落地的可查询单题表，当前业务代码不依赖它，不应为本项目额外补建或强制使用。

当前 RDS 测试闭环最近结果（P001）：

- `assessment_id = 10`
- `question_schema_version = Q1-Q55-v1.1`
- `plan_id = 1`
- 最新 `plan_version_id = 9`
- 状态：`PUBLISHED`
- `plan_task`：DIET 4、EXERCISE 1、PULMONARY_PREHAB 2

## 9. 缺失数据和医学安全边界

全局规则位于 [missing_data_policy.py](backend/app/missing_data_policy.py)：

- 缺失不能猜测、插值或默认正常；
- 明确选择“无”必须和 `null/unknown` 区分；
- 选填数据缺失通常不阻止整体方案生成；
- 无法判断时输出“数据不足/未评估/需补充检查/需MDT判断”；
- A-F 表型、疾病风险、执行能力、安全等级彼此分开；
- 肝弹性只作为肝脏代谢/纤维化风险修饰，不凭单次 LSM 诊断 F0-F4 或肝硬化；
- 未经 MDT 确认的红黄灯阈值、剂量、能量目标和进阶条件不得写死。

## 10. 本地启动

### 后端（连接当前 `.env` 指定数据库）

```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --lifespan off
```

`--lifespan off` 用于只启动 API、避免开发预览时执行启动建表钩子。健康检查：

```text
http://localhost:8000/api/health
```

### 前端

```powershell
cd frontend
..\node_modules\.bin\vite.cmd --host 0.0.0.0 --port 5173 --configLoader runner
```

访问：

- 患者端：http://localhost:5173/patient/home
- 医护端：http://localhost:5173/care/dashboard
- API 文档：http://localhost:8000/docs

前端开发代理已指向 `http://127.0.0.1:8000`，用于避免 Windows 下 `localhost` 解析到 IPv6 `::1` 导致 API 代理失败。

## 11. 测试与构建

后端：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m compileall -q app
```

当前结果：`3 passed`，Python 编译检查通过。

前端：

```powershell
cd frontend
..\node_modules\.bin\vite.cmd build --configLoader runner
```

当前 Vite 构建通过。

## 12. 当前未完成或仍为 Mock

- 正式微信登录、患者注册体系和 SSO；
- 真实 GPT/AI Gateway；
- AI 自由问答；
- 图片 OCR、CT/病理自动分析；
- 设备自动同步和正式微信提醒；
- 部分趋势、知识科普、咨询和预警页面仍保留 Mock 回退；
- 生产级权限、对象存储、审计增强和跨设备实时推送；
- 真实 API 完整覆盖所有每日记录页面。

## 13. 后续建议

1. 先以当前结构化方案合同为 API DTO 规范，补齐前端每日记录到真实 API 的映射。
2. 将医护编辑从高级 JSON 编辑逐步升级为结构化表单，但仍保存同一份方案 JSON。
3. 在测试环境完成 Flyway/Liquibase 迁移管理后，再考虑生产部署。
4. AI 接入时复用 `GLOBAL_MISSING_DATA_RULE` 和 `plan_contract.py`，所有结果继续经过医护审核后发布。

本文件是当前工程状态总结；具体字段和 SQL 以 `database/` 下版本文件及实际 RDS 检查结果为准。
