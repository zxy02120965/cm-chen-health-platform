"""Regression coverage for exact snack coverage under egg allergy."""

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


def _egg_allergy_payload() -> dict:
    return {
        "patient_id": "P003-EGG-ALLERGY",
        "sex": "女",
        "age_years": 54,
        "q14_height": 165,
        "q15_weight": 68,
        "height_cm": 165,
        "weight_kg": 68,
        "q6_surgeryWindow": "4–8周",
        "q12_respiratorySymptoms": ["无"],
        "q28_weightChange": "稳定",
        "q29_appetite": "正常",
        "q30_intake": "正常",
        "q31_eatingDifficulties": ["无明显困难"],
        "q32_foodAllergy": ["鸡蛋"],
        "q33_foodIntolerance": ["无"],
        "q34_dietPattern": ["三餐规律"],
        "q37_activityLimitations": ["无明显限制"],
        "q43_metabolicConditions": ["糖尿病"],
        "q51_executionBarriers": ["无"],
    }


def test_exact_egg_free_snack_candidates_are_available_after_s009_filter():
    profile = candidate_test_profile()
    snacks = [
        item for item in profile["V2-FOOD-COMPONENTS"]["items"]
        if item.get("category") == "snack"
        and item.get("exact_nutrition_eligible") is True
        and item.get("component_id") != "S009"
        and not any("蛋" in str(value) for value in (item.get("ingredients") or []))
    ]
    assert {item["component_id"] for item in snacks} >= {"S002", "S005", "S010"}
    assert len(snacks) >= 2


def test_egg_allergy_week_uses_only_exact_nutrition_safe_snacks():
    payload = _egg_allergy_payload()
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    assert plan["diet_plan"]["nutrition_plan_validation"] == "PASS"
    assert plan["validation_result"]["content_validation"] == "PASS"
    assert all(day["nutrition_closure"]["closure_status"] == "PASS" for day in plan["weekly_schedule"])

    selected_ids = []
    for day in plan["canonical_week_diet"]["days"]:
        snack = day["meals"]["snack"]
        for item in snack.get("food_items") or []:
            selected_ids.append(item["component_id"])
            assert item["component_id"] != "S009"
            assert item["planned_nutrition"] is not None
            assert item["nutrition_status"] == "ACTIVE_RECALCULATED"
            assert all("蛋" not in str(ingredient.get("ingredient_name")) for ingredient in item.get("ingredients") or [])
    assert len(selected_ids) == 7
    assert set(selected_ids) <= {"S002", "S005", "S010"}
