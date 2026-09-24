-- MySQL 8.0 incremental migration from V1.0.
-- Adds monitoring alerts, multi-round consultation messages and business event history.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS monitoring_alert (
  alert_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NOT NULL,
  record_id BIGINT UNSIGNED NULL,
  alert_type VARCHAR(100) NOT NULL,
  latest_value VARCHAR(160) NULL,
  trend VARCHAR(80) NULL,
  safety_level ENUM('green','yellow','red') NOT NULL,
  status ENUM('PENDING','HANDLED','DISMISSED') NOT NULL DEFAULT 'PENDING',
  triggered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  handled_by BIGINT UNSIGNED NULL,
  handled_at DATETIME NULL,
  note TEXT NULL,
  INDEX idx_alert_queue (status, safety_level, triggered_at),
  INDEX idx_alert_patient (patient_id, triggered_at),
  CONSTRAINT fk_alert_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
  CONSTRAINT fk_alert_record FOREIGN KEY (record_id) REFERENCES patient_record(record_id),
  CONSTRAINT fk_alert_handler FOREIGN KEY (handled_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS consultation_message (
  message_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  consultation_id VARCHAR(40) NOT NULL,
  sender_type ENUM('PATIENT','CLINICIAN','SYSTEM') NOT NULL,
  sender_id VARCHAR(120) NULL,
  message_text TEXT NOT NULL,
  attachment_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_message_conversation (consultation_id, created_at),
  CONSTRAINT fk_message_consult FOREIGN KEY (consultation_id) REFERENCES consultation(consultation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS business_event (
  event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id VARCHAR(32) NULL,
  event_type ENUM('ASSESSMENT_SUBMITTED','ASSESSMENT_REVIEWED','PLAN_GENERATED','PLAN_REVIEWED','PLAN_PUBLISHED','PLAN_RETURNED','PLAN_PAUSED','RECORD_SUBMITTED','ALERT_TRIGGERED','CONSULTATION_CREATED','CONSULTATION_REPLIED','EDUCATION_PUBLISHED','OTHER') NOT NULL,
  object_type VARCHAR(60) NULL,
  object_id VARCHAR(80) NULL,
  actor_type ENUM('PATIENT','CLINICIAN','SYSTEM','AI') NOT NULL,
  actor_id VARCHAR(120) NULL,
  payload_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_event_patient_time (patient_id, created_at),
  INDEX idx_event_type_time (event_type, created_at),
  CONSTRAINT fk_event_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
