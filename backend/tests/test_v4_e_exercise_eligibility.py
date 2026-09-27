import json
from pathlib import Path

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile
from app.v4_e_exercise_eligibility import (
    apply_e_eligibility_to_schedule,
    derive_e_formal_aerobic_eligibility,
)


FIXTURE = Path(__file__).parent / "fixtures" / "v4_contract" / "SYN-E01.json"


def _e_payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["assessment_payload"]


def test_markedly_reduced_intake_defers_formal_aerobic_without_threshold_inference():
    result = derive_e_formal_aerobic_eligibility(
        _e_payload(), safety_level="yellow", primary_nutrition_phenotype="E"
    )
    assert result["intake_stability"] == "MARKEDLY_REDUCED"
    assert result["weight_trend"] == "UNKNOWN"
    assert result["fatigue_recovery"] == "LIMITED"
    assert result["borg_function_review"] == "UNKNOWN"
    assert result["status"] == "DEFERRED_FOR_NUTRITION_RECOVERY"
    assert "MARKEDLY_REDUCED_INTAKE" in result["reasons"]
    assert "SAFETY_BURDEN" not in result["reasons"]
    assert result["source_trace"]["fatigue_recovery"].endswith("q51_executionBarriers")
    assert result["source_trace"]["safety_burden"].startswith("existing_reason_codes")


def test_missing_e_inputs_remain_not_assessed():
    result = derive_e_formal_aerobic_eligibility(
        {"q30_intake": None, "q28_weightChange": None},
        safety_level="GREEN",
        primary_nutrition_phenotype="E",
    )
    assert result["status"] == "NOT_ASSESSED"
    assert all(result[key] == "UNKNOWN" for key in (
        "intake_stability", "weight_trend", "fatigue_recovery", "borg_function_review"
    ))


def test_yellow_without_explicit_nutrition_or_exercise_blocker_is_not_a_defer_shortcut():
    result = derive_e_formal_aerobic_eligibility(
        {
            "intake_stability": "UNKNOWN",
            "weight_trend": "UNKNOWN",
            "fatigue_recovery": "UNKNOWN",
            "borg_function_review": "UNKNOWN",
        },
        safety_level="YELLOW",
        primary_nutrition_phenotype="E",
        existing_reason_codes=[],
    )
    assert result["status"] == "NOT_ASSESSED"
    assert "SAFETY_BURDEN" not in result["reasons"]


def test_deferred_schedule_removes_formal_aerobic_and_keeps_derived_consistency():
    payload = _e_payload()
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    trace = plan["exercise_plan_trace"]
    validation = trace["context_snapshot"]["e_formal_aerobic_validation"]
    assert validation["formal_aerobic_days_target"] == 0
    assert validation["zero_day_reason_present"] is True
    assert validation["status"] == "PASS"
    assert trace["weekly_schedule_derived"]["formal_aerobic_days_actual"] == 0
    assert trace["weekly_schedule_derived"]["functional_activity_days_actual"] == 0
    assert trace["weekly_schedule_declared"]["functional_activity_days_target"] == ">0_or_as_tolerated"
    assert trace["context_snapshot"]["formal_aerobic_eligibility"]["reasons"] == [
        "MARKEDLY_REDUCED_INTAKE", "NUTRITION_RECOVERY_PRIORITY"
    ]
    assert trace["context_snapshot"]["e_formal_aerobic_validation"]["functional_activity_preserved_when_safe"] is None
    assert trace["context_snapshot"]["functional_activity_materialization"] == {
        "status": "UNAVAILABLE",
        "reason_codes": ["FUNCTIONAL_ACTIVITY_SOURCE_UNAVAILABLE"],
    }
    assert trace["schedule_consistency_validation"]["status"] == "PASS"
    assert trace["trace_materialization_status"] == "FULL"


def test_functional_activity_is_not_counted_as_formal_aerobic():
    action = {"exercise_id": "A01", "name": "舒适轻走", "status": "DRAFT", "mdt_confirmed": False, "candidate_dose": "按需"}
    schedule = [
        {"day": 1, "aerobic": [], "resistance": [], "flexibility": [], "functional_activity": [action], "functional_activity_session_role": "FUNCTIONAL_ACTIVITY"}
    ] + [{"day": day, "aerobic": [], "resistance": [], "flexibility": []} for day in range(2, 8)]
    eligibility = {"status": "DEFERRED_FOR_NUTRITION_RECOVERY"}
    adjusted, _ = apply_e_eligibility_to_schedule(schedule, eligibility)
    assert adjusted[0]["functional_activity"][0]["exercise_id"] == "A01"


def test_allowed_low_dose_is_not_forced_to_zero_days():
    payload = {
        "intake_stability": "STABLE",
        "weight_trend": "STABLE",
        "fatigue_recovery": "ACCEPTABLE",
        "borg_function_review": "ACCEPTABLE",
    }
    result = derive_e_formal_aerobic_eligibility(
        payload, safety_level="GREEN", primary_nutrition_phenotype="E"
    )
    assert result["status"] == "ALLOWED_LOW_DOSE"
