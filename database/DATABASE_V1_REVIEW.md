# MySQL 数据库 V1.0（工程师审核稿）

## A. ER 关系（以 `patient_id` 为业务主线）

```text
patient 1──1 patient_profile
patient 1──N assessment 1──N assessment_answer
assessment 1──N assessment_result 1──N goal 1──N plan 1──N plan_version
plan_version 1──N plan_review
plan_version 1──N plan_task 1──N patient_record
patient 1──N body_measurement_record
patient 1──N consultation 1──N consultation_reply
patient 1──N document / notification / audit_log
clinician_account N──N patient (patient_clinician_relation)
clinician_account 1──N plan_review / consultation_reply / education_content
```

患者端和医护端只改变展示视图，不复制业务数据。医护发布 `plan_version=PUBLISHED` 后，由任务表生成每日任务；患者提交 `patient_record`，后端再计算任务完成状态和本周完成度。

## B-C. 表清单与关键字段

| 表 | 用途 | 主键/主要外键 |
|---|---|---|
| `patient` | 账号身份：姓名、性别、出生日期、联系方式、头像 | `patient_id` |
| `patient_profile` | A-F表型、疾病/代谢风险、执行能力、安全等级、手术窗口 | PK/FK `patient_id` |
| `assessment` | Q1-Q55 V1.1一次评估的版本、状态、答案快照；Q1-Q4由patient资料关联 | `assessment_id`; FK patient |
| `assessment_answer` | 可查询的单题答案，V1.1题号范围由配置约束；Q1-Q4不重复存储 | FK assessment/patient |
| `assessment_result` | 综合评估结果及 MDT 确认状态 | FK assessment/patient |
| `goal` | 阶段目标及患者期望、目标版本 | FK patient/result |
| `plan` | 方案聚合及当前状态 | FK patient/goal |
| `plan_version` | 不覆盖历史的方案版本与内容 | FK plan |
| `plan_review` | 审核、退回、发布等医护操作记录 | FK plan/version/clinician |
| `plan_task` | 饮食、运动、肺康复任务的计划值 | FK plan_version/patient |
| `patient_record` | 每日执行记录；同日可有多个运动/肺康复项目 | FK patient/task |
| `body_measurement_record` | 体重、体脂、腰围、血压等历史测量 | FK patient |
| `consultation` | 患者咨询主记录与状态 | FK patient |
| `consultation_reply` | 医护回复历史 | FK consultation/clinician |
| `education_content` | 医护发布的图文/视频宣教内容 | FK clinician |
| `notification` | 评估、方案、咨询、提醒、异常等动态 | FK patient |
| `document` | CT、病理、检验报告等文件元数据 | FK patient |
| `clinician_account` | 统一医护账号（当前一名审核医护可用一条记录） | `clinician_id` |
| `patient_clinician_relation` | 患者与医护关系、责任角色 | 复合 PK patient/clinician |
| `audit_log` | 重要操作的前后值与追溯 | `audit_id`; FK patient |

完整字段、类型、索引、枚举和外键约束见同目录 `schema.sql`。

### V1.1 增量项

| 新增表 | 原因 | 前端对应 |
|---|---|---|
| `monitoring_alert` | V1.0只有记录，没有跨患者异常队列 | 医护“监测与预警”、工作台预警数量 |
| `consultation_message` | V1.0只有单条回复，无法保存多轮会话 | 患者在线咨询、医护咨询详情 |
| `business_event` | V1.0审计日志偏操作追溯，缺少业务动态流 | 工作台最新动态、患者360历史记录 |

V1.1不修改V1.0字段；执行文件为 `V1_1__monitoring_messages_history.sql`。

## D-E. 运行文件

- `schema.sql`：MySQL 8.0 基线建表。
- `seed_v1.sql`：P001-P003、统一医护、评估/结果/目标/已发布方案/任务/记录/咨询/宣教等演示数据。
- `schema.sql.v0-backup-20260904`：替换前的原始 schema 备份。
- `V1_1__monitoring_messages_history.sql`：增量补充监测预警、多轮咨询消息和业务事件历史。

## F. 迁移方案

先备份数据库，在测试库执行基线和 seed；生产采用 Flyway/Liquibase，将本文件作为 `V1__baseline.sql`，再执行 `V1_1__monitoring_messages_history.sql`，后续只新增 `V2__...sql`，禁止修改已执行迁移。具体命令和发布检查见 `MIGRATION_V1.md`。

## G. 当前 Mock / 待后端实现

前端当前仍以 localStorage 保存当前患者、趋势点、任务完成、咨询覆盖和预警处理状态；真实登录、文件对象存储、设备采集、消息推送、API DTO 映射均待后端实现。JSON 字段（答案、方案内容、任务排程、记录元数据）先保留弹性，待接口确认后再拆分索引字段。

## H. 医学安全约束

数据库不写死 A-F 分型、疾病风险、安全等级、生命体征/化验异常阈值、BORG 或自动调方案阈值。此类规则由 MDT 确认并版本化；`assessment_result.mdt_confirmation_status` 用于记录确认状态。原型中的红黄绿仅是已有 Mock/规则结果的展示状态，不代表生产医学判断。
