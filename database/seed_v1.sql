-- V1.0 demo seed; safe to run after schema.sql on an empty/demo database.
SET NAMES utf8mb4;
INSERT INTO clinician_account (clinician_id, username, display_name, role) VALUES
  (1, 'reviewer_demo', '审核医护', 'REVIEWER')
ON DUPLICATE KEY UPDATE display_name=VALUES(display_name);

INSERT INTO patient (patient_id, name, sex, birth_date, phone, account_status) VALUES
  ('P001','测试患者001','女','2000-01-01','00000000001','ACTIVE'),
  ('P002','测试患者002','男','2000-01-02','00000000002','ACTIVE'),
  ('P003','测试患者003','女','2000-01-03','00000000003','ACTIVE')
ON DUPLICATE KEY UPDATE name=VALUES(name), updated_at=CURRENT_TIMESTAMP;

INSERT INTO patient_profile (patient_id,a_f_phenotype,disease_risk,execution_ability,safety_level,surgery_window,current_summary,updated_by) VALUES
 ('P001','A2','代谢风险关注','良好','green','4–8周','营养与肺预康复并行管理',1),
 ('P002','B1','疾病风险关注','一般','yellow','2–4周','需补充评估资料并复核方案',1),
 ('P003','C3','重点关注','受限','red','2周以内','训练不适，需尽快人工跟进',1)
ON DUPLICATE KEY UPDATE updated_at=CURRENT_TIMESTAMP;

INSERT INTO assessment (assessment_id,patient_id,assessment_version,status,source,answers_json,data_completeness,submitted_at) VALUES
 (1001,'P001',1,'COMPLETED','MOCK',JSON_OBJECT('Q5','家人共同居住','Q6','4–8周','Q14',170,'Q15',70,'Q28','稳定','Q54',JSON_ARRAY('改善营养','提高运动能力')),0.82,NOW()),
 (1002,'P002',1,'UNDER_REVIEW','MOCK',JSON_OBJECT('Q5','家人共同居住','Q6','2–4周','Q14',168,'Q15',78),0.56,NOW()),
 (1003,'P003',1,'SUBMITTED','MOCK',JSON_OBJECT('Q5','独居','Q6','2周以内','Q14',160,'Q15',72),0.68,NOW())
ON DUPLICATE KEY UPDATE updated_at=CURRENT_TIMESTAMP;

INSERT INTO assessment_result (assessment_result_id,assessment_id,patient_id,result_version,a_f_phenotype,disease_risk,execution_ability,safety_level,primary_problems,mdt_confirmation_status,generated_at) VALUES
 (2001,1001,'P001',1,'A2','代谢风险关注','良好','green',JSON_ARRAY('体重管理','术前体能'), 'PENDING',NOW())
ON DUPLICATE KEY UPDATE created_at=created_at;

INSERT INTO goal (goal_id,patient_id,assessment_result_id,goal_version,stage,period_start,period_end,patient_expectation,target_json,status,approved_by,approved_at) VALUES
 (3001,'P001',2001,1,'术前营养与功能优化','2026-09-01','2026-09-28',JSON_ARRAY('改善营养','提高运动能力'),JSON_OBJECT('weeklyCompletionTarget',0.8),'ACTIVE',1,NOW())
ON DUPLICATE KEY UPDATE updated_at=CURRENT_TIMESTAMP;

INSERT INTO plan (plan_id,patient_id,goal_id,status,current_version_no,generated_by,published_at) VALUES
 (4001,'P001',3001,'PUBLISHED',1,'MOCK',NOW())
ON DUPLICATE KEY UPDATE updated_at=CURRENT_TIMESTAMP;
INSERT INTO plan_version (plan_version_id,plan_id,version_no,status,content_json,generated_by,published_at) VALUES
 (4101,4001,1,'PUBLISHED',JSON_OBJECT('goal','稳定体重并完成术前呼吸训练','diet','三餐规律，优先蛋白质与蔬菜','exercise','步行训练，每周3次','pulmonary','缩唇呼吸，每日2组'),'MOCK',NOW())
ON DUPLICATE KEY UPDATE status='PUBLISHED';
INSERT INTO plan_task (plan_task_id,plan_version_id,patient_id,task_type,task_name,instructions,planned_duration_min,planned_reps,planned_sets,unit,active) VALUES
 (4201,4101,'P001','DIET','三餐记录','按实际饮食完成记录',NULL,NULL,NULL,'次',1),
 (4202,4101,'P001','EXERCISE','步行训练','按舒适强度完成',20,NULL,NULL,'分钟',1),
 (4203,4101,'P001','PULMONARY','缩唇呼吸','缓慢呼气，配合腹式呼吸',NULL,10,2,'次/组',1)
ON DUPLICATE KEY UPDATE active=1;

INSERT INTO body_measurement_record (body_record_id,patient_id,record_date,weight_kg,body_fat_pct,waist_cm,source) VALUES
 (5001,'P001','2026-09-03',70.0,29.2,88.0,'MOCK'),(5002,'P001','2026-09-04',69.7,29.0,87.5,'MOCK')
ON DUPLICATE KEY UPDATE weight_kg=VALUES(weight_kg);

INSERT INTO consultation (consultation_id,patient_id,consultation_type,description,status,handling_status) VALUES
 ('C001','P001','方案问题','本周运动任务如何调整？','待回复','待处理'),
 ('C002','P003','指标变化','训练后出现轻微气促。','已回复','处理中')
ON DUPLICATE KEY UPDATE updated_at=CURRENT_TIMESTAMP;
INSERT INTO consultation_reply (consultation_id,clinician_id,reply_text) VALUES
 ('C002',1,'已收到，先暂停高强度训练并记录不适，我们会尽快复核。');

INSERT INTO education_content (education_id,title,category,content_type,duration_seconds,intro,status,published_by,published_at) VALUES
 (6001,'术前呼吸训练方法','肺预康复','VIDEO',180,'缩唇呼吸与腹式呼吸示范','PUBLISHED',1,NOW()),
 (6002,'肺结节患者饮食注意事项','饮食','VIDEO',240,'术前营养与饮食安排建议','PUBLISHED',1,NOW())
ON DUPLICATE KEY UPDATE status='PUBLISHED';
INSERT INTO notification (patient_id,notification_type,title,content) VALUES
 ('P001','PLAN','新方案已发布','您的术前营养与功能优化方案已由医护审核发布。'),
 ('P001','REMINDER','今日记录提醒','请完成今日体重与运动记录。');

INSERT INTO patient_clinician_relation (patient_id,clinician_id,relation_role) VALUES
 ('P001',1,'PRIMARY'),('P002',1,'PRIMARY'),('P003',1,'PRIMARY')
ON DUPLICATE KEY UPDATE active=1;
