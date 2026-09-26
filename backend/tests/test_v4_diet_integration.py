from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


def _payload(patient_id="SYN-V4-DIET", *, severe_decline=False):
    value = {
        "patient_id": patient_id,
        "sex": "女",
        "age_years": 54,
        "q14_height": 165,
        "q15_weight": 68,
        "height_cm": 165,
        "weight_kg": 68,
        "q6_surgeryWindow": "4–8周",
        "q12_respiratorySymptoms": ["无"],
        "q28_weightChange": "不明原因下降" if severe_decline else "稳定",
        "q29_appetite": "正常",
        "q30_intake": "减少50%" if severe_decline else "正常",
        "q31_eatingDifficulties": ["无明显困难"],
        "q32_foodAllergy": ["无"],
        "q33_foodIntolerance": ["无"],
        "q34_dietPattern": ["三餐规律"],
        "q37_activityLimitations": ["无明显限制"],
        "q43_metabolicConditions": ["无"],
        "q51_executionBarriers": ["无"],
    }
    return value


def test_build_plan_exposes_canonical_trace_and_projections():
    payload = _payload()
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    trace = plan["diet_plan_trace"]
    assert trace is plan["canonical_week_diet"]
    assert trace["trace_schema_version"] == "FOOD_TRACE_V4_2"
    assert len(trace["days"]) == 7
    assert len(plan["weekly_schedule"]) == 7
    assert plan["weekly_schedule"][0]["diet"]
    for day in trace["days"]:
        for meal in day["meals"].values():
            for item in meal["food_items"]:
                assert item["food_item_id"]
                assert item["component_id"]
                assert item["materialization_source"] == "COMPONENT_EXECUTION_MAPPING_V1_2"


def test_e01_keeps_structure_only_and_no_formal_planned_nutrition():
    payload = _payload("SYN-V4-E01", severe_decline=True)
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    assert plan["energy_state"]["energy_target"]["status"] == "UNAVAILABLE"
    assert plan["energy_state"]["diet_generation_mode"] == "STRUCTURE_ONLY"
    for day in plan["diet_plan_trace"]["days"]:
        for meal in day["meals"].values():
            for item in meal["food_items"]:
                assert item["planned_nutrition"] is None
