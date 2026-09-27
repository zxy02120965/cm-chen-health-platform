"""Regression coverage for approval status and publication blockers."""

from app import main


def _reviewable_plan(*, publication_blocked: bool, publish_validation: str, safety_level: str = "green"):
    return {
        "status": "IN_REVIEW",
        "draft": {
            "publication_blocked": publication_blocked,
            "safety_level": safety_level,
            "validation_result": {
                "content_validation": "PASS",
                "safety_validation": "PASS",
                "publish_validation": publish_validation,
                "publish_block_reasons": [],
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

    result = _approve(monkeypatch, plan)

    assert result["status"] == "APPROVED_PENDING_PUBLISH"
    assert result["status"] != "READY_TO_PUBLISH"


def test_unblocked_yellow_approval_enters_ready_to_publish(monkeypatch):
    # YELLOW is not itself a publication blocker; only the explicit blocker
    # and existing publication validation determine the workflow state.
    plan = _reviewable_plan(publication_blocked=False, publish_validation="PASS", safety_level="yellow")

    result = _approve(monkeypatch, plan)

    assert result["status"] == "READY_TO_PUBLISH"
