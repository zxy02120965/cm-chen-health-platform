# 前端双端数据一致性复核（V1.0/V1.1）

复核原则：同一 `patient_id`、同一业务对象、患者端与医护端只做不同展示。

## 已统一

| 对象 | 统一来源/关系 | 结论 |
|---|---|---|
| patient / patient_profile | `mock/patients.js` + `patientStore.patientProfileData` | 患者首页、个人资料、患者列表、患者360共用 |
| Q1-Q55 V1.1 assessment | `assessmentByPatient`/API，配置来自 `assessmentQuestions.js` | 评估页保存后患者360读取同一答案；Q1-Q4关联patient资料 |
| assessment_result | `patientStore.assessmentResultData` | 患者结果页与患者360结果页共用摘要 |
| plan / plan_version / review | `patientStore.planData`、`plansByPatient` | 编辑、审核意见、状态流转、发布均写入同一 localStorage |
| plan_task / patient_record | `mockPublishedPlanTasks` + `dailyRecords` | 计划值只读，患者实际执行记录供方案页和医护监测读取 |
| consultation / message | `consultations.js` + `consultationsByPatient` | 患者端、咨询队列、患者360共享会话与多轮消息 |
| education_content | `mock/knowledge.js` | 患者只显示 PUBLISHED，系统管理使用同一内容列表 |
| notification / activity | `mock/activities.js` | 患者首页与工作台使用同一动态对象 |
| todo / alert | `careTodos.js`、`careAlerts.js`，带 localStorage 状态 | 工作台统计、跨患者列表与详情跳转共用 |

## 本轮已修正

- 工作台待办事项不再维护独立数组，改从待办 Mock 列表计算。
- 患者列表“未处理咨询”改为从共享咨询数据计算。
- 评估结果摘要集中到 `assessmentResultData`。
- 宣教内容增加发布状态，患者端过滤未发布内容。
- 方案状态变化同步待办：审核通过进入待发布，正式发布后移除，退回进入已退回。
- 患者评估最终提交会写入待审核评估待办。

## 仍是 Mock / 待真实 API

- 预警由 `careAlerts.js` Mock 事件提供，尚未由后端规则根据监测记录生成。
- `mockPublishedPlanTasks` 是发布方案任务的前端样例，尚未从 `plan_task` API读取。
- localStorage 不提供跨浏览器实时推送；真实 API 接入时替换 store 数据源即可。
- 医护审核评估的正式动作、通知推送、文件存储、设备同步和认证仍待后端实现。

## 数据库结论

V1.0 已覆盖主业务表、历史版本、方案审核、任务、执行记录、宣教、通知和审计。V1.0原本缺少可独立查询的监测预警、多轮消息及业务事件表，已通过 `V1_1__monitoring_messages_history.sql` 增量补齐；不覆盖 V1.0。
