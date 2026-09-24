-- ============================================================================
-- MySQL 8.0 / V1.2 增量迁移：Assessment Questionnaire V1.1 / Q1-Q55（带字段注释版）
-- ============================================================================
-- 用途：将已有 V1.0 评估结构切换到 Assessment Questionnaire V1.1。
--
-- 重要规则：
--   1. 本文件只做增量变更，不删除或覆盖历史 assessment 记录。
--   2. Q1-Q4 是 patient 账号身份资料，在 assessment_answer 中不重复存储。
--   3. assessment.answers_json / assessment_answer.value_json 允许保存 null、
--      明确选择“无”和 other_text；缺失数据不得用 0 或“正常”替代。
--   4. Q27（6分钟步行）、Q45（关键化验）、Q50（肝弹性成像）为选填。
--   5. Q46 选择“无”时，Q47 不强制填写；Q48 选择“无”时，Q49 不强制填写。
--   6. 本文件不要直接在生产 RDS 执行；请先在测试库备份并验证。

SET NAMES utf8mb4;

-- ----------------------------------------------------------------------------
-- 一、评估主表 assessment
-- ----------------------------------------------------------------------------
-- assessment_version：同一患者的历史评估版本号，不能因 Q50 插入而覆盖旧版本。
-- question_schema_version：本条评估所使用的题目版本；新记录使用 Q1-Q55-v1.1。
-- answers_json：结构化答案载荷；Q5-Q55 以配置 key 保存，Q1-Q4 从 patient 读取。
-- status：评估业务状态；DRAFT/提交/审核/完成/退回由后端流程维护。
-- data_completeness：资料充分度，可为空；不代表医学风险等级。
ALTER TABLE assessment
  MODIFY COLUMN assessment_version INT UNSIGNED NOT NULL
    COMMENT '患者评估历史版本号；V1.0 与 V1.1 独立保留',
  MODIFY COLUMN question_schema_version VARCHAR(30) NOT NULL
    DEFAULT 'Q1-Q55-v1.1'
    COMMENT '评估问卷版本标识；当前正式版本为 Q1-Q55-v1.1',
  MODIFY COLUMN status ENUM('DRAFT','SUBMITTED','UNDER_REVIEW','COMPLETED','RETURNED')
    NOT NULL DEFAULT 'DRAFT'
    COMMENT '评估状态：草稿、已提交、审核中、已完成、已退回',
  MODIFY COLUMN source ENUM('PATIENT','CLINICIAN','MOCK')
    NOT NULL DEFAULT 'PATIENT'
    COMMENT '评估数据来源：患者填写、医护补录或原型Mock',
  MODIFY COLUMN answers_json JSON NOT NULL
    COMMENT 'Q5-Q55评估答案JSON；允许null、明确无、other_text，不自动补全缺失',
  MODIFY COLUMN data_completeness DECIMAL(5,2) NULL
    COMMENT '评估数据充分度百分比；缺失时为NULL，不用默认值代替',
  ALTER COLUMN question_schema_version SET DEFAULT 'Q1-Q55-v1.1';

-- ----------------------------------------------------------------------------
-- 二、评估逐题答案表 assessment_answer
-- ----------------------------------------------------------------------------
-- 一条记录对应一个 assessment_id 下的一道正式题目。
-- Q1-Q4 属于 patient 身份资料，因此这里的正式题号范围为 Q5-Q55。
-- value_json 用于保存单选、多选、复合题、化验、肝弹性及 other_text。
ALTER TABLE assessment_answer
  MODIFY COLUMN assessment_id BIGINT UNSIGNED NOT NULL
    COMMENT '所属评估记录ID，关联 assessment.assessment_id',
  MODIFY COLUMN patient_id VARCHAR(32) NOT NULL
    COMMENT '患者业务ID，关联 patient.patient_id',
  MODIFY COLUMN question_id TINYINT UNSIGNED NOT NULL
    COMMENT '正式评估题号 Q5-Q55；Q1-Q4 从 patient 读取，不重复存储',
  MODIFY COLUMN value_json JSON NULL
    COMMENT '题目答案JSON；未填写保留NULL，其他说明使用 other_text',
  MODIFY COLUMN source ENUM('PATIENT','CLINICIAN','MOCK')
    NOT NULL DEFAULT 'PATIENT'
    COMMENT '答案来源：患者填写、医护补录或原型Mock',
  DROP CHECK chk_answer_question,
  ADD CONSTRAINT chk_answer_question
    CHECK (question_id BETWEEN 5 AND 55);

-- ----------------------------------------------------------------------------
-- 三、字段与问卷映射说明（说明性注释，不新增数据库列）
-- ----------------------------------------------------------------------------
-- Q50 肝弹性成像建议在 answers_json 中保存：
--   { performed, checkDate, method, lsm, conclusion, fatQuantType, cap,
--     otherFatIndex }
-- “未做过”与 null/unknown 必须区分；部分缺失字段保持 null。
-- Q51 执行能力、Q52 饮食记录偏好、Q53 运动偏好、Q54 家属协助、Q55 健康目标。
-- Q27/Q45/Q50 为选填，后端不得因其缺失阻止整体评估或方案生成。

-- ----------------------------------------------------------------------------
-- 四、执行后检查建议
-- ----------------------------------------------------------------------------
-- 1. SHOW FULL COLUMNS FROM assessment;
-- 2. SHOW FULL COLUMNS FROM assessment_answer;
-- 3. SELECT question_schema_version, COUNT(*) FROM assessment
--      GROUP BY question_schema_version;
-- 4. 检查历史 Q1-Q54 记录的原版本号未被覆盖，新记录写入 Q1-Q55-v1.1。
