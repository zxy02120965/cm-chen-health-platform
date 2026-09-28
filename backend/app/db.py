from __future__ import annotations

"""SQLAlchemy persistence for the MySQL V1.0/V1.1 schema.

When DB_HOST is omitted the API keeps the existing SQLite development fallback.
For MySQL, DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD are used to build the
connection URL safely (including passwords containing ``@``).
"""

import os
from datetime import date, datetime
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, URL, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from .ai_governance import ADAPTIVE_RULES, PENDING_CONFIGS

# Allow local development with a project-root .env while keeping secrets out of
# source control. Docker Compose injects the same variables directly.
load_dotenv()


def _database_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    host = os.getenv("DB_HOST")
    if not host:
        return "sqlite:///./cm_chen_dev.db"

    # Accept both the API-oriented DB_* names and the MYSQL_* names used by
    # the Compose/.env template, so direct uvicorn startup and Compose behave
    # identically.
    username = os.getenv("DB_USER") or os.getenv("MYSQL_USER") or "zxy"
    password = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD") or ""
    database = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or "ai_zxy"
    return URL.create(
        "mysql+pymysql",
        username=username,
        password=password,
        host=host,
        port=int(os.getenv("DB_PORT", "3306")),
        database=database,
    ).render_as_string(hide_password=False)


