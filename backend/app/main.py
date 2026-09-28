from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text

from .db import (
    AssessmentRow,
    AssessmentResultRow,
    BodyMeasurementRecordRow,
    BusinessEventRow,
    ClinicianAccountRow,
    ConsultationMessageRow,
    ConsultationReplyRow,
    ConsultationRow,
    EducationContentRow,
    PatientRecordRow,
    PatientRow,
    PlanRow,
    PlanTaskRow,
    SessionLocal,
    MonitoringAlertRow,
    MdtConfigRow,
    KnowledgeItemRow,
    AdaptiveRuleRow,
    engine,
    _latest_assessment,
    _latest_plan,
    _latest_published_plan_version,
    init_db,
    read_patient_data,
    read_current_assessment_snapshot,
    read_published_plan,
    read_patient_profile,
    update_plan,
    write_assessment,
    write_plan,
)
from .ai_governance import build_generation_context, evaluate_adjustment, validate_draft
from .rules import assess_payload, generate_plan_draft
from .v2_engine import weekly_review, candidate_test_profile

app = FastAPI(title="CM Chen Health Management API", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

PATIENTS: dict[str, dict[str, Any]] = {
    "P001": {"id": "P001", "patient_id": "P001", "name": "张女士", "alias": "张女士", "sex": "女", "birth_date": "1968-05-12", "age_band": "55–64岁", "stage": "术前管理第9天"},
    "P002": {"id": "P002", "patient_id": "P002", "name": "李先生", "alias": "李先生", "sex": "男", "birth_date": "1975-09-03", "age_band": "45–54岁", "stage": "围术期机能优化"},
    "P003": {"id": "P003", "patient_id": "P003", "name": "王女士", "alias": "王女士", "sex": "女", "birth_date": "1962-11-20", "age_band": "55–64岁", "stage": "术前复评"},
}
ASSESSMENTS: dict[str, dict[str, Any]] = {}
PLANS: dict[str, dict[str, Any]] = {}


class AssessmentIn(BaseModel):
    """Accepts Q1-Q56 V1.2 answers plus legacy flat fields during API transition."""
    model_config = ConfigDict(extra="allow")
    answers: dict[str, Any] = Field(default_factory=dict)
    status: Literal["DRAFT", "SUBMITTED", "UNDER_REVIEW", "COMPLETED", "RETURNED"] = "SUBMITTED"


class ReviewIn(BaseModel):
    action: Literal["start_review", "approve", "publish", "return", "pause"]
    note: str = ""
    reviewer: str = "统一医护账号"
    reviewer_id: int = 1


class PlanUpdateIn(BaseModel):
    draft: dict[str, Any]
    status: Literal["AI_GENERATED_PENDING_REVIEW", "RULE_GENERATED_PENDING_REVIEW", "IN_REVIEW", "APPROVED_PENDING_PUBLISH", "APPROVED_PENDING_MDT_ACTIVATION", "READY_TO_PUBLISH", "PUBLISHED", "RETURNED", "PAUSED"] | None = None


class AssessmentReviewIn(BaseModel):
    action: Literal["approve", "return"]
    reviewer_id: int = 1
    note: str = ""
    q56_goal: dict[str, Any] | None = None


class RecordIn(BaseModel):
    record_date: date = Field(default_factory=date.today)
    record_type: Literal["DIET", "EXERCISE", "PULMONARY", "VITAL", "DAILY_SYMPTOM", "OTHER"]
    plan_task_id: int | None = None
    actual_duration_min: float | None = Field(default=None, ge=0)
    actual_reps: float | None = Field(default=None, ge=0)
    actual_sets: float | None = Field(default=None, ge=0)
    actual_times: float | None = Field(default=None, ge=0)
    intensity: str | None = None
    discomfort: Literal["NONE", "MILD", "MODERATE", "SEVERE"] | None = None
    note: str | None = None
    metadata_json: dict[str, Any] | None = None


class BodyMeasurementIn(BaseModel):
    record_date: date = Field(default_factory=date.today)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    body_fat_pct: float | None = Field(default=None, ge=1, le=80)
    waist_cm: float | None = Field(default=None, ge=30, le=250)
    heart_rate: float | None = Field(default=None, ge=20, le=250)
    systolic_bp: float | None = Field(default=None, ge=40, le=300)
    diastolic_bp: float | None = Field(default=None, ge=20, le=200)
    note: str | None = None


class ConsultationIn(BaseModel):
    consultation_id: str | None = None
    consultation_type: str
    description: str = Field(min_length=1)


class MessageIn(BaseModel):
    sender_type: Literal["PATIENT", "CLINICIAN", "SYSTEM"]
    sender_id: str | None = None
    message_text: str = Field(min_length=1)
    attachment_json: dict[str, Any] | None = None


class EducationPublishIn(BaseModel):
    published_by: int = 1


class PatientProfileIn(BaseModel):
    name: str | None = None
    sex: Literal["男", "女"] | None = None
    birth_date: date | None = None
    phone: str | None = None
    avatar_url: str | None = None


class MdtConfigUpdateIn(BaseModel):
    value_json: dict[str, Any] = Field(default_factory=dict)
    status: Literal["PENDING", "ACTIVE", "RETIRED"] = "PENDING"
    reviewer_id: int = 1


class KnowledgeItemIn(BaseModel):
    item_id: str = Field(min_length=2, max_length=64)
    item_type: Literal["FOOD", "EXERCISE", "PULMONARY", "TEMPLATE"]
    display_name: str = Field(min_length=1, max_length=255)
    content_json: dict[str, Any]
    source_document: str = Field(min_length=1, max_length=255)
    source_version: str = "V1.0"
    status: Literal["DRAFT", "ACTIVE", "RETIRED"] = "DRAFT"
    reviewer_id: int = 1


class AdjustmentPreviewIn(BaseModel):
    signals: dict[str, bool] = Field(default_factory=dict)


class AdaptiveRuleUpdateIn(BaseModel):
    status: Literal["PENDING", "ACTIVE", "RETIRED"]
    reviewer_id: int = 1


def _governance_context(session: Any) -> dict[str, Any]:
    configs = [{"config_id": x.config_id, "domain": x.domain, "display_name": x.display_name,
                "value_json": x.value_json, "status": x.status, "source_version": x.source_version}
               for x in session.scalars(select(MdtConfigRow)).all()]
    knowledge = [{"item_id": x.item_id, "item_type": x.item_type, "display_name": x.display_name,
                  "content_json": x.content_json, "status": x.status, "source_version": x.source_version}
                 for x in session.scalars(select(KnowledgeItemRow)).all()]
    rules = [{"rule_id": x.rule_id, "trigger": x.trigger_json, "safety_level": x.safety_level,
              "action": x.system_action, "reviewer_role": x.reviewer_role,
              "adjustable_fields": x.adjustable_fields, "status": x.status}
             for x in session.scalars(select(AdaptiveRuleRow)).all()]
    return build_generation_context(configs=configs, knowledge=knowledge, rules=rules)


def _patient_or_404(patient_id: str) -> dict[str, Any]:
    # Database is authoritative whenever it is reachable; the in-memory
    # dictionary is only a development fallback for an unavailable database.
    try:
        with SessionLocal() as session:
            row = session.get(PatientRow, patient_id)
            if row:
                return {"id": row.patient_id, "patient_id": row.patient_id, "name": row.name, "alias": row.name, "sex": row.sex, "birth_date": row.birth_date.isoformat() if row.birth_date else None, "phone": row.phone}
    except Exception:
        pass
    if patient_id in PATIENTS:
        return PATIENTS[patient_id]
    raise HTTPException(404, "患者不存在")


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    """Report API health and verify the configured database connection."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE", "ai_zxy"), "database_status": "ok"}
    except Exception:
        # Do not leak connection strings or credentials in the health response.
        return {"status": "degraded", "database": os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE", "ai_zxy"), "database_status": "unavailable"}


@app.get("/api/ai-governance/context")
def get_ai_governance_context() -> dict[str, Any]:
    """Read-only AI gateway context; the prompt itself is never authoritative."""
    try:
        with SessionLocal() as session:
            return _governance_context(session)
    except Exception as exc:
        raise HTTPException(503, f"治理配置暂不可用: {exc}") from exc


@app.get("/api/ai-governance/configs")
def list_mdt_configs(domain: str | None = None) -> list[dict[str, Any]]:
    try:
        with SessionLocal() as session:
            stmt = select(MdtConfigRow).order_by(MdtConfigRow.config_id)
            if domain:
                stmt = stmt.where(MdtConfigRow.domain == domain.upper())
            return [{"config_id": x.config_id, "domain": x.domain, "display_name": x.display_name,
                     "value_json": x.value_json, "status": x.status, "source_version": x.source_version,
                     "responsible_mdt": x.responsible_mdt, "approved_by": x.approved_by,
                     "approved_at": _iso(x.approved_at)} for x in session.scalars(stmt).all()]
    except Exception as exc:
        raise HTTPException(503, f"MDT配置暂不可用: {exc}") from exc


@app.put("/api/ai-governance/configs/{config_id}")
def update_mdt_config(config_id: str, body: MdtConfigUpdateIn) -> dict[str, Any]:
    try:
        with SessionLocal() as session:
            row = session.get(MdtConfigRow, config_id)
            if not row:
                raise HTTPException(404, "配置不存在")
            row.value_json, row.status = body.value_json, body.status
            row.approved_by = body.reviewer_id if body.status == "ACTIVE" else None
            row.approved_at = datetime.utcnow() if body.status == "ACTIVE" else None
            session.add(BusinessEventRow(event_type="MDT_CONFIG_UPDATED", object_type="mdt_config", object_id=config_id,
                actor_type="CLINICIAN", actor_id=str(body.reviewer_id), payload_json={"status": body.status}))
            session.commit()
            return {"config_id": config_id, "status": row.status, "approved_at": _iso(row.approved_at)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"MDT配置未能保存: {exc}") from exc


@app.get("/api/ai-governance/knowledge")
def list_knowledge(item_type: str | None = None, active_only: bool = False) -> list[dict[str, Any]]:
    try:
        with SessionLocal() as session:
            stmt = select(KnowledgeItemRow).order_by(KnowledgeItemRow.item_type, KnowledgeItemRow.item_id)
            if item_type:
                stmt = stmt.where(KnowledgeItemRow.item_type == item_type.upper())
            if active_only:
                stmt = stmt.where(KnowledgeItemRow.status == "ACTIVE")
            return [{"item_id": x.item_id, "item_type": x.item_type, "display_name": x.display_name,
                     "content_json": x.content_json, "status": x.status, "source_document": x.source_document,
                     "source_version": x.source_version, "approved_at": _iso(x.approved_at)}
                    for x in session.scalars(stmt).all()]
    except Exception as exc:
        raise HTTPException(503, f"知识库暂不可用: {exc}") from exc


@app.put("/api/ai-governance/knowledge/{item_id}")
def upsert_knowledge(item_id: str, body: KnowledgeItemIn) -> dict[str, Any]:
    if item_id != body.item_id:
        raise HTTPException(400, "路径与项目ID不一致")
    try:
        with SessionLocal() as session:
            row = session.scalars(select(KnowledgeItemRow).where(KnowledgeItemRow.item_id == item_id)).first()
            if row is None:
                row = KnowledgeItemRow(item_id=item_id, item_type=body.item_type, display_name=body.display_name,
                    content_json=body.content_json, source_document=body.source_document, source_version=body.source_version)
                session.add(row)
            else:
                row.item_type, row.display_name, row.content_json = body.item_type, body.display_name, body.content_json
                row.source_document, row.source_version = body.source_document, body.source_version
            row.status = body.status
            row.approved_by = body.reviewer_id if body.status == "ACTIVE" else None
            row.approved_at = datetime.utcnow() if body.status == "ACTIVE" else None
            session.add(BusinessEventRow(event_type="KNOWLEDGE_ITEM_UPDATED", object_type="knowledge_item", object_id=item_id,
                actor_type="CLINICIAN", actor_id=str(body.reviewer_id), payload_json={"status": body.status, "item_type": body.item_type}))
            session.commit()
            return {"item_id": item_id, "status": row.status, "approved_at": _iso(row.approved_at)}
    except Exception as exc:
        raise HTTPException(503, f"知识库项目未能保存: {exc}") from exc


@app.post("/api/patients/{patient_id}/adjustment-preview")
def preview_adjustment(patient_id: str, body: AdjustmentPreviewIn) -> dict[str, Any]:
    """Return a reviewable adjustment decision; it never edits a plan itself."""
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            context = _governance_context(session)
        matches = evaluate_adjustment(body.signals, context["adaptive_rules"])
        return {"patient_id": patient_id, "matches": matches,
                "decision": "AI_GENERATED_PENDING_REVIEW" if matches else "MAINTAIN_CURRENT_PUBLISHED_PLAN",
                "new_plan_version_created": False,
                "note": "仅当相关自适应规则已由MDT启用，且医护审核后，才可生成新版本。"}
    except Exception as exc:
        raise HTTPException(503, f"动态调整规则暂不可用: {exc}") from exc


@app.put("/api/ai-governance/adaptive-rules/{rule_id}")
def update_adaptive_rule(rule_id: str, body: AdaptiveRuleUpdateIn) -> dict[str, Any]:
    try:
        with SessionLocal() as session:
            row = session.get(AdaptiveRuleRow, rule_id)
            if not row:
                raise HTTPException(404, "动态调整规则不存在")
            row.status = body.status
            row.approved_by = body.reviewer_id if body.status == "ACTIVE" else None
            row.approved_at = datetime.utcnow() if body.status == "ACTIVE" else None
            session.add(BusinessEventRow(event_type="ADAPTIVE_RULE_UPDATED", object_type="adaptive_rule", object_id=rule_id,
                actor_type="CLINICIAN", actor_id=str(body.reviewer_id), payload_json={"status": body.status}))
            session.commit()
            return {"rule_id": rule_id, "status": row.status, "approved_at": _iso(row.approved_at)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"动态调整规则未能保存: {exc}") from exc


@app.get("/api/patients")
def list_patients() -> list[dict[str, Any]]:
    try:
        with SessionLocal() as session:
            rows = session.scalars(select(PatientRow).order_by(PatientRow.patient_id)).all()
            if rows:
                return [{"id": r.patient_id, "patient_id": r.patient_id, "name": r.name, "alias": r.name, "sex": r.sex, "birth_date": _iso(r.birth_date), "phone": r.phone, "account_status": r.account_status} for r in rows]
    except Exception:
        pass
    return list(PATIENTS.values())


@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: str) -> dict[str, Any]:
    patient = _patient_or_404(patient_id)
    snapshot = read_current_assessment_snapshot(patient_id)
    payload = (snapshot or {}).get("answers") or ASSESSMENTS.get(patient_id, {})
    # A persisted result is the canonical view for an existing assessment
    # (including legacy Q1-Q55 history).  Only assessments without a result
    # are evaluated through the shared rule entry point.
    evaluation = (snapshot or {}).get("evaluation") or assess_payload({**payload, "profile_sex": patient.get("sex")})
    # The patient summary must never expose a draft or an old cached version.
    assessment_meta = None
    if snapshot:
        assessment_meta = {
            "assessment_id": snapshot["assessment_id"],
            "assessment_version": snapshot["assessment_version"],
            "question_schema_version": snapshot["question_schema_version"],
            "status": snapshot["status"],
        }
    return {**patient, "assessment": payload, "assessment_meta": assessment_meta, "evaluation": evaluation, "patient_profile": read_patient_profile(patient_id), "plan": read_published_plan(patient_id)}


@app.get("/api/patients/{patient_id}/profile")
def get_patient_profile(patient_id: str) -> dict[str, Any]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            row = session.get(PatientRow, patient_id)
            if not row:
                raise HTTPException(404, "患者不存在")
            return {"patient_id": row.patient_id, "name": row.name, "sex": row.sex, "birth_date": _iso(row.birth_date), "phone": row.phone, "avatar_url": row.avatar_url, "health_profile": read_patient_profile(patient_id)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.put("/api/patients/{patient_id}/profile")
def update_patient_profile(patient_id: str, body: PatientProfileIn) -> dict[str, Any]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            row = session.get(PatientRow, patient_id)
            if not row:
                raise HTTPException(404, "患者不存在")
            for key, value in body.model_dump(exclude_none=True).items():
                setattr(row, key, value)
            session.commit()
            return {"patient_id": row.patient_id, "name": row.name, "sex": row.sex, "birth_date": _iso(row.birth_date), "phone": row.phone, "avatar_url": row.avatar_url}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/patients/{patient_id}/assessment")
def get_assessment(patient_id: str) -> dict[str, Any]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            rows = session.scalars(select(AssessmentRow).where(AssessmentRow.patient_id == patient_id).order_by(AssessmentRow.assessment_version.desc())).all()
            current = rows[0] if rows else None
            return {"patient_id": patient_id, "questionnaire_version": current.question_schema_version if current else None, "current": ({"assessment_id": current.assessment_id, "version": current.assessment_version, "question_schema_version": current.question_schema_version, "status": current.status, "answers": current.answers_json} if current else None), "history": [{"assessment_id": r.assessment_id, "version": r.assessment_version, "question_schema_version": r.question_schema_version, "status": r.status, "updated_at": _iso(r.updated_at)} for r in rows]}
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/patients/{patient_id}/assessment/result")
def get_assessment_result(patient_id: str) -> dict[str, Any]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            assessment = _latest_assessment(session, patient_id)
            if not assessment:
                raise HTTPException(404, "暂无评估结果")
            result = session.scalars(select(AssessmentResultRow).where(AssessmentResultRow.assessment_id == assessment.assessment_id).order_by(AssessmentResultRow.result_version.desc())).first()
            if result:
                payload = dict(result.result_json or {})
                payload.update({"patient_id": patient_id, "assessment_id": assessment.assessment_id, "version": result.result_version, "questionnaire_version": assessment.question_schema_version, "question_schema_version": assessment.question_schema_version, "status": assessment.status, "mdt_confirmation_status": result.mdt_confirmation_status, "phenotype": result.a_f_phenotype or payload.get("phenotype"), "disease_risk": result.disease_risk, "execution_ability": result.execution_ability or "unknown", "safety": result.safety_level or payload.get("safety"), "primary_problems": result.primary_problems, "limitations": result.limitations, "preferences": result.preferences, "surgery_window": result.surgery_window, "goal_priority": result.goal_priority})
                return payload
            return {"patient_id": patient_id, "assessment_id": assessment.assessment_id, "version": assessment.assessment_version, "questionnaire_version": assessment.question_schema_version, "question_schema_version": assessment.question_schema_version, "status": assessment.status, **assess_payload(assessment.answers_json or {})}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.put("/api/patients/{patient_id}/assessment")
def save_assessment(patient_id: str, body: AssessmentIn) -> dict[str, Any]:
    patient = _patient_or_404(patient_id)
    raw = body.model_dump(exclude_none=True)
    status = raw.pop("status", "SUBMITTED")
    incoming_answers = {**raw.pop("answers", {}), **raw}
    existing_answers = read_patient_data(patient_id)[0] or {}
    answers = {**existing_answers, **incoming_answers}
    ASSESSMENTS[patient_id] = answers
    # Identity remains owned by patient; rules receive a transient profile
    # value for evaluation but it is not duplicated in answers_json.
    evaluation = assess_payload({**answers, "profile_sex": patient.get("sex")})
    persisted = write_assessment(patient_id, answers, evaluation, status=status)
    if not persisted:
        raise HTTPException(503, "评估未能写入数据库")
    if patient_id in PLANS:
        PLANS[patient_id]["status"] = "RETURNED"
    return {"patient_id": patient_id, "assessment_id": persisted["assessment_id"], "assessment_version": persisted["assessment_version"], "assessment": answers, "evaluation": evaluation, "status": status, "patient": patient}


@app.post("/api/patients/{patient_id}/assessment/review")
def review_assessment(patient_id: str, body: AssessmentReviewIn) -> dict[str, Any]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            row = _latest_assessment(session, patient_id)
            if not row:
                raise HTTPException(404, "暂无评估记录")
            now = datetime.utcnow()
            # A clinician Q56 edit is an immutable new assessment snapshot;
            # the patient's submitted version remains available in history.
            if body.q56_goal is not None:
                answers = dict(row.answers_json or {})
                answers["q56_goal"] = body.q56_goal
                evaluation = assess_payload({**answers, "profile_sex": (_patient_or_404(patient_id).get("sex"))})
                new_row = AssessmentRow(patient_id=patient_id, assessment_version=row.assessment_version + 1,
                    question_schema_version="Q1-Q56-v1.2", status="COMPLETED" if body.action == "approve" else "RETURNED",
                    source="CLINICIAN", answers_json=answers, data_completeness=row.data_completeness,
                    submitted_at=now, reviewed_by=body.reviewer_id, reviewed_at=now, updated_at=now)
                session.add(new_row)
                session.flush()
                session.add(AssessmentResultRow(assessment_id=new_row.assessment_id, patient_id=patient_id,
                    result_version=new_row.assessment_version, a_f_phenotype=evaluation.get("phenotype_code") or evaluation.get("phenotype"),
                    execution_ability=evaluation.get("execution_ability") or "unknown", safety_level=evaluation.get("safety"),
                    result_json=evaluation, generated_at=now, reviewed_by=body.reviewer_id, reviewed_at=now))
                from .db import sync_patient_profile
                sync_patient_profile(session, patient_id, answers, evaluation)
                session.add(BusinessEventRow(patient_id=patient_id, event_type="ASSESSMENT_Q56_UPDATED", object_type="assessment", object_id=str(new_row.assessment_id), actor_type="CLINICIAN", actor_id=str(body.reviewer_id), payload_json={"previous_assessment_id": row.assessment_id, "note": body.note}))
                session.commit()
                return {"patient_id": patient_id, "assessment_id": new_row.assessment_id, "previous_assessment_id": row.assessment_id, "status": new_row.status, "assessment_version": new_row.assessment_version, "q56_goal": body.q56_goal, "reviewed_at": now.isoformat()}
            row.status = "COMPLETED" if body.action == "approve" else "RETURNED"
            row.reviewed_by, row.reviewed_at = body.reviewer_id, now
            result = session.scalars(select(AssessmentResultRow).where(AssessmentResultRow.assessment_id == row.assessment_id).order_by(AssessmentResultRow.result_version.desc())).first()
            if result:
                result.reviewed_by, result.reviewed_at = body.reviewer_id, now
            session.add(BusinessEventRow(patient_id=patient_id, event_type="ASSESSMENT_REVIEWED", object_type="assessment", object_id=str(row.assessment_id), actor_type="CLINICIAN", actor_id=str(body.reviewer_id), payload_json={"action": body.action, "note": body.note}))
            session.commit()
            return {"patient_id": patient_id, "assessment_id": row.assessment_id, "status": row.status, "reviewed_at": now.isoformat()}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.post("/api/patients/{patient_id}/plans/draft")
def create_plan(patient_id: str) -> dict[str, Any]:
    patient = _patient_or_404(patient_id)
    payload = ASSESSMENTS.get(patient_id, read_patient_data(patient_id)[0] or {})
    evaluation = assess_payload({**payload, "profile_sex": patient.get("sex")})
    with SessionLocal() as session:
        context = _governance_context(session)
    active_values = {x["config_id"]: {**(x.get("value_json") or {}), "status": x.get("status"), "source_version": x.get("source_version")} for x in context["active_mdt_configs"]}
    # PENDING governance may still have reviewed candidate values.  Merge only
    # the explicit TEST/CANDIDATE profile so clinicians receive a complete
    # clinician-only draft. Candidate metadata is retained for audit, but the
    # current project V2/V3 baseline is not blocked at the patient level.
    candidate = candidate_test_profile()
    for key, value in candidate.items():
        if key == "environment" or not isinstance(value, dict):
            continue
        # Candidate values fill governance-pending configs for the clinician
        # draft. Existing ACTIVE values always win; no production config is
        # promoted and the candidate source remains visible in the draft.
        existing = active_values.get(key) or {}
        # FOOD selection is an explicit source cutover: the new generation
        # path must use the manifest-backed V1.4 metadata even if an older
        # governance row still contains the legacy V1.7-shaped catalog.
        if key in {"FOOD_SELECTION_METADATA", "V2-FOOD-COMPONENTS"}:
            active_values[key] = {**value, "status": value.get("status", "ACTIVE"), "environment": "TEST_ONLY"}
            continue
        existing_payload = {k: v for k, v in existing.items() if k not in {"status", "source_version", "environment"}}
        existing_has_values = any(v not in (None, "", [], {}) for v in existing_payload.values())
        if existing.get("status") == "ACTIVE" and existing_has_values:
            continue
        active_values[key] = {**existing, **value, "status": "CANDIDATE", "environment": "CANDIDATE_MDT"}
    active_knowledge = context.get("approved_knowledge", [])
    for cfg_id, item_type, key in (("V2-FOOD-COMPONENTS", "FOOD", "component_id"), ("V2-EXERCISE-ACTIONS", "EXERCISE", "exercise_id"), ("V2-PULMONARY-ACTIONS", "PULMONARY", "pulmonary_id")):
        # FOOD selection is now a manifest-backed V1.4 asset merged with the
        # V1.3 execution truth by candidate_test_profile().  Do not let older
        # approved-knowledge rows (including the unregistered V1.7 workbook)
        # overwrite that source for new plan generation.
        if item_type == "FOOD":
            continue
        entries = [x.get("content_json", {}) for x in active_knowledge if x.get("item_type") == item_type and x.get("content_json", {}).get(key)]
        ids = [x.get(key) for x in entries]
        if ids:
            active_values.setdefault(cfg_id, {}).update({"status": "ACTIVE", "ids": ids, "items": entries})
    # The account birth date is identity data, not duplicated in assessment;
    # pass it transiently to the energy calculator when age is needed.
    generation_payload = {**payload, "birth_date": patient.get("birth_date")}
    draft = generate_plan_draft(patient, generation_payload, evaluation, active_configs=active_values)
    draft["generation_authority"] = {"authority_order": context["authority_order"],
        "pending_mdt_config_ids": context["pending_mdt_config_ids"], "prompt_role": context["prompt_role"]}
    draft["safety_validation_errors"] = validate_draft(draft, context["active_mdt_configs"])
    previous_version = int((PLANS.get(patient_id) or {}).get("version", 0))
    plan = {"patient_id": patient_id, "version": previous_version + 1, "status": "RULE_GENERATED_PENDING_REVIEW", "evaluation": evaluation, "draft": draft, "created_at": datetime.now(timezone.utc).isoformat()}
    from .plan_view import build_plan_view
    draft["plan_view"] = build_plan_view({**draft, "patient_id": patient_id, "status": plan["status"]})
    PLANS[patient_id] = plan
    persisted = write_plan(patient_id, plan)
    if not persisted:
        raise HTTPException(503, "方案草稿未能写入数据库")
    plan.update(persisted)
    PLANS[patient_id] = plan
    return plan


@app.get("/api/patients/{patient_id}/plan")
def get_plan(patient_id: str, include_unpublished: bool = Query(default=False)) -> dict[str, Any]:
    _patient_or_404(patient_id)
    # Patient-facing reads always query the newest published RDS version.  The
    # clinician detail view may explicitly request the current draft/review
    # version for its approval workflow.
    plan = read_published_plan(patient_id) if not include_unpublished else (PLANS.get(patient_id) or read_patient_data(patient_id)[1])
    if not plan:
        raise HTTPException(404, "当前暂无方案")
    return plan


@app.put("/api/patients/{patient_id}/plan")
def save_plan_draft(patient_id: str, body: PlanUpdateIn) -> dict[str, Any]:
    """Persist clinician edits as a new immutable plan version."""
    _patient_or_404(patient_id)
    plan = PLANS.get(patient_id) or read_patient_data(patient_id)[1]
    if not plan:
        raise HTTPException(404, "请先生成方案草稿")
    with SessionLocal() as session:
        context = _governance_context(session)
    errors = validate_draft(body.draft, context["active_mdt_configs"])
    if body.status == "PUBLISHED" and errors:
        raise HTTPException(422, {"message": "安全校验未通过，不能发布", "errors": errors})
    draft = {**body.draft, "safety_validation_errors": errors}
    updated = {**plan, "patient_id": patient_id, "draft": draft, "status": body.status or plan.get("status", "IN_REVIEW")}
    from .plan_view import build_plan_view
    draft["plan_view"] = build_plan_view({**draft, "patient_id": patient_id, "status": updated["status"]})
    PLANS[patient_id] = updated
    persisted = write_plan(patient_id, updated)
    if not persisted:
        raise HTTPException(503, "方案修改未能写入数据库")
    updated.update(persisted)
    PLANS[patient_id] = updated
    return updated


def _hard_publication_blockers(draft: dict[str, Any], validation: dict[str, Any]) -> list[str]:
    """Return only blockers that clinician approval must not bypass.

    Candidate/provisional energy provenance is review-resolvable: approval
    records that a clinician accepted the current version without rewriting
    the underlying energy status.  Explicit safety/content/execution failures
    remain hard blockers and continue to protect publication.
    """
    blockers: list[str] = []
    content_checks = (
        ("content_validation", "方案内容校验未通过"),
        ("nutrition_plan_validation", "营养方案校验未通过"),
        ("exercise_validation", "运动方案校验未通过"),
        ("pulmonary_validation", "肺预康复方案校验未通过"),
        ("safety_validation", "安全校验阻止发布"),
    )
    for key, message in content_checks:
        value = validation.get(key)
        if value not in (None, "PASS"):
            blockers.append(message)
    if str(draft.get("safety_level") or "").lower() == "red":
        blockers.append("安全等级为红色，必须暂停并升级处理")

    reasons = list(validation.get("publish_block_reasons") or [])
    energy_state = ((draft.get("energy_state") or {}).get("energy_target") or {}).get("status")
    for reason in reasons:
        text = str(reason)
        # This is the existing engine reason for provisional/candidate energy.
        # It is resolved by whole-plan clinician approval, while UNAVAILABLE
        # remains a true execution/publication blocker.
        if "能量状态为PROVISIONAL/UNAVAILABLE" in text and energy_state != "UNAVAILABLE":
            continue
        blockers.append(text)
    nested_gate_blocked = bool((draft.get("safety_rules") or {}).get("publication_blocked"))
    if (draft.get("publication_blocked") or nested_gate_blocked) and not reasons:
        blockers.append("方案标记为禁止发布")
    if validation.get("publish_validation") == "BLOCKED" and not reasons and not blockers:
        blockers.append("发布校验未通过")
    return list(dict.fromkeys(blockers))


def _derive_effective_publication_gate(
    draft: dict[str, Any],
    validation: dict[str, Any],
    *,
    clinician_review_status: str | None = None,
) -> dict[str, Any]:
    """Derive one publication gate for review, persistence, and publishing.

    Provisional/candidate energy review is resolved by an explicit clinician
    approval, while hard content/safety/execution failures remain blocking.
    The result also exposes the review-resolvable reasons for audit without
    changing their underlying clinical status.
    """
    hard_blockers = _hard_publication_blockers(draft, validation)
    reasons = [str(reason) for reason in (validation.get("publish_block_reasons") or [])]
    review_resolvable = [reason for reason in reasons if reason not in hard_blockers]
    approved = clinician_review_status == "APPROVED"
    remaining = list(hard_blockers)
    if not approved:
        remaining.extend(review_resolvable)
    return {
        "publication_blocked": bool(remaining),
        "hard_blockers": list(dict.fromkeys(hard_blockers)),
        "review_resolvable_blockers": list(dict.fromkeys(review_resolvable)),
        "remaining_blockers": list(dict.fromkeys(remaining)),
        "ready_to_publish": bool(approved and not hard_blockers),
    }


@app.post("/api/patients/{patient_id}/plans/review")
def review_plan(patient_id: str, body: ReviewIn) -> dict[str, Any]:
    _patient_or_404(patient_id)
    # Publishing must always operate on the latest persisted version, rather
    # than an in-memory object left by an earlier request/process.
    plan = read_patient_data(patient_id)[1] if body.action == "publish" else (PLANS.get(patient_id) or read_patient_data(patient_id)[1])
    if not plan:
        raise HTTPException(404, "请先生成方案草稿")
    # ``read_patient_data`` returns the version content directly, while the
    # in-memory response wraps it under ``draft``.  Normalize both shapes so
    # review actions always operate on the same structured plan object.
    if isinstance(plan.get("draft"), dict):
        draft = plan["draft"]
    elif plan.get("contract_version"):
        # DB reads return the flat content snapshot.  Copy it before wrapping
        # so ``plan["draft"]`` never points back to ``plan`` (which would make
        # persistence JSON-circular after a restart/review action).
        draft = dict(plan)
        for key in ("plan_id", "plan_version_id", "patient_id", "version", "status", "published_at"):
            draft.pop(key, None)
        plan = dict(plan)
    else:
        draft = {}
        plan = dict(plan)
    # Keep one mutable snapshot regardless of whether this request came from
    # memory (wrapper shape) or a fresh DB reload (flat content shape).
    plan["draft"] = draft
    validation = draft.get("validation_result", {}) or {}
    status_map = {"start_review": "IN_REVIEW", "return": "RETURNED", "pause": "PAUSED"}
    if body.action == "approve":
        # Review is deliberately independent from governance publication.
        # Candidate values may be reviewed/edited; governance provenance is
        # retained for audit but is not a patient-level publication blocker.
        if validation.get("content_validation", validation.get("nutrition_plan_validation")) not in (None, "PASS"):
            raise HTTPException(422, {"message": "方案内容校验未通过，不能审核", "errors": validation.get("errors", [])})
        if validation.get("safety_validation") == "BLOCKED" or draft.get("safety_level") == "red":
            raise HTTPException(422, {"message": "安全校验阻止审核通过", "errors": validation.get("publish_block_reasons", [])})
        gate = _derive_effective_publication_gate(draft, validation, clinician_review_status=None)
        hard_blockers = gate["hard_blockers"]
        if hard_blockers:
            raise HTTPException(422, {"message": "方案存在硬性阻断，不能审核通过", "errors": hard_blockers})
        draft["review_status"] = "APPROVED"
        draft["review_eligible"] = True
        resolved_review_reasons = [reason for reason in (validation.get("publish_block_reasons") or []) if reason not in hard_blockers]
        validation["resolved_review_reasons"] = resolved_review_reasons
        validation["publish_block_reasons"] = hard_blockers
        validation["publish_validation"] = "BLOCKED" if hard_blockers else "PASS"
        draft["publication_blocked"] = bool(hard_blockers)
        draft["publish_eligible"] = not hard_blockers
        # Keep the nested safety/publication projection in lockstep with the
        # effective gate. Clinical safety level and reasons are untouched.
        if isinstance(draft.get("safety_rules"), dict):
            draft["safety_rules"]["publication_blocked"] = bool(hard_blockers)
        status_map["approve"] = "APPROVED_PENDING_PUBLISH" if hard_blockers else "READY_TO_PUBLISH"
        validation["review_validation"] = "PASS"
        draft["validation_result"] = validation
        plan["draft"] = draft
    if body.action == "publish":
        if plan.get("status") not in {"READY_TO_PUBLISH", "APPROVED_PENDING_PUBLISH", "APPROVED_PENDING_MDT_ACTIVATION"}:
            raise HTTPException(422, "请先完成审核通过")
        if draft.get("review_status") != "APPROVED":
            raise HTTPException(422, "请先完成审核通过")
        gate = _derive_effective_publication_gate(draft, validation, clinician_review_status="APPROVED")
        if gate["hard_blockers"]:
            raise HTTPException(422, {"message": "安全校验未通过，不能发布", "errors": gate["hard_blockers"]})
        draft["publication_blocked"] = False
        draft["publish_eligible"] = True
        if isinstance(draft.get("safety_rules"), dict):
            draft["safety_rules"]["publication_blocked"] = False
        validation["publish_block_reasons"] = []
        validation["publish_validation"] = "PASS"
        draft["validation_result"] = validation
        with SessionLocal() as session:
            context = _governance_context(session)
        errors = validate_draft(draft, context["active_mdt_configs"])
        if errors or gate["hard_blockers"]:
            raise HTTPException(422, {"message": "安全校验未通过，不能发布", "errors": errors})
        status_map["publish"] = "PUBLISHED"
    plan["status"] = status_map.get(body.action, plan.get("status"))
    if body.action == "start_review":
        draft["review_status"] = "IN_REVIEW"
    elif body.action == "return":
        draft["review_status"] = "RETURNED"
        draft["publish_eligible"] = False
    elif body.action == "publish":
        draft["review_status"] = "APPROVED"
    if isinstance(plan.get("draft"), dict):
        from .plan_view import build_plan_view
        plan["draft"]["plan_view"] = build_plan_view({**plan["draft"], "patient_id": patient_id, "status": plan["status"]})
    plan["reviewer"] = body.reviewer
    plan["review_note"] = body.note
    plan["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    PLANS[patient_id] = plan
    persisted = update_plan(patient_id, plan, action={"start_review": "START_REVIEW", "approve": "APPROVE", "publish": "PUBLISH", "return": "RETURN", "pause": "PAUSE"}[body.action], reviewer_id=body.reviewer_id)
    if not persisted:
        raise HTTPException(503, "方案审核状态未能写入数据库")
    plan.update(persisted)
    PLANS[patient_id] = plan
    return plan


@app.get("/api/patients/{patient_id}/records")
def list_records(patient_id: str, record_type: str | None = Query(default=None)) -> list[dict[str, Any]]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            stmt = select(PatientRecordRow).where(PatientRecordRow.patient_id == patient_id).order_by(PatientRecordRow.record_date.desc(), PatientRecordRow.record_id.desc())
            if record_type:
                stmt = stmt.where(PatientRecordRow.record_type == record_type.upper())
            rows = session.scalars(stmt).all()
            return [{"record_id": r.record_id, "patient_id": r.patient_id, "record_date": _iso(r.record_date), "record_type": r.record_type, "actual_duration_min": r.actual_duration_min, "actual_reps": r.actual_reps, "actual_sets": r.actual_sets, "actual_times": r.actual_times, "intensity": r.intensity, "discomfort": r.discomfort, "note": r.note, "metadata_json": r.metadata_json} for r in rows]
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/patients/{patient_id}/weekly-review")
def get_weekly_review(patient_id: str) -> dict[str, Any]:
    """Return a V2 weekly decision derived from the patient's persisted records.

    This endpoint is intentionally read-only: it never changes a published plan
    and only returns a candidate decision for clinician review.
    """
    patient = _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            rows = session.scalars(select(PatientRecordRow).where(PatientRecordRow.patient_id == patient_id).order_by(PatientRecordRow.record_date.desc()).limit(30)).all()
            measurements = session.scalars(select(BodyMeasurementRecordRow).where(BodyMeasurementRecordRow.patient_id == patient_id).order_by(BodyMeasurementRecordRow.record_date.desc()).limit(30)).all()
            profile = read_patient_profile(patient_id) or {}
            records = [{"record_type": r.record_type, "status": (r.metadata_json or {}).get("status") or ("completed" if r.actual_duration_min or r.actual_reps or r.actual_sets else "partial"), "record_date": _iso(r.record_date), "metadata_json": r.metadata_json, "pending_sync": bool((r.metadata_json or {}).get("pending_sync"))} for r in rows]
            records.extend({"record_type": "BODY", "record_date": _iso(m.record_date), "weight_kg": m.weight_kg, "body_fat_pct": m.body_fat_pct, "waist_cm": m.waist_cm, "metadata_json": {}} for m in measurements)
            review = weekly_review(records, phenotype=(profile.get("a_f_phenotype") or "").split("｜", 1)[0], safety_level=profile.get("safety_level") or "green")
            return {"patient_id": patient_id, "window_days": 7, "record_count": len(records), "review": review, "records": records}
    except Exception as exc:
        raise HTTPException(503, f"周复评暂不可用: {exc}") from exc


@app.get("/api/patients/{patient_id}/plan/tasks")
def list_plan_tasks(patient_id: str) -> list[dict[str, Any]]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            # Only tasks derived from the current published plan version are
            # executable in the patient view. Historical version tasks remain
            # stored for audit/history but are not mixed into today's list.
            # Patient execution must follow the same newest PUBLISHED
            # version as the plan content endpoint.  The plan row may already
            # be IN_REVIEW for a newer draft, so _latest_plan() is not safe
            # here.
            current_plan, current_version = _latest_published_plan_version(session, patient_id)
            stmt = select(PlanTaskRow).where(PlanTaskRow.patient_id == patient_id, PlanTaskRow.active.is_(True))
            if current_version:
                stmt = stmt.where(PlanTaskRow.plan_version_id == current_version.plan_version_id)
            rows = session.scalars(stmt.order_by(PlanTaskRow.plan_task_id)).all()
            return [{"plan_task_id": r.plan_task_id, "plan_version_id": r.plan_version_id, "task_type": r.task_type, "task_name": r.task_name, "instructions": r.instructions, "schedule_json": r.schedule_json, "planned_duration_min": r.planned_duration_min, "planned_reps": r.planned_reps, "planned_sets": r.planned_sets, "planned_times": r.planned_times, "unit": r.unit} for r in rows]
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.post("/api/patients/{patient_id}/records")
def create_record(patient_id: str, body: RecordIn) -> dict[str, Any]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            row = PatientRecordRow(patient_id=patient_id, **body.model_dump())
            session.add(row)
            session.flush()
            session.add(BusinessEventRow(patient_id=patient_id, event_type="RECORD_SUBMITTED", object_type="patient_record", object_id=str(row.record_id), actor_type="PATIENT", actor_id=patient_id))
            session.commit()
            return {"record_id": row.record_id, "patient_id": patient_id, "record_date": _iso(row.record_date), "record_type": row.record_type}
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/patients/{patient_id}/measurements")
def list_measurements(patient_id: str) -> list[dict[str, Any]]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            rows = session.scalars(select(BodyMeasurementRecordRow).where(BodyMeasurementRecordRow.patient_id == patient_id).order_by(BodyMeasurementRecordRow.record_date.desc(), BodyMeasurementRecordRow.body_record_id.desc())).all()
            return [{"body_record_id": r.body_record_id, "record_date": _iso(r.record_date), "weight_kg": r.weight_kg, "body_fat_pct": r.body_fat_pct, "waist_cm": r.waist_cm, "heart_rate": r.heart_rate, "systolic_bp": r.systolic_bp, "diastolic_bp": r.diastolic_bp, "note": r.note} for r in rows]
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.post("/api/patients/{patient_id}/measurements")
def create_measurement(patient_id: str, body: BodyMeasurementIn) -> dict[str, Any]:
    _patient_or_404(patient_id)
    try:
        with SessionLocal() as session:
            row = BodyMeasurementRecordRow(patient_id=patient_id, source="PATIENT", **body.model_dump())
            session.add(row)
            session.flush()
            session.add(BusinessEventRow(patient_id=patient_id, event_type="RECORD_SUBMITTED", object_type="body_measurement_record", object_id=str(row.body_record_id), actor_type="PATIENT", actor_id=patient_id))
            session.commit()
            return {"body_record_id": row.body_record_id, "patient_id": patient_id, "record_date": _iso(row.record_date)}
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/consultations")
def list_consultations(patient_id: str | None = None) -> list[dict[str, Any]]:
    try:
        with SessionLocal() as session:
            stmt = select(ConsultationRow).order_by(ConsultationRow.updated_at.desc())
            if patient_id:
                stmt = stmt.where(ConsultationRow.patient_id == patient_id)
            rows = session.scalars(stmt).all()
            return [{"consultation_id": r.consultation_id, "patient_id": r.patient_id, "consultation_type": r.consultation_type, "description": r.description, "status": r.status, "handling_status": r.handling_status, "created_at": _iso(r.created_at), "updated_at": _iso(r.updated_at)} for r in rows]
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.post("/api/patients/{patient_id}/consultations")
def create_consultation(patient_id: str, body: ConsultationIn) -> dict[str, Any]:
    _patient_or_404(patient_id)
    cid = body.consultation_id or f"C{int(datetime.now().timestamp() * 1000)}"
    try:
        with SessionLocal() as session:
            row = ConsultationRow(consultation_id=cid, patient_id=patient_id, consultation_type=body.consultation_type, description=body.description, status="待回复", handling_status="待处理")
            session.add(row)
            session.add(ConsultationMessageRow(consultation_id=cid, sender_type="PATIENT", sender_id=patient_id, message_text=body.description))
            session.add(BusinessEventRow(patient_id=patient_id, event_type="CONSULTATION_CREATED", object_type="consultation", object_id=cid, actor_type="PATIENT", actor_id=patient_id))
            session.commit()
            return {"consultation_id": cid, "patient_id": patient_id, "status": row.status, "handling_status": row.handling_status}
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/consultations/{consultation_id}/messages")
def list_messages(consultation_id: str) -> list[dict[str, Any]]:
    try:
        with SessionLocal() as session:
            rows = session.scalars(select(ConsultationMessageRow).where(ConsultationMessageRow.consultation_id == consultation_id).order_by(ConsultationMessageRow.created_at)).all()
            return [{"message_id": r.message_id, "consultation_id": r.consultation_id, "sender_type": r.sender_type, "sender_id": r.sender_id, "message_text": r.message_text, "attachment_json": r.attachment_json, "created_at": _iso(r.created_at)} for r in rows]
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.post("/api/consultations/{consultation_id}/complete")
def complete_consultation(consultation_id: str) -> dict[str, Any]:
    try:
        with SessionLocal() as session:
            row = session.get(ConsultationRow, consultation_id)
            if not row:
                raise HTTPException(404, "咨询不存在")
            row.status, row.handling_status = "已完成", "已完成"
            session.commit()
            return {"consultation_id": consultation_id, "status": row.status, "handling_status": row.handling_status}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.post("/api/consultations/{consultation_id}/messages")
def create_message(consultation_id: str, body: MessageIn) -> dict[str, Any]:
    try:
        with SessionLocal() as session:
            consult = session.get(ConsultationRow, consultation_id)
            if not consult:
                raise HTTPException(404, "咨询不存在")
            row = ConsultationMessageRow(consultation_id=consultation_id, **body.model_dump())
            session.add(row)
            if body.sender_type == "CLINICIAN":
                consult.status, consult.handling_status = "已回复", "处理中"
                session.add(ConsultationReplyRow(consultation_id=consultation_id, clinician_id=int(body.sender_id or 1), reply_text=body.message_text))
                session.add(BusinessEventRow(patient_id=consult.patient_id, event_type="CONSULTATION_REPLIED", object_type="consultation", object_id=consultation_id, actor_type="CLINICIAN", actor_id=body.sender_id or "1"))
            session.commit()
            return {"message_id": row.message_id, "consultation_id": consultation_id, "status": consult.status}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/education")
def list_education(published_only: bool = True) -> list[dict[str, Any]]:
    try:
        with SessionLocal() as session:
            stmt = select(EducationContentRow).order_by(EducationContentRow.updated_at.desc())
            if published_only:
                stmt = stmt.where(EducationContentRow.status == "PUBLISHED")
            rows = session.scalars(stmt).all()
            return [{"education_id": r.education_id, "title": r.title, "category": r.category, "content_type": r.content_type, "duration_seconds": r.duration_seconds, "intro": r.intro, "video_url": r.video_url, "qr_code_url": r.qr_code_url, "body_text": r.body_text, "status": r.status, "published_at": _iso(r.published_at)} for r in rows]
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.post("/api/education/{education_id}/publish")
def publish_education(education_id: int, body: EducationPublishIn) -> dict[str, Any]:
    try:
        with SessionLocal() as session:
            row = session.get(EducationContentRow, education_id)
            if not row:
                raise HTTPException(404, "宣教内容不存在")
            row.status, row.published_by, row.published_at = "PUBLISHED", body.published_by, datetime.utcnow()
            session.commit()
            return {"education_id": row.education_id, "status": row.status, "published_at": _iso(row.published_at)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/monitoring/alerts")
def list_alerts(patient_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    try:
        with SessionLocal() as session:
            stmt = select(MonitoringAlertRow).order_by(MonitoringAlertRow.triggered_at.desc())
            if patient_id:
                stmt = stmt.where(MonitoringAlertRow.patient_id == patient_id)
            if status:
                stmt = stmt.where(MonitoringAlertRow.status == status.upper())
            rows = session.scalars(stmt).all()
            return [{"alert_id": r.alert_id, "patient_id": r.patient_id, "alert_type": r.alert_type, "latest_value": r.latest_value, "trend": r.trend, "safety_level": r.safety_level, "status": r.status, "triggered_at": _iso(r.triggered_at), "handled_at": _iso(r.handled_at), "note": r.note} for r in rows]
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.post("/api/monitoring/alerts/{alert_id}/handle")
def handle_alert(alert_id: int, reviewer_id: int = 1, note: str = "") -> dict[str, Any]:
    try:
        with SessionLocal() as session:
            row = session.get(MonitoringAlertRow, alert_id)
            if not row:
                raise HTTPException(404, "异常记录不存在")
            row.status, row.handled_by, row.handled_at, row.note = "HANDLED", reviewer_id, datetime.utcnow(), note
            session.commit()
            return {"alert_id": alert_id, "status": row.status, "handled_at": _iso(row.handled_at)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/dashboard/summary")
def dashboard_summary() -> dict[str, int]:
    """Counts are calculated from shared business tables, not hard-coded UI values."""
    try:
        with SessionLocal() as session:
            patients = len(session.scalars(select(PatientRow)).all())
            pending_assessment = len(session.scalars(select(AssessmentRow).where(AssessmentRow.status == "SUBMITTED")).all())
            pending_assessment_review = len(session.scalars(select(AssessmentRow).where(AssessmentRow.status == "UNDER_REVIEW")).all())
            pending_plan_review = len(session.scalars(select(PlanRow).where(PlanRow.status.in_(["AI_GENERATED_PENDING_REVIEW", "IN_REVIEW"]))).all())
            pending_publish = len(session.scalars(select(PlanRow).where(PlanRow.status == "APPROVED_PENDING_PUBLISH")).all())
            alerts = len(session.scalars(select(MonitoringAlertRow).where(MonitoringAlertRow.status == "PENDING")).all())
            yellow_alerts = len(session.scalars(select(MonitoringAlertRow).where(MonitoringAlertRow.status == "PENDING", MonitoringAlertRow.safety_level == "YELLOW")).all())
            red_alerts = len(session.scalars(select(MonitoringAlertRow).where(MonitoringAlertRow.status == "PENDING", MonitoringAlertRow.safety_level == "RED")).all())
            consults = len(session.scalars(select(ConsultationRow).where(ConsultationRow.status == "待回复")).all())
            pending_consult = len(session.scalars(select(ConsultationRow).where(ConsultationRow.handling_status.in_(["待处理", "处理中"]))).all())
            return {"patients": patients, "pending_assessment": pending_assessment, "pending_assessment_review": pending_assessment_review, "pending_plan_review": pending_plan_review, "pending_publish": pending_publish, "pending_plan": pending_plan_review + pending_publish, "pending_alert": alerts, "yellow_alerts": yellow_alerts, "red_alerts": red_alerts, "unreplied_consultation": consults, "pending_consultation": pending_consult}
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc


@app.get("/api/todos")
def list_todos(tab: str | None = Query(default=None)) -> list[dict[str, Any]]:
    """Build the clinician work queue from the same assessment/plan rows used by
    patient 360; there is deliberately no second todo status store."""
    allowed = {"pending-assessment", "assessment-review", "plan-review", "publish", "returned"}
    if tab and tab not in allowed:
        raise HTTPException(400, "不支持的待办分类")
    try:
        with SessionLocal() as session:
            patients = {p.patient_id: p for p in session.scalars(select(PatientRow)).all()}
            assessments = {}
            for row in session.scalars(select(AssessmentRow).order_by(AssessmentRow.assessment_version.desc(), AssessmentRow.assessment_id.desc())).all():
                assessments.setdefault(row.patient_id, row)
            plans = {}
            for row in session.scalars(select(PlanRow).order_by(PlanRow.updated_at.desc(), PlanRow.plan_id.desc())).all():
                plans.setdefault(row.patient_id, row)

            items: list[dict[str, Any]] = []
            def add(patient_id: str, item_tab: str, item_type: str, summary: str, status: str, updated: Any) -> None:
                if tab and tab != item_tab:
                    return
                patient = patients.get(patient_id)
                if not patient:
                    return
                items.append({"key": f"{item_tab}-{patient_id}", "tab": item_tab, "patient": patient.name, "id": patient_id, "type": item_type, "summary": summary, "updated": _iso(updated) or "", "status": status})

            for patient_id in patients:
                assessment = assessments.get(patient_id)
                plan = plans.get(patient_id)
                if not assessment:
                    add(patient_id, "pending-assessment", "首次评估", "尚未提交 Q1–Q55 评估", "待完成", None)
                elif assessment.status in {"SUBMITTED", "UNDER_REVIEW"}:
                    add(patient_id, "assessment-review", "首次评估", "Q1–Q55 已提交，等待审核", "待审核", assessment.updated_at)
                elif assessment.status == "RETURNED":
                    add(patient_id, "returned", "评估退回", "评估需要补充后重新提交", "已退回", assessment.updated_at)
                if plan and plan.status in {"AI_GENERATED_PENDING_REVIEW", "IN_REVIEW"}:
                    add(patient_id, "plan-review", "AI方案草稿", "方案草稿等待医护审核", "待审核", plan.updated_at)
                elif plan and plan.status == "APPROVED_PENDING_PUBLISH":
                    add(patient_id, "publish", "已审核方案", "审核通过，等待正式发布", "待发布", plan.updated_at)
                elif plan and plan.status == "RETURNED":
                    add(patient_id, "returned", "方案草稿", "方案已退回，等待修改后重新提交", "已退回", plan.updated_at)
            return items
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"数据库暂不可用: {exc}") from exc
