"""Regression coverage for approval status and publication blockers."""

from copy import deepcopy

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app import db


@pytest.fixture
def lifecycle_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db.Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        session.add(db.ClinicianAccountRow(clinician_id=1, username="test-reviewer", display_name="Test Reviewer"))
        session.add(db.PatientRow(patient_id="P001", name="Test Patient", sex="女"))
        session.commit()
    monkeypatch.setattr(db, "SessionLocal", session_factory)
    monkeypatch.setattr(main, "SessionLocal", session_factory)
    monkeypatch.setattr(main, "_patient_or_404", lambda patient_id: {"patient_id": patient_id})
    monkeypatch.setattr(main, "_governance_context", lambda session: {"active_mdt_configs": []})
    return session_factory


def _persist_lifecycle_plan(session_factory, *, status="IN_REVIEW", marker="A"):
    draft = {
        "contract_version": "2.1",
        "generator_type": "RULE_BASED",
        "generation_source": "RULE_BASED",
        "rule_authority": "PROJECT_BASELINE_V2_V3",
        "patient_id": "P001",
        "primary_nutrition_phenotype": "B",
        "complexity_overlay": "none",
        "display_phenotype": "B",
        "safety_level": "yellow",
        "safety_rules": {"safety_level": "yellow", "publication_blocked": True},
        "clinician_notes": {"review_required": True},
        "energy_state": {"energy_target": {"status": "PROVISIONAL", "provisional_energy_target_kcal": 1600}},
        "validation_result": {
            "content_validation": "PASS",
            "nutrition_plan_validation": "PASS",
            "exercise_validation": "PASS",
            "pulmonary_validation": "PASS",
            "safety_validation": "PASS",
            "review_validation": "PASS",
            "publish_validation": "BLOCKED",
            "publish_block_reasons": ["能量状态为PROVISIONAL/UNAVAILABLE，需医护审核"],
        },
        "publication_blocked": True,
        "review_eligible": True,
        "publish_eligible": False,
        "diet_plan": {},
        "exercise_plan": [],
        "pulmonary_prehab_plan": [],
        "diet_plan_trace": {},
        "exercise_plan_trace": {},
        "pulmonary_rehab_trace": {},
        "artifact_manifest": {"status": "PASS"},
        "stage_goals": {},
        "monitoring_plan": {},
        "weekly_review": {},
        "marker": marker,
    }
    with session_factory() as session:
        plan = db.PlanRow(patient_id="P001", status=status, current_version_no=1)
        session.add(plan)
        session.flush()
        session.add(db.PlanVersionRow(plan_id=plan.plan_id, version_no=1, status=status, content_json=draft))
        session.commit()
    return draft


def _reviewable_plan(*, publication_blocked: bool, publish_validation: str, safety_level: str = "green", reasons=None, energy_status="PROVISIONAL"):
    return {
        "status": "IN_REVIEW",
        "draft": {
            "publication_blocked": publication_blocked,
            "safety_level": safety_level,
            "energy_state": {"energy_target": {"status": energy_status}},
            "validation_result": {
                "content_validation": "PASS",
                "safety_validation": "PASS",
                "publish_validation": publish_validation,
                "publish_block_reasons": list(reasons or []),
            },
        },
    }


def _approve(monkeypatch, plan):
    monkeypatch.setattr(main, "PLANS", {"P001": plan})
    monkeypatch.setattr(main, "_patient_or_404", lambda patient_id: {"patient_id": patient_id})
    monkeypatch.setattr(main, "update_plan", lambda *args, **kwargs: {"persisted": True})
    return main.review_plan("P001", main.ReviewIn(action="approve"))


def test_blocked_approval_stays_pending_publish(monkeypatch):
    plan = _reviewable_plan(publication_blocked=True, publish_validation="BLOCKED")

    with pytest.raises(HTTPException) as exc_info:
        _approve(monkeypatch, plan)

    assert exc_info.value.status_code == 422
    assert "硬性阻断" in str(exc_info.value.detail)


def test_unblocked_yellow_approval_enters_ready_to_publish(monkeypatch):
    # YELLOW is not itself a publication blocker; only the explicit blocker
    # and existing publication validation determine the workflow state.
    plan = _reviewable_plan(publication_blocked=False, publish_validation="PASS", safety_level="yellow")

    result = _approve(monkeypatch, plan)

    assert result["status"] == "READY_TO_PUBLISH"


def test_provisional_energy_review_is_resolved_by_whole_plan_approval(monkeypatch):
    plan = _reviewable_plan(
        publication_blocked=True,
        publish_validation="BLOCKED",
        reasons=["能量状态为PROVISIONAL/UNAVAILABLE，需医护审核"],
        energy_status="PROVISIONAL",
    )

    result = _approve(monkeypatch, plan)

    assert result["status"] == "READY_TO_PUBLISH"
    assert result["draft"]["review_status"] == "APPROVED"
    assert result["draft"]["energy_state"]["energy_target"]["status"] == "PROVISIONAL"
    assert result["draft"]["publication_blocked"] is False