DATABASE_URL = _database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
pool_args = {"poolclass": StaticPool} if DATABASE_URL == "sqlite:///:memory:" else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args, **pool_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ClinicianAccountRow(Base):
    __tablename__ = "clinician_account"
    clinician_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(40), default="REVIEWER")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PatientRow(Base):
    __tablename__ = "patient"
    patient_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sex: Mapped[str | None] = mapped_column(String(8), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    account_status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PatientProfileRow(Base):
    __tablename__ = "patient_profile"
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), primary_key=True)
    a_f_phenotype: Mapped[str | None] = mapped_column(String(40), nullable=True)
    disease_risk: Mapped[str | None] = mapped_column(String(40), nullable=True)
    execution_ability: Mapped[str | None] = mapped_column(String(40), nullable=True)
    safety_level: Mapped[str | None] = mapped_column(String(12), nullable=True)
    surgery_window: Mapped[str | None] = mapped_column(String(40), nullable=True)
    primary_problems: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    management_priority: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    current_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AssessmentRow(Base):
    __tablename__ = "assessment"
    assessment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    assessment_version: Mapped[int] = mapped_column(Integer)
    question_schema_version: Mapped[str] = mapped_column(String(30), default="Q1-Q56-v1.2")
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    source: Mapped[str] = mapped_column(String(16), default="PATIENT")
    answers_json: Mapped[Any] = mapped_column(JSON, default=dict)
    data_completeness: Mapped[float | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AssessmentResultRow(Base):
    __tablename__ = "assessment_result"
    assessment_result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessment.assessment_id"))
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    result_version: Mapped[int] = mapped_column(Integer)
    a_f_phenotype: Mapped[str | None] = mapped_column(String(40), nullable=True)
    disease_risk: Mapped[str | None] = mapped_column(String(40), nullable=True)
    execution_ability: Mapped[str | None] = mapped_column(String(40), nullable=True)
    safety_level: Mapped[str | None] = mapped_column(String(12), nullable=True)
    primary_problems: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    limitations: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    preferences: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    surgery_window: Mapped[str | None] = mapped_column(String(40), nullable=True)
    goal_priority: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    mdt_confirmation_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    result_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GoalRow(Base):
    __tablename__ = "goal"
    goal_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    assessment_result_id: Mapped[int | None] = mapped_column(ForeignKey("assessment_result.assessment_result_id"), nullable=True)
    goal_version: Mapped[int] = mapped_column(Integer, default=1)
    stage: Mapped[str] = mapped_column(String(80))
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    patient_expectation: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    target_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanRow(Base):
    __tablename__ = "plan"
    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goal.goal_id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="AI_GENERATED_PENDING_REVIEW")
    current_version_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(16), default="AI")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlanVersionRow(Base):
    __tablename__ = "plan_version"
    plan_version_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.plan_id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40))
    content_json: Mapped[Any] = mapped_column(JSON, default=dict)
    generated_by: Mapped[str] = mapped_column(String(16), default="AI")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlanReviewRow(Base):
    __tablename__ = "plan_review"
    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plan.plan_id"), index=True)
    plan_version_id: Mapped[int] = mapped_column(ForeignKey("plan_version.plan_version_id"))
    reviewer_clinician_id: Mapped[int] = mapped_column(ForeignKey("clinician_account.clinician_id"))
    action: Mapped[str] = mapped_column(String(20))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlanTaskRow(Base):
    __tablename__ = "plan_task"
    plan_task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_version_id: Mapped[int] = mapped_column(ForeignKey("plan_version.plan_version_id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    task_type: Mapped[str] = mapped_column(String(20))
    task_name: Mapped[str] = mapped_column(String(160))
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    planned_duration_min: Mapped[float | None] = mapped_column(nullable=True)
    planned_reps: Mapped[float | None] = mapped_column(nullable=True)
    planned_sets: Mapped[float | None] = mapped_column(nullable=True)
    planned_times: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PatientRecordRow(Base):
    __tablename__ = "patient_record"
    record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    plan_task_id: Mapped[int | None] = mapped_column(ForeignKey("plan_task.plan_task_id"), nullable=True)
    record_date: Mapped[date] = mapped_column(Date)
    record_type: Mapped[str] = mapped_column(String(20))
    actual_duration_min: Mapped[float | None] = mapped_column(nullable=True)
    actual_reps: Mapped[float | None] = mapped_column(nullable=True)
    actual_sets: Mapped[float | None] = mapped_column(nullable=True)
    actual_times: Mapped[float | None] = mapped_column(nullable=True)
    intensity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    discomfort: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BodyMeasurementRecordRow(Base):
    __tablename__ = "body_measurement_record"
    body_record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    record_date: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(nullable=True)
    heart_rate: Mapped[float | None] = mapped_column(nullable=True)
    systolic_bp: Mapped[float | None] = mapped_column(nullable=True)
    diastolic_bp: Mapped[float | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="PATIENT")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConsultationRow(Base):
    __tablename__ = "consultation"
    consultation_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    consultation_type: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="待回复")
    handling_status: Mapped[str] = mapped_column(String(16), default="待处理")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConsultationReplyRow(Base):
    __tablename__ = "consultation_reply"
    reply_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultation.consultation_id"), index=True)
    clinician_id: Mapped[int] = mapped_column(ForeignKey("clinician_account.clinician_id"))
    reply_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConsultationMessageRow(Base):
    __tablename__ = "consultation_message"
    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consultation_id: Mapped[str] = mapped_column(ForeignKey("consultation.consultation_id"), index=True)
    sender_type: Mapped[str] = mapped_column(String(16))
    sender_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message_text: Mapped[str] = mapped_column(Text)
    attachment_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EducationContentRow(Base):
    __tablename__ = "education_content"
    education_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20))
    content_type: Mapped[str] = mapped_column(String(16), default="VIDEO")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intro: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    qr_code_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    published_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MonitoringAlertRow(Base):
    __tablename__ = "monitoring_alert"
    alert_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patient.patient_id"), index=True)
    record_id: Mapped[int | None] = mapped_column(ForeignKey("patient_record.record_id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(100))
    latest_value: Mapped[str | None] = mapped_column(String(160), nullable=True)
    trend: Mapped[str | None] = mapped_column(String(80), nullable=True)
    safety_level: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class BusinessEventRow(Base):
    __tablename__ = "business_event"
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str | None] = mapped_column(ForeignKey("patient.patient_id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    object_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    object_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payload_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MdtConfigRow(Base):
    __tablename__ = "mdt_config"
    config_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(20))
    display_name: Mapped[str] = mapped_column(String(255))
    value_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    source_version: Mapped[str] = mapped_column(String(80), default="V1.0")
    responsible_mdt: Mapped[str] = mapped_column(String(255))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeItemRow(Base):
    __tablename__ = "knowledge_item"
    knowledge_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    item_type: Mapped[str] = mapped_column(String(20), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    content_json: Mapped[Any] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    source_document: Mapped[str] = mapped_column(String(255))
    source_version: Mapped[str] = mapped_column(String(80), default="V1.0")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdaptiveRuleRow(Base):
    __tablename__ = "adaptive_rule"
    rule_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trigger_json: Mapped[Any] = mapped_column(JSON, default=dict)
    safety_level: Mapped[str] = mapped_column(String(16))
    system_action: Mapped[Any] = mapped_column(JSON, default=dict)
    reviewer_role: Mapped[str] = mapped_column(String(255))
    adjustable_fields: Mapped[Any] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    source_version: Mapped[str] = mapped_column(String(80), default="V1.0")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("clinician_account.clinician_id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db() -> bool:
    try:
        Base.metadata.create_all(engine)
        with SessionLocal() as session:
            if session.get(ClinicianAccountRow, 1) is None:
                session.add(ClinicianAccountRow(clinician_id=1, username="reviewer_demo", display_name="审核医护", role="REVIEWER", status="ACTIVE"))
            # Synthetic development/demo seed data only; never use real patient identity data here.
            demo_patients = [
                PatientRow(patient_id="P001", name="测试患者001", sex="女", birth_date=date(2000, 1, 1), phone="00000000001"),
                PatientRow(patient_id="P002", name="测试患者002", sex="男", birth_date=date(2000, 1, 2), phone="00000000002"),
                PatientRow(patient_id="P003", name="测试患者003", sex="女", birth_date=date(2000, 1, 3), phone="00000000003"),
            ]
            for row in demo_patients:
                if session.get(PatientRow, row.patient_id) is None:
                    session.add(row)
            for config_id, domain, display_name, responsible_mdt in PENDING_CONFIGS:
                if session.get(MdtConfigRow, config_id) is None:
                    session.add(MdtConfigRow(config_id=config_id, domain=domain, display_name=display_name,
                        responsible_mdt=responsible_mdt, status="PENDING", source_version="V1.0"))
            for rule_id, trigger, safety_level, freeze, reviewer_role, fields, outcome in ADAPTIVE_RULES:
                if session.get(AdaptiveRuleRow, rule_id) is None:
                    session.add(AdaptiveRuleRow(rule_id=rule_id, trigger_json={"description": trigger},
                        safety_level=safety_level, system_action={"freeze": freeze, "outcome": outcome},
                        reviewer_role=reviewer_role, adjustable_fields=fields, status="PENDING", source_version="V1.0"))
            session.commit()
        return True
    except Exception:
        return False


def _latest_assessment(session: Session, patient_id: str) -> AssessmentRow | None:
    return session.scalars(select(AssessmentRow).where(AssessmentRow.patient_id == patient_id).order_by(AssessmentRow.assessment_version.desc(), AssessmentRow.assessment_id.desc())).first()


def read_current_assessment_snapshot(patient_id: str) -> dict[str, Any] | None:
    """Read the current assessment and its persisted evaluation snapshot.

    Historical assessments may have been evaluated by an older rule release.
    For API presentation we therefore prefer the result snapshot linked to
    the current assessment instead of silently recalculating it with today's
    rules.  New submissions still produce that snapshot through the unified
    ``assess_payload`` -> ``calculate_phenotype`` path.
    """
    try:
        with SessionLocal() as session:
            assessment = _latest_assessment(session, patient_id)
            if not assessment:
                return None
            result = session.scalars(
                select(AssessmentResultRow)
                .where(AssessmentResultRow.assessment_id == assessment.assessment_id)
                .order_by(AssessmentResultRow.result_version.desc(), AssessmentResultRow.assessment_result_id.desc())
            ).first()
            evaluation = None
            if result:
                evaluation = dict(result.result_json or {})
                # Snapshot columns are authoritative when present; retain the
                # JSON details (missing/uncertain/Q50 etc.) alongside them.
                evaluation.update({
                    "phenotype_code": result.a_f_phenotype or evaluation.get("phenotype_code"),
                    "phenotype": evaluation.get("phenotype") or result.a_f_phenotype,
                    "disease_risk": result.disease_risk,
                    "execution_ability": result.execution_ability or "unknown",
                    "safety": result.safety_level or evaluation.get("safety"),
                    "surgery_window": result.surgery_window,
                    "goal_priority": result.goal_priority,
                })
            return {
                "assessment_id": assessment.assessment_id,
                "assessment_version": assessment.assessment_version,
                "question_schema_version": assessment.question_schema_version,
                "status": assessment.status,
                "answers": assessment.answers_json or {},
                "evaluation": evaluation,
            }
    except Exception:
        return None


def _latest_plan(session: Session, patient_id: str) -> tuple[PlanRow | None, PlanVersionRow | None]:
    plan = session.scalars(select(PlanRow).where(PlanRow.patient_id == patient_id).order_by(PlanRow.updated_at.desc(), PlanRow.plan_id.desc())).first()
    if not plan:
        return None, None
    version = session.scalars(select(PlanVersionRow).where(PlanVersionRow.plan_id == plan.plan_id).order_by(PlanVersionRow.version_no.desc(), PlanVersionRow.plan_version_id.desc())).first()
    return plan, version


def _latest_published_plan_version(session: Session, patient_id: str) -> tuple[PlanRow | None, PlanVersionRow | None]:
    """Return the newest published snapshot without relying on ``plan.status``.

    ``plan.status`` describes the current workflow state and can legitimately
    be ``IN_REVIEW`` while the previous published version remains the active
    patient-facing plan.  Patient reads must therefore select the version by
    its own immutable publication status.
    """
    plan = session.scalars(
        select(PlanRow)
        .where(PlanRow.patient_id == patient_id)
        .order_by(PlanRow.updated_at.desc(), PlanRow.plan_id.desc())
    ).first()
    if not plan:
        return None, None
    version = session.scalars(
        select(PlanVersionRow)
        .where(PlanVersionRow.plan_id == plan.plan_id, PlanVersionRow.status == "PUBLISHED")
        .order_by(
            PlanVersionRow.version_no.desc(),
            PlanVersionRow.published_at.desc(),
            PlanVersionRow.plan_version_id.desc(),
        )
    ).first()
    return plan, version


def read_published_plan(patient_id: str) -> dict[str, Any] | None:
    """Return only the newest published version for patient-facing reads.

    In-memory API state can outlive a newer RDS version (for example after a
    clinician publishes from another tab).  This query is intentionally fresh
    on every request and never falls back to a draft or an old published row.
    """
    try:
        with SessionLocal() as session:
            plan, version = _latest_published_plan_version(session, patient_id)
            if not plan or not version:
                return None
            payload = dict(version.content_json or {})
            payload.update({
                "plan_id": plan.plan_id,
                "plan_version_id": version.plan_version_id,
                "patient_id": patient_id,
                "version": version.version_no,
                "status": "PUBLISHED",
                "published_at": version.published_at.isoformat() if version.published_at else (plan.published_at.isoformat() if plan.published_at else None),
            })
            return payload
    except Exception:
        return None


def sync_patient_profile(session: Session, patient_id: str, payload: dict[str, Any], evaluation: dict[str, Any]) -> PatientProfileRow:
    """Persist only deterministic assessment output in the profile snapshot.

    The current schema has JSON columns for the result details, so missing and
    uncertain data are kept as structured values instead of being coerced into
    a clinical risk level.  Disease risk and execution ability remain null when
    the rules do not determine them.
    """
    profile = session.get(PatientProfileRow, patient_id)
    if profile is None:
        profile = PatientProfileRow(patient_id=patient_id)
        session.add(profile)
    phenotype = evaluation.get("phenotype_code") or evaluation.get("phenotype")
    liver_modifier = evaluation.get("liver_modifier")
    liver_review = bool(evaluation.get("need_clinician_review"))
    barriers = evaluation.get("execution_barriers") or payload.get("q51_executionBarriers") or []
    execution = "red" if len(barriers) >= 4 else "yellow" if len(barriers) >= 2 else "green" if barriers == [] else "unknown"
    phenotype_modifiers = {
        "surgery_window": payload.get("q6_surgeryWindow"),
        "liver_metabolic_risk": liver_modifier,
        "liver_fibrosis_risk": liver_modifier if liver_modifier and liver_modifier != "未评估" else None,
        "nutrition_risk": "营养风险关注" if phenotype and str(phenotype).startswith("D") else None,
        "muscle_protection": True if phenotype and str(phenotype).startswith("D") or liver_review else None,
    }
    profile.a_f_phenotype = phenotype
    # No confirmed disease-specific risk rule exists in the current engine.
    profile.disease_risk = None
    # Likewise, do not infer a traffic-light execution ability from one answer.
    profile.execution_ability = execution
    profile.safety_level = evaluation.get("safety")
    profile.surgery_window = payload.get("q6_surgeryWindow")
    profile.primary_problems = {
        "phenotype_modifiers": phenotype_modifiers,
        "disease_risk": None,
        "missing_data": evaluation.get("missing_data", []),
        "uncertain_items": evaluation.get("uncertain_items", []),
        "explicit_none": evaluation.get("explicit_none", []),
        "need_clinician_review": bool(evaluation.get("need_clinician_review")),
        "enhanced_eligible": evaluation.get("enhanced_eligible"),
        "enhanced_ineligible_reasons": evaluation.get("enhanced_ineligible_reasons", []),
        "goal_conflict": evaluation.get("goal_conflict", False),
        "publication_blocked": evaluation.get("publication_blocked", False),
        "manual_review_required": evaluation.get("manual_review_required", bool(evaluation.get("need_clinician_review"))),
    }
    profile.management_priority = {
        "execution_ability": execution,
        "safety_level": evaluation.get("safety"),
        "priority": ["安全", "营养充分", "肌肉保护"],
    }
    profile.current_summary = evaluation.get("safety_label") or evaluation.get("tier_label")
    return profile


def read_patient_profile(patient_id: str) -> dict[str, Any] | None:
    """Read the persisted clinical profile snapshot without mixing account data."""
    try:
        with SessionLocal() as session:
            row = session.get(PatientProfileRow, patient_id)
            if not row:
                return None
            return {
                "patient_id": row.patient_id,
                "a_f_phenotype": row.a_f_phenotype,
                "disease_risk": row.disease_risk,
                "execution_ability": row.execution_ability,
                "safety_level": row.safety_level,
                "surgery_window": row.surgery_window,
                "primary_problems": row.primary_problems,
                "management_priority": row.management_priority,
                "current_summary": row.current_summary,
                "updated_by": row.updated_by,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
    except Exception:
        return None


def _task_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def materialize_plan_tasks(session: Session, patient_id: str, plan_row: PlanRow, version: PlanVersionRow) -> list[PlanTaskRow]:
    """Create idempotent execution tasks from one published plan version.

    Only fields explicitly present in the published JSON are copied.  No dose,
    frequency, threshold, or medical instruction is invented here.
    """
    existing = session.scalars(select(PlanTaskRow).where(PlanTaskRow.plan_version_id == version.plan_version_id)).all()
    if existing:
        return existing
    content = dict(version.content_json or {})
    specs: list[tuple[str, str, str, Any]] = []
    # Structured Plan Content Contract (v1.0) is the preferred source.  Every
    # field is copied verbatim into schedule_json; scalar dose columns remain
    # NULL when the published content did not contain an explicit number.
    structured = False
    diet_plan = content.get("diet_plan")
    if isinstance(diet_plan, dict):
        structured = True
        meal_found = False
        for meal_key, label in (("breakfast", "早餐"), ("lunch", "午餐"), ("snack", "加餐"), ("dinner", "晚餐")):
            meal = diet_plan.get(meal_key)
            if not isinstance(meal, dict):
                continue
            meal_found = True
            specs.append(("DIET", str(meal.get("dish_name") or f"{label}（待医护补充）"), f"diet_plan.{meal_key}", meal))
        if not meal_found:
            specs.append(("DIET", "饮食计划（待医护补充餐次）", "diet_plan", diet_plan))
    exercise_plan = content.get("exercise_plan")
    if isinstance(exercise_plan, list):
        structured = True
        for index, item in enumerate(exercise_plan):
            if isinstance(item, dict):
                specs.append(("EXERCISE", str(item.get("exercise_name") or "运动项目（待医护确认）"), f"exercise_plan[{index}]", item))
    pulmonary_plan = content.get("pulmonary_prehab_plan")
    if isinstance(pulmonary_plan, list):
        structured = True
        for index, item in enumerate(pulmonary_plan):
            if isinstance(item, dict):
                specs.append(("PULMONARY_PREHAB", str(item.get("action_name") or "肺预康复项目（待医护确认）"), f"pulmonary_prehab_plan[{index}]", item))

    explicit_tasks = content.get("tasks")
    if not structured and isinstance(explicit_tasks, list):
        for item in explicit_tasks:
            if not isinstance(item, dict):
                continue
            task_type = str(item.get("task_type") or item.get("type") or "OTHER").upper()
            if task_type not in {"DIET", "EXERCISE", "PULMONARY_PREHAB"}:
                continue
            specs.append((task_type, str(item.get("task_name") or item.get("name") or task_type), "task", item))
    elif not structured:
        # Current rules produce section text, not doses. Preserve that text and
        # leave planned values null until a clinician publishes structured data.
        for task_type, key, name in (
            ("DIET", "diet", "饮食任务"),
            ("EXERCISE", "exercise", "运动任务"),
            ("PULMONARY_PREHAB", "pulmonary_prehab", "肺预康复任务"),
        ):
            if content.get(key) not in (None, ""):
                specs.append((task_type, name, key, content[key]))
    created: list[PlanTaskRow] = []
    for task_type, name, source_key, source in specs:
        raw = source if isinstance(source, dict) else {}
        instructions = raw.get("brief_instructions") or raw.get("instructions") or (source if isinstance(source, str) else None)
        task = PlanTaskRow(
            plan_version_id=version.plan_version_id,
            patient_id=patient_id,
            task_type=task_type,
            task_name=name,
            instructions=instructions,
            schedule_json={"source_key": source_key, "published_content": source},
            planned_duration_min=_task_number(raw.get("duration") or raw.get("duration_min")),
            planned_reps=_task_number(raw.get("repetitions") or raw.get("reps")),
            planned_sets=_task_number(raw.get("sets")),
            planned_times=_task_number(raw.get("times") or raw.get("daily_frequency")),
            unit=raw.get("unit"),
            active=True,
        )
        session.add(task)
        created.append(task)
    return created


def read_patient_data(patient_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        with SessionLocal() as session:
            assessment = _latest_assessment(session, patient_id)
            plan, version = _latest_plan(session, patient_id)
            plan_payload = None
            if plan:
                plan_payload = dict(version.content_json or {}) if version else {}
                plan_payload.update({"plan_id": plan.plan_id, "plan_version_id": version.plan_version_id if version else None, "patient_id": patient_id, "version": version.version_no if version else plan.current_version_no, "status": plan.status, "published_at": plan.published_at.isoformat() if plan.published_at else None})
            return (assessment.answers_json if assessment else None, plan_payload)
    except Exception:
        return None, None


def write_assessment(patient_id: str, payload: dict[str, Any], evaluation: dict[str, Any], status: str = "SUBMITTED", source: str = "PATIENT") -> dict[str, Any] | None:
    try:
        with SessionLocal() as session:
            previous = _latest_assessment(session, patient_id)
            version = (previous.assessment_version + 1) if previous else 1
            now = datetime.utcnow()
            row = AssessmentRow(patient_id=patient_id, assessment_version=version, question_schema_version="Q1-Q56-v1.2", status=status, source=source, answers_json=payload, data_completeness=(evaluation.get("score", 0) / 100), submitted_at=now if status in {"SUBMITTED", "UNDER_REVIEW", "COMPLETED"} else None, updated_at=now)
            session.add(row)
            session.flush()
            session.add(AssessmentResultRow(assessment_id=row.assessment_id, patient_id=patient_id, result_version=version, a_f_phenotype=evaluation.get("phenotype_code") or evaluation.get("phenotype"), execution_ability=evaluation.get("execution_ability") or "unknown", safety_level=evaluation.get("safety"), result_json=evaluation, generated_at=now))
            sync_patient_profile(session, patient_id, payload, evaluation)
            session.add(BusinessEventRow(patient_id=patient_id, event_type="ASSESSMENT_SUBMITTED", object_type="assessment", object_id=str(row.assessment_id), actor_type=source, actor_id=patient_id))
            session.commit()
            return {"assessment_id": row.assessment_id, "assessment_version": version}
    except Exception:
        return None


def write_plan(patient_id: str, plan: dict[str, Any]) -> dict[str, Any] | None:
    try:
        with SessionLocal() as session:
            current = session.scalars(select(PlanRow).where(PlanRow.patient_id == patient_id).order_by(PlanRow.plan_id.desc())).first()
            if current:
                plan_row = current
                version_no = (plan_row.current_version_no or 0) + 1
            else:
                plan_row = PlanRow(patient_id=patient_id, status=plan.get("status", "AI_GENERATED_PENDING_REVIEW"), generated_by=(plan.get("draft", {}).get("generator_type") or plan.get("generation_source") or "RULE_BASED"))
                session.add(plan_row)
                session.flush()
                version_no = 1
            plan_row.status = plan.get("status", "AI_GENERATED_PENDING_REVIEW")
            plan_row.current_version_no = version_no
            content = plan.get("draft", plan)
            version = PlanVersionRow(plan_id=plan_row.plan_id, version_no=version_no, status=plan_row.status, generated_by=(content.get("generator_type") or plan.get("generation_source") or "RULE_BASED"), content_json=content)
            session.add(version)
            session.flush()
            session.add(BusinessEventRow(patient_id=patient_id, event_type="PLAN_GENERATED", object_type="plan", object_id=str(plan_row.plan_id), actor_type="AI", actor_id="rules"))
            session.commit()
            return {"plan_id": plan_row.plan_id, "plan_version_id": version.plan_version_id, "version": version_no}
    except Exception:
        return None


def update_plan(patient_id: str, plan: dict[str, Any], action: str | None = None, reviewer_id: int = 1) -> dict[str, Any] | None:
    try:
        with SessionLocal() as session:
            plan_row, version = _latest_plan(session, patient_id)
            if not plan_row or not version:
                return False
            status = plan.get("status", plan_row.status)
            plan_row.status = status
            version.status = status
            # Lifecycle actions update the immutable version snapshot as well
            # as its workflow column.  Without this, a restart reloads the
            # original generated content and loses review/gate state.
            content = dict(plan.get("draft") or plan)
            content["status"] = status
            if plan.get("reviewer") is not None:
                content["reviewer"] = plan.get("reviewer")
            if plan.get("review_note") is not None:
                content["review_note"] = plan.get("review_note")
            if plan.get("reviewed_at") is not None:
                content["reviewed_at"] = plan.get("reviewed_at")
            version.content_json = content
            if status == "PUBLISHED":
                plan_row.published_at = datetime.utcnow()
                version.published_at = plan_row.published_at
            review_action = action or {"PUBLISHED": "PUBLISH", "RETURNED": "RETURN", "IN_REVIEW": "START_REVIEW"}.get(status, "APPROVE")
            session.add(PlanReviewRow(plan_id=plan_row.plan_id, plan_version_id=version.plan_version_id, reviewer_clinician_id=reviewer_id, action=review_action, comment=plan.get("review_note")))
            event_type = {"PUBLISHED": "PLAN_PUBLISHED", "RETURNED": "PLAN_RETURNED", "PAUSED": "PLAN_PAUSED"}.get(status, "PLAN_REVIEWED")
            session.add(BusinessEventRow(patient_id=patient_id, event_type=event_type, object_type="plan", object_id=str(plan_row.plan_id), actor_type="CLINICIAN", actor_id=str(reviewer_id), payload_json={"status": status, "comment": plan.get("review_note")}))
            if status == "PUBLISHED":
                materialize_plan_tasks(session, patient_id, plan_row, version)
            session.commit()
            return {"plan_id": plan_row.plan_id, "plan_version_id": version.plan_version_id, "version": version.version_no, "status": status, "published_at": plan_row.published_at}
    except Exception:
        return None
