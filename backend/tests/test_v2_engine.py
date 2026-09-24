from app.rules import assess_payload, generate_plan_draft
from app.v2_engine import weekly_review
from app.plan_contract import contract_missing_keys


def _case(**extra):
    payload = {
        "sex": "女", "height_cm": 165, "weight_kg": 68,
        "food_allergy": "无", "swallowing": "无", "recent_weight_intake": "稳定",
        "surgery_window_days": 30, "six_minute_walk_m": 420, "spo2_percent": 97,
        "q6_surgeryWindow": "2–4周", "q15_weight": 68, "q22_bmr": 1350,
    }
    payload.update(extra)
    return payload


def test_structured_v21_contract_has_all_sections_and_optional_q56():
    payload = _case(q56_goal={"has_clinician_goal": False})
    evaluation = assess_payload(payload)
    draft = generate_plan_draft({}, payload, evaluation)
    assert draft["contract_version"] == "2.1"
    assert not contract_missing_keys(draft)
    assert draft["goal_source"] == "SYSTEM_DEFAULT_AF"
    assert draft["nutrition_generation_status"] == "incomplete"
    assert draft["diet_plan"]["components"] == []
    assert draft["exercise_plan"]
    assert draft["pulmonary_prehab_plan"]
    assert draft["energy_calculation"]["daily_energy_target_kcal"] is None


def test_q56_clinician_goal_is_preserved_without_overriding_safety():
    payload = _case(q56_goal={"has_clinician_goal": True, "primary_goal": "ENHANCED_FAT_LOSS"}, q12_respiratorySymptoms=["胸痛"])
    evaluation = assess_payload(payload)
    draft = generate_plan_draft({}, payload, evaluation)
    assert draft["safety_level"] == "red"
    assert draft["goal_source"] == "Q56_CLINICIAN"
    assert draft["exercise_plan"] == []
    assert draft["pulmonary_prehab_plan"] == []


def test_weekly_review_is_conservative_with_sparse_data():
    result = weekly_review([{"status": "completed"}] * 2)
    assert result["decision"] == "DATA_INSUFFICIENT"
    assert result["confidence"] == "LOW"