def test_unavailable_energy_remains_hard_blocker(monkeypatch):
    plan = _reviewable_plan(
        publication_blocked=True,
        publish_validation="BLOCKED",
        reasons=["能量状态为PROVISIONAL/UNAVAILABLE，需医护审核"],
        energy_status="UNAVAILABLE",
    )

    with pytest.raises(HTTPException) as exc_info:
        _approve(monkeypatch, plan)

    assert exc_info.value.status_code == 422
    assert "硬性阻断" in str(exc_info.value.detail)


def test_validator_failure_cannot_be_bypassed(monkeypatch):
    plan = _reviewable_plan(publication_blocked=False, publish_validation="PASS")
    plan["draft"]["validation_result"]["exercise_validation"] = "FAIL"

    with pytest.raises(HTTPException) as exc_info:
        _approve(monkeypatch, plan)

    assert exc_info.value.status_code == 422
    assert "硬性阻断" in str(exc_info.value.detail)


def test_approve_persists_optional_review_note(monkeypatch):
    plan = _reviewable_plan(publication_blocked=False, publish_validation="PASS")
    persisted = {}

    monkeypatch.setattr(main, "PLANS", {"P001": plan})
    monkeypatch.setattr(main, "_patient_or_404", lambda patient_id: {"patient_id": patient_id})
    monkeypatch.setattr(main, "update_plan", lambda patient_id, value, **kwargs: persisted.update(value) or {"persisted": True})

    result = main.review_plan("P001", main.ReviewIn(action="approve", note="整体审核通过"))

    assert result["review_note"] == "整体审核通过"
    assert persisted["review_note"] == "整体审核通过"


def test_return_for_revision_persists_note(monkeypatch):
    plan = _reviewable_plan(publication_blocked=False, publish_validation="PASS")
    persisted = {}

    monkeypatch.setattr(main, "PLANS", {"P001": plan})
    monkeypatch.setattr(main, "_patient_or_404", lambda patient_id: {"patient_id": patient_id})
    monkeypatch.setattr(main, "update_plan", lambda patient_id, value, **kwargs: persisted.update(value) or {"persisted": True})

    result = main.review_plan("P001", main.ReviewIn(action="return", note="请调整早餐主食"))

    assert result["status"] == "RETURNED"
    assert result["review_note"] == "请调整早餐主食"
    assert persisted["review_note"] == "请调整早餐主食"


def test_approve_reload_publish_persists_full_snapshot(lifecycle_db, monkeypatch):
    _persist_lifecycle_plan(lifecycle_db)
    monkeypatch.setattr(main, "PLANS", {})

    approved = main.review_plan("P001", main.ReviewIn(action="approve", note="E2E lifecycle persistence A."))
    assert approved["status"] == "READY_TO_PUBLISH"
    assert approved["draft"]["review_status"] == "APPROVED"
    assert approved["draft"]["publication_blocked"] is False
    assert approved["draft"]["safety_rules"]["publication_blocked"] is False
    assert approved["draft"]["energy_state"]["energy_target"]["status"] == "PROVISIONAL"
    assert approved["draft"]["safety_level"] == "yellow"

    monkeypatch.setattr(main, "PLANS", {})
    reloaded = main.read_patient_data("P001")[1]
    assert reloaded["status"] == "READY_TO_PUBLISH"
    assert reloaded["review_status"] == "APPROVED"
    assert reloaded["review_note"] == "E2E lifecycle persistence A."
    assert reloaded["publication_blocked"] is False
    assert reloaded["safety_rules"]["publication_blocked"] is False

    published = main.review_plan("P001", main.ReviewIn(action="publish", note="E2E lifecycle publish A."))
    assert published["status"] == "PUBLISHED"
    latest = db.read_published_plan("P001")
    assert latest["status"] == "PUBLISHED"
    assert latest["version"] == 1
    assert latest["review_status"] == "APPROVED"
    assert latest["publication_blocked"] is False


def test_return_reload_keeps_note_and_historical_published(lifecycle_db, monkeypatch):
    base = _persist_lifecycle_plan(lifecycle_db, status="PUBLISHED", marker="A")
    with lifecycle_db() as session:
        plan = session.query(db.PlanRow).filter_by(patient_id="P001").one()
        plan.current_version_no = 2
        draft_b = deepcopy(base)
        draft_b["marker"] = "B"
        session.add(db.PlanVersionRow(plan_id=plan.plan_id, version_no=2, status="RULE_GENERATED_PENDING_REVIEW", content_json=draft_b))
        session.commit()
    monkeypatch.setattr(main, "PLANS", {})
    returned = main.review_plan("P001", main.ReviewIn(action="return", note="E2E return-for-revision C."))
    assert returned["status"] == "RETURNED"
    monkeypatch.setattr(main, "PLANS", {})
    reloaded = main.read_patient_data("P001")[1]
    assert reloaded["status"] == "RETURNED"
    assert reloaded["review_status"] == "RETURNED"
    assert reloaded["review_note"] == "E2E return-for-revision C."
    published = db.read_published_plan("P001")
    assert published["version"] == 1
    assert published["marker"] == "A"
