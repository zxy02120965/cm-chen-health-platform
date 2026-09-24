-- ============================================================================
-- MySQL V1.1 增量迁移（带中文注释版）
-- ============================================================================
-- 用途：在已有 MySQL V1.0 基础上补充：
--   1) 监测异常/预警队列
--   2) 在线咨询多轮消息
--   3) 评估、方案、咨询、提醒等业务事件历史
--
-- 重要说明：
--   * 本文件与 V1_1__monitoring_messages_history.sql 的建表逻辑保持一致，
--     仅增加说明性注释，方便工程师审核。
--   * 执行前必须先执行 database/schema.sql（V1.0），因为本迁移引用了
--     patient、patient_record、clinician_account、consultation 等表。
--   * IF NOT EXISTS 适合演示环境或可控的增量初始化。正式环境建议由
--     Flyway/Liquibase 管理版本，并在预发布数据库验证后再执行。
--   * 本版本不写入任何医学红黄绿阈值；颜色/安全等级由已确认的规则服务提供。

SET NAMES utf8mb4;

-- ============================================================================
-- 一、监测异常表 monitoring_alert
-- ============================================================================
-- 一条记录代表一次需要医护处理或留痕的监测异常。
-- 来源可以是体重、体脂、腰围、血压、运动、肺预康复等患者记录，
-- 也可以是评估资料缺失等系统事件。
-- 患者端展示风险提示，医护端“监测与预警”读取同一张表。
CREATE TABLE IF NOT EXISTS monitoring_alert (
  -- 自增主键；不使用 patient_id + alert_type 作为唯一键，允许同类异常多次发生。
  alert_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '监测异常记录自增主键',

  -- 核心业务关联键；必须与 patient.patient_id 一致。
  patient_id VARCHAR(32) NOT NULL COMMENT '患者业务ID，关联 patient.patient_id',

  -- 可选：触发该异常的患者每日记录；资料缺失类异常可以为空。
  record_id BIGINT UNSIGNED NULL COMMENT '触发异常的患者记录ID，可为空',

  -- 异常类型，例如“体重趋势关注”“肺康复不适”“评估资料缺失”。
  alert_type VARCHAR(100) NOT NULL COMMENT '异常类型或提醒类型',

  -- 触发时用于医护列表显示的原始值或摘要；不承担医学判断逻辑。
  latest_value VARCHAR(160) NULL COMMENT '触发异常时的最新值或摘要',

  -- 趋势摘要，例如“上升”“下降”“本周波动需复核”；具体计算由后端规则提供。
  trend VARCHAR(80) NULL COMMENT '趋势摘要，由规则或后端提供',

  -- 展示/处置等级。当前仅保存规则结果，不在数据库中定义阈值。
  safety_level ENUM('green','yellow','red') NOT NULL COMMENT '安全显示等级，不代表数据库内置医学阈值',

  -- PENDING=待处理；HANDLED=已处理；DISMISSED=已忽略/关闭。
  status ENUM('PENDING','HANDLED','DISMISSED') NOT NULL DEFAULT 'PENDING' COMMENT '异常处理状态：待处理、已处理、已关闭',

  -- 异常产生时间，用于医护队列排序和患者动态时间线。
  triggered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '异常触发时间',

  -- 处理该异常的医护账号；未处理时为空。
  handled_by BIGINT UNSIGNED NULL COMMENT '处理异常的医护账号ID',

  -- 异常处理完成时间。
  handled_at DATETIME NULL COMMENT '异常处理完成时间',

  -- 医护处理备注或规则说明；不替代正式病历记录。
  note TEXT NULL COMMENT '医护处理备注或规则说明',

  -- 支持医护端按状态、等级、时间查询待办队列。
  INDEX idx_alert_queue (status, safety_level, triggered_at),
  -- 支持患者360和患者端按患者查看异常历史。
  INDEX idx_alert_patient (patient_id, triggered_at),

  CONSTRAINT fk_alert_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_alert_record FOREIGN KEY (record_id) REFERENCES patient_record(record_id),
  CONSTRAINT fk_alert_handler FOREIGN KEY (handled_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- 二、咨询消息表 consultation_message
-- ============================================================================
-- consultation 保存会话级信息（咨询类型、状态、患者等）；
-- 本表保存会话内的每一条消息，从而支持：
-- 患者提问 -> 医护回复 -> 患者追问 -> 医护再次回复。
-- 患者端和医护端通过 consultation_id 读取同一组消息。
CREATE TABLE IF NOT EXISTS consultation_message (
  -- 自增消息主键。
  message_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '咨询消息自增主键',

  -- 所属咨询会话；对应 consultation.consultation_id。
  consultation_id VARCHAR(40) NOT NULL COMMENT '所属咨询会话ID，关联 consultation.consultation_id',

  -- 消息发送方：患者、医护或系统通知。
  sender_type ENUM('PATIENT','CLINICIAN','SYSTEM') NOT NULL COMMENT '消息发送方类型',

  -- 发送方业务账号/标识。患者可使用 patient_id，医护使用 clinician_id 的字符串表示。
  sender_id VARCHAR(120) NULL COMMENT '消息发送方账号或业务ID',

  -- 消息正文；当前原型的文字回复落在此字段。
  message_text TEXT NOT NULL COMMENT '消息正文',

  -- 图片等附件的结构化信息；仅保存元数据/地址，不在此表存二进制文件。
  attachment_json JSON NULL COMMENT '附件元数据JSON，不存放二进制文件本体',

  -- 消息创建时间；同一会话按此字段升序展示消息线程。
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '消息创建时间',

  -- 支持咨询详情按时间读取多轮消息。
  INDEX idx_message_conversation (consultation_id, created_at),

  CONSTRAINT fk_message_consult FOREIGN KEY (consultation_id) REFERENCES consultation(consultation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- 三、业务事件表 business_event
-- ============================================================================
-- 事件表只记录重要业务事件，用于：
--   * 患者首页“最新动态”
--   * 医护端最近动态
--   * 患者360历史记录
-- 它不替代 assessment、plan、patient_record 等业务表，日常数据仍从原业务表读取。
CREATE TABLE IF NOT EXISTS business_event (
  -- 自增事件主键。
  event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '业务事件自增主键',

  -- 事件关联患者；系统级事件可以为空。
  patient_id VARCHAR(32) NULL COMMENT '关联患者ID，系统级事件可为空',

  -- 事件类型。枚举用于约束核心事件名称，OTHER 用于暂未标准化的事件。
  event_type ENUM('ASSESSMENT_SUBMITTED','ASSESSMENT_REVIEWED','PLAN_GENERATED','PLAN_REVIEWED','PLAN_PUBLISHED','PLAN_RETURNED','PLAN_PAUSED','RECORD_SUBMITTED','ALERT_TRIGGERED','CONSULTATION_CREATED','CONSULTATION_REPLIED','EDUCATION_PUBLISHED','OTHER') NOT NULL COMMENT '重要业务事件类型',

  -- 事件对应的业务对象类型，例如 assessment、plan、consultation。
  object_type VARCHAR(60) NULL COMMENT '事件关联的业务对象类型',

  -- 对应业务对象主键/编号；统一使用字符串以兼容不同对象编号格式。
  object_id VARCHAR(80) NULL COMMENT '事件关联的业务对象ID',

  -- 事件发起方：患者、医护、系统或 AI。
  actor_type ENUM('PATIENT','CLINICIAN','SYSTEM','AI') NOT NULL COMMENT '事件发起方类型',

  -- 发起方账号/标识。
  actor_id VARCHAR(120) NULL COMMENT '事件发起方账号或业务ID',

  -- 事件补充信息，例如版本号、状态变化前后值、摘要等。
  payload_json JSON NULL COMMENT '事件补充数据，如版本、状态变更前后值、摘要',

  -- 事件发生时间；用于动态流和历史记录排序。
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '事件发生时间',

  -- 患者360按患者查看重要事件时间线。
  INDEX idx_event_patient_time (patient_id, created_at),
  -- 医护工作台按事件类型和时间查询最近动态。
  INDEX idx_event_type_time (event_type, created_at),

  CONSTRAINT fk_event_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- 执行后的业务对应关系（说明，不是 SQL）
-- ============================================================================
-- patient_record -> monitoring_alert：患者记录触发异常后生成预警。
-- consultation -> consultation_message：一条咨询会话包含多条患者/医护消息。
-- assessment / plan / consultation / alert / education -> business_event：
-- 重要状态变化生成事件，患者端和医护端读取同一事件源的不同视图。
--
-- 当前仍待后端实现：
--   1) 如何根据规则生成 monitoring_alert；
--   2) 如何将计划发布拆分为 DailyTask 并计算完成度；
--   3) 文件实际存储和访问权限；
--   4) 登录鉴权、医护权限、审计追踪；
--   5) 业务事件的去重、重试和归档策略。
