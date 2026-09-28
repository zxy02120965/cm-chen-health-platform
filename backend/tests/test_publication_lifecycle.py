"""Regression coverage for approval status and publication blockers."""

import pytest
from fastapi import HTTPException

from app import main


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
