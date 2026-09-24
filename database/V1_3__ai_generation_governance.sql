-- AI generation authority and knowledge tables. No medical value is active
-- until the corresponding MDT record is marked ACTIVE by an accountable user.
CREATE TABLE IF NOT EXISTS mdt_config (
  config_id VARCHAR(64) PRIMARY KEY,
  domain ENUM('NUTRITION','FOOD','EXERCISE','PULMONARY','SAFETY') NOT NULL,
  display_name VARCHAR(255) NOT NULL,
  value_json JSON NULL,
  status ENUM('PENDING','ACTIVE','RETIRED') NOT NULL DEFAULT 'PENDING',
  source_version VARCHAR(80) NOT NULL,
  responsible_mdt VARCHAR(255) NOT NULL,
  approved_by BIGINT UNSIGNED NULL,
  approved_at DATETIME NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_mdt_config_approver FOREIGN KEY (approved_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS knowledge_item (
  knowledge_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  item_id VARCHAR(64) NOT NULL UNIQUE,
  item_type ENUM('FOOD','EXERCISE','PULMONARY','TEMPLATE') NOT NULL,
  display_name VARCHAR(255) NOT NULL,
  content_json JSON NOT NULL,
  status ENUM('DRAFT','ACTIVE','RETIRED') NOT NULL DEFAULT 'DRAFT',
  source_document VARCHAR(255) NOT NULL,
  source_version VARCHAR(80) NOT NULL,
  approved_by BIGINT UNSIGNED NULL,
  approved_at DATETIME NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_knowledge_type_status (item_type, status),
  CONSTRAINT fk_knowledge_approver FOREIGN KEY (approved_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS adaptive_rule (
  rule_id VARCHAR(64) PRIMARY KEY,
  trigger_json JSON NOT NULL,
  safety_level ENUM('GREEN','YELLOW','RED','REVIEW') NOT NULL,
  system_action JSON NOT NULL,
  reviewer_role VARCHAR(255) NOT NULL,
  adjustable_fields JSON NOT NULL,
  status ENUM('PENDING','ACTIVE','RETIRED') NOT NULL DEFAULT 'PENDING',
  source_version VARCHAR(80) NOT NULL,
  approved_by BIGINT UNSIGNED NULL,
  approved_at DATETIME NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_adaptive_approver FOREIGN KEY (approved_by) REFERENCES clinician_account(clinician_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
