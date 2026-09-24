-- MySQL V1.2 incremental migration for Assessment Questionnaire V1.1 (Q1-Q55).
-- Do not run automatically against the RDS in this review round.
-- Existing assessment rows are preserved; assessment_version remains the
-- numeric history revision and question_schema_version identifies the form.

ALTER TABLE assessment
  ALTER COLUMN question_schema_version SET DEFAULT 'Q1-Q55-v1.1';

ALTER TABLE assessment_answer
  DROP CHECK chk_answer_question,
  ADD CONSTRAINT chk_answer_question CHECK (question_id BETWEEN 5 AND 55);

-- Q1-Q4 remain in patient and are not duplicated in assessment_answer.
-- Q50-Q55 are stored in assessment.answers_json/value_json, including null,
-- explicit "无", and other_text values without defaulting missing data.
