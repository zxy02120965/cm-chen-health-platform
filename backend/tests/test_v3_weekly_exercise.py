from app.v2_engine import build_v2_plan, build_v3_weekly_exercise, candidate_test_profile
from app.rules import assess_payload
from app.plan_validator import validate_plan


def _green_a_payload():
    return {
        "sex": "女", "age_years": 54, "q14_height": 165, "q15_weight": 68,
        "height_cm": 165, "weight_kg": 68, "q6_surgeryWindow": "4–8周",
        "q12_respiratorySymptoms": ["无"], "q28_weightChange": "稳定",
        "q29_appetite": "正常", "q30_intake": "正常",
        "q31_eatingDifficulties": ["无明显困难"], "q34_dietPattern": ["三餐规律"],
        "q37_activityLimitations": ["无明显限制"], "q43_metabolicConditions": ["无"],
        "q51_executionBarriers": ["无"],
    }


def test_v3_a_week_has_day1_to_day7_and_complete_resistance_combo():
    payload = _green_a_payload()
    evaluation = assess_payload(payload)
    plan = build_v2_plan(payload, evaluation, active_configs=candidate_test_profile())
    assert plan["rule_version"] == "V3.0"
    assert [d["day"] for d in plan["weekly_schedule"]] == list(range(1, 8))
    resistance_days = [d for d in plan["weekly_schedule"] if d["resistance"]]
    assert 2 <= len(resistance_days) <= 3
    assert all(4 <= len(d["resistance"]) <= 6 for d in resistance_days)
    assert all(b - a > 1 for a, b in zip([d["day"] for d in resistance_days], [d["day"] for d in resistance_days][1:]))
    assert len({d["aerobic"][0]["exercise_id"] for d in plan["weekly_schedule"] if d["aerobic"]}) >= 2


def test_v3_validator_rejects_incomplete_resistance_combo():
    payload = _green_a_payload()
    evaluation = assess_payload(payload)
    plan = build_v2_plan(payload, evaluation, active_configs=candidate_test_profile())
    plan["weekly_schedule"][0]["resistance"] = plan["weekly_schedule"][0]["resistance"][:1]
    result = validate_plan(plan, mode="TEST_ONLY")
    assert result["status"] == "FAIL"
    assert any("动作数量" in error for error in result["errors"])


def test_v3_red_safety_removes_training_days():
    payload = _green_a_payload()
    payload["q12_respiratorySymptoms"] = ["胸痛"]
    evaluation = assess_payload(payload)
    plan = build_v2_plan(payload, evaluation, active_configs=candidate_test_profile())
    assert evaluation["safety"] == "red"
    assert all(not d["resistance"] and not d["aerobic"] for d in plan["weekly_schedule"])
