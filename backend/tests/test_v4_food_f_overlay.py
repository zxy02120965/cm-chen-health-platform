"""Phase 5B-5 FOOD complexity overlay contract tests."""

import json
from pathlib import Path

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "v4_contract"


def _plan(fixture_id: str):
    fixture = json.loads((FIXTURE_DIR / f"SYN-{fixture_id}.json").read_text(encoding="utf-8"))
    payload = fixture["assessment_payload"]
    return build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())


def test_f_food_overlay_captures_base_and_final_and_preserves_b():
    plan = _plan("F01")
    trace = plan["diet_plan_trace"]
    overlay = trace["generation_context"]["food_complexity_overlay"]

    assert plan["primary_nutrition_phenotype"] == "B"
    assert plan["complexity_overlay"] == "F"
    assert overlay["overlay"] == "F"
    assert overlay["applied"] is True
    assert overlay["before"]["weekly_unique_menu_patterns"] == 7
    assert overlay["after"]["weekly_unique_menu_patterns"] <= 3
    assert overlay["strategies"]["SIMPLIFY_BREAKFAST"]["status"] == "APPLIED"
    assert overlay["preserved"]["underlying_primary_phenotype"] == "B"
    assert overlay["preserved"]["energy_direction"] is True


def test_f_food_breakfast_simplification_is_auditable_and_closes():
    plan = _plan("F01")
    trace = plan["diet_plan_trace"]
    overlay = trace["generation_context"]["food_complexity_overlay"]

    assert overlay["before"]["breakfast_component_counts"] == [3] * 7
    assert overlay["after"]["breakfast_component_counts"] == [2] * 7
    assert all(
        len(day["meals"]["breakfast"]["food_items"]) == 2
        for day in trace["days"]
    )
    assert all(item["closure_status"] == "PASS" for item in plan["nutrition_trace"]["closure_result"])
    assert plan["validation_result"]["nutrition_plan_validation"] == "PASS"
    assert overlay["preserved"]["nutrition_closure"] is True


def test_f_food_overlay_keeps_execution_grid_and_projection_consistent():
    plan = _plan("F01")
    trace = plan["diet_plan_trace"]
    assert trace["trace_materialization_status"] == "FULL"
    assert trace["trace_validation"]["status"] == "PASS"
    assert trace["trace_validation"]["all_patient_visible_amounts_are_executable"] is True
    assert trace["generation_context"]["food_complexity_overlay"]["preserved"]["executable_amounts_legal"] is True

    for day_index, day in enumerate(trace["days"]):
        projected = plan["weekly_schedule"][day_index]["diet"]
        for meal_name, meal in day["meals"].items():
            root_ids = [item["component_id"] for item in meal["food_items"]]
            projected_meal = next(item for item in projected if item.get("meal_type") == meal_name)
            projected_ids = [item["component_id"] for item in projected_meal.get("components", [])]
            assert projected_ids == root_ids


def test_non_f_food_plans_do_not_enter_overlay():
    for fixture_id in ("A01", "B01", "C01", "D01", "E01"):
        plan = _plan(fixture_id)
        overlay = plan["diet_plan_trace"]["generation_context"]["food_complexity_overlay"]
        assert overlay["overlay"] == "none"
        assert overlay["applied"] is False
        assert plan["complexity_overlay"] != "F"


def test_f_overlay_is_deterministic_and_does_not_touch_exercise_counts():
    first = _plan("F01")
    second = _plan("F01")
    assert first["diet_plan_trace"] == second["diet_plan_trace"]
    assert first["diet_plan_trace"]["generation_context"]["food_complexity_overlay"]["after"]["weekly_unique_menu_patterns"] == 3
    assert first["exercise_plan_trace"]["weekly_schedule_derived"] == {
        "formal_aerobic_days_actual": 3,
        "functional_activity_days_actual": 0,
        "resistance_days_actual": 2,
        "recovery_days_actual": 0,
        "flexibility_days_actual": 2,
    }
