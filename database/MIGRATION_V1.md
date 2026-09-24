# MySQL V1.0 migration notes

## Baseline

`schema.sql` is the MySQL 8.0 baseline. The former schema was preserved as `schema.sql.v0-backup-20260904` before replacement. Apply the baseline to a new or backed-up database, then run `seed_v1.sql` only in a demo environment.

```bash
mysql --default-character-set=utf8mb4 -u <user> -p <database> < database/schema.sql
mysql --default-character-set=utf8mb4 -u <user> -p <database> < database/seed_v1.sql
```

For production, use Flyway or Liquibase. Rename this baseline to `V1__baseline.sql` in the migration directory and never edit an applied migration. The first incremental patch is `V1_1__monitoring_messages_history.sql`, which adds `monitoring_alert`, `consultation_message` and `business_event`. Future changes are additive `V2__...sql` files, reviewed against the API contract and a backup. Before each release: snapshot the database, run migrations on staging, verify foreign keys/indexes, then promote.

## Shared data contract

Both web clients address the same `patient.patient_id`. Assessment history is append-only by `(patient_id, assessment_version)`; the V1.1 `answers_json` stores Q5-Q55 while Q1-Q4 are joined from `patient` and are not duplicated. Old Q1-Q54 snapshots remain historical through `question_schema_version`. Plan history is append-only by `(plan_id, version_no)`. The task chain is `plan_version (PUBLISHED) -> plan_task -> patient_record`, while body measurements stay in `body_measurement_record`. Consultation replies, education, notifications and audit entries are shared objects rather than per-client copies.

## Mock/TODO fields

The prototype still uses localStorage for current patient, task completion, alert handling, consultation overrides and trend points. The SQL columns are ready for API wiring, but object storage keys, authentication/authorization, device ingestion and notification delivery are TODO. `schedule_json`, `answers_json`, `content_json` and `metadata_json` are intentionally flexible until the backend DTOs are finalized.

## Clinical safety / MDT confirmation

No production threshold is encoded for A-F classification, disease risk, safety colors, abnormal vital signs, BORG, laboratory interpretation or plan adaptation. `assessment_result.mdt_confirmation_status` records whether a result has been confirmed. Rules and thresholds must be supplied and versioned by the clinical/MDT team before production activation; UI colors in the prototype are display states only.
