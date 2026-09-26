from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile
from app.v4_exercise_trace import build_canonical_exercise_week

from tests.test_v2_catalog_and_golden import _payload


def _action(eid="A01", *, status="DRAFT", confirmed=False):
    return {
        "exercise_id": eid,
        "name": f"action-{eid}",
        "category": "aerobic",
        "status": status,
        "mdt_confirmed": confirmed,
        "candidate_dose": "5-10 min",
        "duration_range": "5-10 min",
    }


def _week():
    return [
        {"day": 1, "aerobic": [_action()], "resistance": [], "flexibility": [], "day_type": "aerobic"},
        {"day": 2, "aerobic": [], "resistance": [], "flexibility": [], "day_type": "rest"},
        {"day": 3, "aerobic": [_action("A02")], "resistance": [_action("R01")], "flexibility": [], "day_type": "mixed"},
        {"day": 4, "aerobic": [], "resistance": [], "flexibility": [], "day_type": "rest"},
        {"day": 5, "aerobic": [], "resistance": [], "flexibility": [_action("S01")], "day_type": "flexibility"},
        {"day": 6, "aerobic": [], "resistance": [], "flexibility": [], "day_type": "rest"},
        {"day": 7, "aerobic": [], "resistance": [], "flexibility": [], "day_type": "rest"},
    ]


def test_trace_has_v4_root_days_roles_and_stable_action_identity():
    trace, projection, flat = build_canonical_exercise_week(
        _week(),
        combo={"aerobic_days_target": [1, 5], "resistance_days_target": [1, 3]},
        v4_phenotype_contract={"primary_nutrition_phenotype": "A", "complexity_overlay": "none", "display_phenotype": "A"},
        allowed_action_ids={"A01", "A02", "R01", "S01"},
    )
    assert trace["schema_version"] == "EXERCISE_TRACE_V4_2"
    assert [x["day"] for x in trace["daily_schedule"]] == list(range(1, 8))
    assert trace["trace_materialization_status"] == "FULL"
    assert trace["weekly_schedule_derived"] == {
        "formal_aerobic_days_actual": 2,
        "functional_activity_days_actual": 0,
        "resistance_days_actual": 1,
        "recovery_days_actual": 0,
        "flexibility_days_actual": 1,
    }
    assert trace["daily_schedule"][1]["sessions"] == []
    assert trace["daily_schedule"][1]["reason"]
    action = trace["daily_schedule"][0]["sessions"][0]["actions"][0]
    assert action["action_id"] == "A01"
    assert action["patient_display_name"] == "action-A01"
    assert action["dose_status"] == "PROVISIONAL"
    assert action["duration_min"] is None
    assert projection[0]["aerobic"][0]["action_id"] == "A01"
    assert flat[0]["action_id"] == "A01"


def test_frozen_golden_cases_get_structural_trace_and_e_pending_marker():
    for case_id in ("SYN-A01", "SYN-C01", "SYN-E01", "SYN-F01"):
        payload = _payload(case_id)
        plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
        trace = plan["exercise_plan_trace"]
        assert trace["trace_materialization_status"] == "FULL"
        assert len(trace["daily_schedule"]) == 7
        assert all(session["session_role"] in {"FORMAL_AEROBIC", "RESISTANCE", "FLEXIBILITY"} for day in trace["daily_schedule"] for session in day["sessions"])
        if case_id == "SYN-E01":
            assert trace["context_snapshot"]["formal_aerobic_eligibility"]["status"] == "NOT_ASSESSED"
            validation = trace["context_snapshot"]["e_formal_aerobic_validation"]
            assert validation["eligibility_status"] == "NOT_ASSESSED"
            assert validation["status"] == "FAIL"
            assert validation["reason_codes"] == ["E_ELIGIBILITY_NOT_ASSESSED"]
            assert validation["formal_aerobic_days_target"] is None
            assert isinstance(validation["formal_aerobic_days_target"], (int, float, type(None)))
            assert not isinstance(validation["formal_aerobic_days_target"], (list, tuple, range))
            assert trace["weekly_schedule_declared"]["formal_aerobic_days_target"] == (2, 3)
            assert trace["weekly_schedule_derived"]["formal_aerobic_days_actual"] == 3
            assert "PENDING_REVIEW" not in validation.values()
            assert trace["trace_materialization_status"] == "FULL"


def test_f_overlay_context_keeps_underlying_primary_and_manual_review_reason():
    trace, _, _ = build_canonical_exercise_week(
        _week(),
        combo={"aerobic_days_target": [1, 5], "resistance_days_target": [1, 3]},
        v4_phenotype_contract={"primary_nutrition_phenotype": "B", "complexity_overlay": "F", "display_phenotype": "F", "reasons": ["complexity"]},
        allowed_action_ids={"A01", "A02", "R01", "S01"},
    )
    assert trace["context_snapshot"]["primary_nutrition_phenotype"] == "B"
    assert trace["context_snapshot"]["complexity_overlay"] == "F"
    assert trace["context_snapshot"]["display_phenotype"] == "F"
    assert trace["context_snapshot"]["complexity_reduction"]["applied"] is True
