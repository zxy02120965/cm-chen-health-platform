-- MySQL 8.0 / V1.0 baseline for the shared patient + clinician system.
-- Q1-Q4 identity fields are owned by patient; assessment.answers_json stores health answers Q5-Q54 in the V1.0 baseline.
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS clinician_account (
  clinician_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  display_name VARCHAR(120) NOT NULL,
  role VARCHAR(40) NOT NULL DEFAULT 'REVIEWER',
  status ENUM('ACTIVE','DISABLED') NOT NULL DEFAULT 'ACTIVE',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS patient (
  patient_id VARCHAR(32) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  sex ENUM('男','女') NULL,
  birth_date DATE NULL,
  phone VARCHAR(32) NULL,
  avatar_url VARCHAR(500) NULL,
  account_status ENUM('ACTIVE','DISABLED') NOT NULL DEFAULT 'ACTIVE',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_patient_phone (phone),
  INDEX idx_patient_status (account_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS patient_profile (
  patient_id VARCHAR(32) PRIMARY KEY,
  a_f_phenotype VARCHAR(40) NULL,
  disease_risk VARCHAR(40) NULL,
  execution_ability VARCHAR(40) NULL,
  safety_level ENUM('green','yellow','red') NULL,
  surgery_window VARCHAR(40) NULL,
  primary_problems JSON NULL,
  management_priority JSON NULL,
  current_summary TEXT NULL,
  updated_by BIGINT UNSIGNED NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_profile_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_profile_clinician FOREIGN KEY (updated_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS assessment (
  assessment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NOT NULL,
  assessment_version INT UNSIGNED NOT NULL,
  question_schema_version VARCHAR(30) NOT NULL DEFAULT 'Q1-Q54-v1',
  status ENUM('DRAFT','SUBMITTED','UNDER_REVIEW','COMPLETED','RETURNED') NOT NULL DEFAULT 'DRAFT',
  source ENUM('PATIENT','CLINICIAN','MOCK') NOT NULL DEFAULT 'PATIENT',
  answers_json JSON NOT NULL COMMENT '健康评估答案；Q5-Q54键值，Q1-Q4通过patient关联',
  data_completeness DECIMAL(5,2) NULL,
  started_at DATETIME NULL,
  submitted_at DATETIME NULL,
  reviewed_by BIGINT UNSIGNED NULL,
  reviewed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_assessment_version (patient_id, assessment_version),
  INDEX idx_assessment_status (status),
  INDEX idx_assessment_patient_updated (patient_id, updated_at),
  CONSTRAINT fk_assessment_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_assessment_reviewer FOREIGN KEY (reviewed_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS assessment_answer (
  assessment_answer_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  assessment_id BIGINT UNSIGNED NOT NULL,
  patient_id VARCHAR(32) NOT NULL,
  question_id TINYINT UNSIGNED NOT NULL COMMENT '正式健康题号Q5-Q54；Q1-Q4从patient读取，不重复存储',
  value_json JSON NULL,
  source ENUM('PATIENT','CLINICIAN','MOCK') NOT NULL DEFAULT 'PATIENT',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_assessment_question (assessment_id, question_id),
  INDEX idx_answer_patient_question (patient_id, question_id),
  CONSTRAINT chk_answer_question CHECK (question_id BETWEEN 5 AND 54),
  CONSTRAINT fk_answer_assessment FOREIGN KEY (assessment_id) REFERENCES assessment(assessment_id),
  CONSTRAINT fk_answer_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS assessment_result (
  assessment_result_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  assessment_id BIGINT UNSIGNED NOT NULL,
  patient_id VARCHAR(32) NOT NULL,
  result_version INT UNSIGNED NOT NULL,
  a_f_phenotype VARCHAR(40) NULL,
  disease_risk VARCHAR(40) NULL,
  execution_ability VARCHAR(40) NULL,
  safety_level ENUM('green','yellow','red') NULL,
  primary_problems JSON NULL,
  limitations JSON NULL,
  preferences JSON NULL,
  surgery_window VARCHAR(40) NULL,
  goal_priority JSON NULL,
  mdt_confirmation_status ENUM('PENDING','CONFIRMED','NOT_APPLICABLE') NOT NULL DEFAULT 'PENDING',
  result_json JSON NULL,
  generated_at DATETIME NULL,
  reviewed_by BIGINT UNSIGNED NULL,
  reviewed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_result_version (patient_id, result_version),
  INDEX idx_result_patient (patient_id, created_at),
  CONSTRAINT fk_result_assessment FOREIGN KEY (assessment_id) REFERENCES assessment(assessment_id),
  CONSTRAINT fk_result_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_result_reviewer FOREIGN KEY (reviewed_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS goal (
  goal_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NOT NULL,
  assessment_result_id BIGINT UNSIGNED NULL,
  goal_version INT UNSIGNED NOT NULL DEFAULT 1,
  stage VARCHAR(80) NOT NULL,
  period_start DATE NULL,
  period_end DATE NULL,
  patient_expectation JSON NULL,
  target_json JSON NULL,
  status ENUM('DRAFT','ACTIVE','COMPLETED','PAUSED') NOT NULL DEFAULT 'DRAFT',
  approved_by BIGINT UNSIGNED NULL,
  approved_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_goal_version (patient_id, goal_version),
  INDEX idx_goal_patient_status (patient_id, status),
  CONSTRAINT fk_goal_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_goal_result FOREIGN KEY (assessment_result_id) REFERENCES assessment_result(assessment_result_id),
  CONSTRAINT fk_goal_approver FOREIGN KEY (approved_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS plan (
  plan_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NOT NULL,
  goal_id BIGINT UNSIGNED NULL,
  status ENUM('AI_GENERATED_PENDING_REVIEW','IN_REVIEW','APPROVED_PENDING_PUBLISH','PUBLISHED','RETURNED','PAUSED') NOT NULL DEFAULT 'AI_GENERATED_PENDING_REVIEW',
  current_version_no INT UNSIGNED NULL,
  generated_by ENUM('AI','CLINICIAN','MOCK') NOT NULL DEFAULT 'AI',
  published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_plan_patient_status (patient_id, status),
  CONSTRAINT fk_plan_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_plan_goal FOREIGN KEY (goal_id) REFERENCES goal(goal_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS plan_version (
  plan_version_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  plan_id BIGINT UNSIGNED NOT NULL,
  version_no INT UNSIGNED NOT NULL,
  status ENUM('AI_GENERATED_PENDING_REVIEW','IN_REVIEW','APPROVED_PENDING_PUBLISH','PUBLISHED','RETURNED','PAUSED') NOT NULL,
  content_json JSON NOT NULL,
  generated_by ENUM('AI','CLINICIAN','MOCK') NOT NULL DEFAULT 'AI',
  submitted_at DATETIME NULL,
  published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_plan_version (plan_id, version_no),
  INDEX idx_plan_version_status (status),
  CONSTRAINT fk_plan_version_plan FOREIGN KEY (plan_id) REFERENCES plan(plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS plan_review (
  review_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  plan_id BIGINT UNSIGNED NOT NULL,
  plan_version_id BIGINT UNSIGNED NOT NULL,
  reviewer_clinician_id BIGINT UNSIGNED NOT NULL,
  action ENUM('SUBMIT','START_REVIEW','APPROVE','RETURN','PUBLISH','PAUSE') NOT NULL,
  comment TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_review_plan_version (plan_version_id, created_at),
  CONSTRAINT fk_review_plan FOREIGN KEY (plan_id) REFERENCES plan(plan_id),
  CONSTRAINT fk_review_version FOREIGN KEY (plan_version_id) REFERENCES plan_version(plan_version_id),
  CONSTRAINT fk_review_clinician FOREIGN KEY (reviewer_clinician_id) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS plan_task (
  plan_task_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  plan_version_id BIGINT UNSIGNED NOT NULL,
  patient_id VARCHAR(32) NOT NULL,
  task_type ENUM('DIET','EXERCISE','PULMONARY','MONITOR','OTHER') NOT NULL,
  task_name VARCHAR(160) NOT NULL,
  instructions TEXT NULL,
  schedule_json JSON NULL,
  planned_duration_min DECIMAL(8,2) NULL,
  planned_reps DECIMAL(8,2) NULL,
  planned_sets DECIMAL(8,2) NULL,
  planned_times DECIMAL(8,2) NULL,
  unit VARCHAR(30) NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_task_patient_active (patient_id, active),
  INDEX idx_task_plan_version (plan_version_id),
  CONSTRAINT fk_task_version FOREIGN KEY (plan_version_id) REFERENCES plan_version(plan_version_id),
  CONSTRAINT fk_task_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS patient_record (
  record_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NOT NULL,
  plan_task_id BIGINT UNSIGNED NULL,
  record_date DATE NOT NULL,
  record_type ENUM('DIET','EXERCISE','PULMONARY','VITAL','OTHER') NOT NULL,
  actual_duration_min DECIMAL(8,2) NULL,
  actual_reps DECIMAL(8,2) NULL,
  actual_sets DECIMAL(8,2) NULL,
  actual_times DECIMAL(8,2) NULL,
  intensity VARCHAR(40) NULL,
  discomfort ENUM('NONE','MILD','MODERATE','SEVERE') NULL,
  note TEXT NULL,
  metadata_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_record_patient_date (patient_id, record_date),
  INDEX idx_record_task_date (plan_task_id, record_date),
  CONSTRAINT fk_record_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_record_task FOREIGN KEY (plan_task_id) REFERENCES plan_task(plan_task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS body_measurement_record (
  body_record_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NOT NULL,
  record_date DATE NOT NULL,
  weight_kg DECIMAL(6,2) NULL,
  body_fat_pct DECIMAL(5,2) NULL,
  waist_cm DECIMAL(6,2) NULL,
  heart_rate DECIMAL(6,2) NULL,
  systolic_bp DECIMAL(6,2) NULL,
  diastolic_bp DECIMAL(6,2) NULL,
  spo2_pct DECIMAL(5,2) NULL,
  source ENUM('PATIENT','CLINICIAN','DEVICE','MOCK') NOT NULL DEFAULT 'PATIENT',
  note TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_body_patient_date (patient_id, record_date),
  CONSTRAINT fk_body_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS consultation (
  consultation_id VARCHAR(40) PRIMARY KEY,
  patient_id VARCHAR(32) NOT NULL,
  consultation_type ENUM('饮食','运动','肺预康复','指标变化','方案问题','其他') NOT NULL,
  description TEXT NOT NULL,
  status ENUM('待回复','已回复','已完成') NOT NULL DEFAULT '待回复',
  handling_status ENUM('待处理','处理中','已完成') NOT NULL DEFAULT '待处理',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_consult_patient_status (patient_id, status),
  INDEX idx_consult_handling (handling_status, updated_at),
  CONSTRAINT fk_consult_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS consultation_reply (
  reply_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  consultation_id VARCHAR(40) NOT NULL,
  clinician_id BIGINT UNSIGNED NOT NULL,
  reply_text TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_reply_consult (consultation_id, created_at),
  CONSTRAINT fk_reply_consult FOREIGN KEY (consultation_id) REFERENCES consultation(consultation_id),
  CONSTRAINT fk_reply_clinician FOREIGN KEY (clinician_id) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS education_content (
  education_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  category ENUM('饮食','运动','肺预康复','术前准备','代谢健康','常见问题','术后恢复') NOT NULL,
  content_type ENUM('VIDEO','ARTICLE') NOT NULL DEFAULT 'VIDEO',
  duration_seconds INT UNSIGNED NULL,
  intro TEXT NULL,
  video_url VARCHAR(500) NULL,
  qr_code_url VARCHAR(500) NULL,
  body_text MEDIUMTEXT NULL,
  status ENUM('DRAFT','PUBLISHED','OFFLINE') NOT NULL DEFAULT 'DRAFT',
  published_by BIGINT UNSIGNED NULL,
  published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_education_category_status (category, status),
  CONSTRAINT fk_education_publisher FOREIGN KEY (published_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notification (
  notification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NULL,
  notification_type ENUM('ASSESSMENT','PLAN','CONSULT','REMINDER','ALERT','EDUCATION','OTHER') NOT NULL,
  title VARCHAR(200) NOT NULL,
  content TEXT NOT NULL,
  read_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_notification_patient_created (patient_id, created_at),
  CONSTRAINT fk_notification_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS document (
  document_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NOT NULL,
  document_type ENUM('CT','PATHOLOGY','LAB','OTHER') NOT NULL,
  exam_date DATE NULL,
  file_name VARCHAR(255) NOT NULL,
  object_key VARCHAR(500) NULL,
  upload_status ENUM('UPLOADING','UPLOADED','FAILED','DELETED') NOT NULL DEFAULT 'UPLOADING',
  note TEXT NULL,
  uploaded_by_type ENUM('PATIENT','CLINICIAN') NOT NULL DEFAULT 'PATIENT',
  uploaded_by BIGINT UNSIGNED NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_document_patient_type (patient_id, document_type),
  CONSTRAINT fk_document_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_document_clinician FOREIGN KEY (uploaded_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS patient_clinician_relation (
  patient_id VARCHAR(32) NOT NULL,
  clinician_id BIGINT UNSIGNED NOT NULL,
  relation_role ENUM('PRIMARY','REVIEWER','ASSISTANT') NOT NULL DEFAULT 'REVIEWER',
  active TINYINT(1) NOT NULL DEFAULT 1,
  assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  unassigned_at DATETIME NULL,
  PRIMARY KEY (patient_id, clinician_id),
  INDEX idx_relation_clinician_active (clinician_id, active),
  CONSTRAINT fk_relation_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_relation_clinician FOREIGN KEY (clinician_id) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_log (
  audit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  actor_type ENUM('PATIENT','CLINICIAN','SYSTEM','AI') NOT NULL,
  actor_id VARCHAR(120) NULL,
  patient_id VARCHAR(32) NULL,
  object_type VARCHAR(60) NOT NULL,
  object_id VARCHAR(80) NULL,
  action VARCHAR(80) NOT NULL,
  before_json JSON NULL,
  after_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_patient_time (patient_id, created_at),
  INDEX idx_audit_object (object_type, object_id),
  CONSTRAINT fk_audit_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
