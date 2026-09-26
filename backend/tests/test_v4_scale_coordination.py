from copy import deepcopy

import pytest

from app.rules import assess_payload
from app.v2_engine import (
    _close_day_meals,
    _portion_options_for,
    build_v2_plan,
    candidate_test_profile,
)
from app.v4_food_data import get_allowed_component_scales, load_v4_food_data
from app.v4_food_materializer import materialize_standard_component


def _payload(patient_id="SYN-SCALE", *, weight=68):
    return {
        "patient_id": patient_id,
        "sex": "女",
        "age_years": 54,
        "q14_height": 165,
        "q15_weight": weight,
        "height_cm": 165,
        "weight_kg": weight,
        "q6_surgeryWindow": "4–8周",
        "q12_respiratorySymptoms": ["无"],
        "q28_weightChange": "稳定",
        "q29_appetite": "正常",
        "q30_intake": "正常",
        "q31_eatingDifficulties": ["无"],
        "q32_foodAllergy": ["无"],
        "q33_foodIntolerance": ["无"],
        "q34_dietPattern": ["三餐规律"],
        "q37_activityLimits": ["无"],
        "q43_metabolicConditions": ["无"],
        "q51_executionBarriers": ["无"],
    }


def test_provider_is_the_same_source_used_by_materializer():
    runtime = load_v4_food_data()
    for component_id in ("C001", "C003", "P007", "S001"):
        assert get_allowed_component_scales(component_id) == runtime.component(component_id).allowed_scales


def test_known_component_ignores_historical_global_scale_options():
    component = {
        "component_id": "C003",
        "portion_min": 0.5,
        "portion_max": 2.0,
        "portion_step": 0.25,
        "portion_options": [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
    }
    assert _portion_options_for(component) == list(get_allowed_component_scales("C003"))
    assert 0.5 not in _portion_options_for(component)
    assert 1.5 in _portion_options_for(component)


def test_component_scale_sets_are_not_shared_between_components():
    assert _portion_options_for({"component_id": "C003"}) != _portion_options_for({"component_id": "P007"})
    assert _portion_options_for({"component_id": "P007"}) == [1.0]


def test_unknown_component_does_not_receive_fabricated_default_scale():
    assert _portion_options_for({"component_id": "NOT-IN-V1-2", "portion_options": [1.0]}) == []


def test_close_day_meals_only_selects_frozen_allowed_scales():
    catalog = candidate_test_profile()["V2-FOOD-COMPONENTS"]["items"]
    by_id = {item["component_id"]: item for item in catalog}
    meals = {
        "breakfast": {"components": [deepcopy(by_id["C003"])]},
        "lunch": {"components": [deepcopy(by_id["P007"])]},
    }
    closure, _ = _close_day_meals(
        1,
        meals,
        daily_energy=1000,
        protein_target=40,
        carb_range=None,
        fat_range=None,
        meal_distribution={"breakfast": 50, "lunch": 50},
    )
    assert closure["closure_status"] in {"PASS", "WARN", "INCOMPLETE"}
    for meal in meals.values():
        for component in meal["components"]:
            scale = component.get("portion_scale", 1.0)
            assert scale in get_allowed_component_scales(component["component_id"])


def test_pending_component_can_execute_on_a_legal_scale():
    runtime = load_v4_food_data()
    pending = next(component for component in runtime.components.values() if not component.exact_nutrition_eligible)
    result = materialize_standard_component(pending.component_id, pending.allowed_scales[0], runtime=runtime)
    assert result["execution_materialization_status"] == "PASS"
    assert result["exact_nutrition_eligible"] is False
    assert result["nutrition_source_pending"] is True


def test_illegal_scale_is_rejected_before_final_materialization():
    runtime = load_v4_food_data()
    with pytest.raises(ValueError):
        materialize_standard_component("C003", 0.5, runtime=runtime)


def test_replacement_and_final_projection_use_component_specific_scales():
    payload = _payload("SYN-SCALE-PLAN", weight=68)
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    runtime = load_v4_food_data()
    for day in plan["weekly_schedule"]:
        for meal in day.get("diet", []):
            for component in meal.get("components", []):
                component_id = component.get("component_id")
                if not component_id or component_id not in runtime.components:
                    continue
                assert (component.get("portion_scale") or 1.0) in runtime.component(component_id).allowed_scales


def test_scale_coordination_diagnostic_is_present_and_has_no_invalid_final_items():
    payload = _payload("SYN-SCALE-DIAGNOSTIC", weight=68)
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    diagnostic = plan["nutrition_trace"]["v4_scale_coordination"]
    assert diagnostic["total_standard_component_items"] > 0
    assert diagnostic["items_with_valid_allowed_scale"] == diagnostic["total_standard_component_items"]
    assert diagnostic["no_legal_scale_components"] == 0
    assert diagnostic["status"] == "PASS"


def test_e01_structure_only_still_uses_legal_scales():
    payload = _payload("SYN-SCALE-E01", weight=60)
    payload["q28_weightChange"] = "不明原因下降"
    payload["q30_intake"] = "减少50%"
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    assert plan["energy_state"]["diet_generation_mode"] == "STRUCTURE_ONLY"
    runtime = load_v4_food_data()
    for day in plan["weekly_schedule"]:
        for meal in day.get("diet", []):
            for component in meal.get("components", []):
                component_id = component.get("component_id")
                if component_id in runtime.components:
                    assert (component.get("portion_scale") or 1.0) in runtime.component(component_id).allowed_scales


def test_f01_underlying_energy_state_and_scales_remain_legal():
    payload = _payload("SYN-SCALE-F01", weight=78)
    payload["q43_metabolicConditions"] = ["糖尿病", "血脂异常", "高血压", "睡眠呼吸暂停"]
    payload["q51_executionBarriers"] = ["不会操作设备"]
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    assert plan["primary_nutrition_phenotype"] == "B"
    assert plan["complexity_overlay"] == "F"
    assert plan["energy_state"]["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"
    runtime = load_v4_food_data()
    for day in plan["diet_plan_trace"]["days"]:
        for meal in day["meals"].values():
            for item in meal["food_items"]:
                if item.get("component_id") in runtime.components:
                    assert item["component_portion_scale"] in runtime.component(item["component_id"]).allowed_scales


def test_no_base_times_illegal_scale_leaks_to_patient_projection():
    payload = _payload("SYN-SCALE-LEAK", weight=68)
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    runtime = load_v4_food_data()
    for day in plan["weekly_schedule"]:
        for meal in day.get("diet", []):
            for component in meal.get("components", []):
                component_id = component.get("component_id")
                if component_id in runtime.components:
                    assert (component.get("portion_scale") or 1.0) in runtime.component(component_id).allowed_scales
