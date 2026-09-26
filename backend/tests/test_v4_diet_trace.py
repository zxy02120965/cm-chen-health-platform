from app.v4_diet_materialization import TRACE_SCHEMA_VERSION, materialize_canonical_week_diet
from app.v4_food_data import load_v4_food_data


def _valid_week():
    return [
        {
            slot: {
                "meal_type": slot,
                "category": "vegetable",
                "dish_name": "蒜香西兰花",
                "cooking_method": "清蒸",
                "components": [{"component_id": "V001", "category": "vegetable", "dish_name": "蒜香西兰花", "portion_scale": 1.0, "cooking_method": "清蒸"}],
                "estimated_energy": 117.2,
                "estimated_protein": 8.2,
                "estimated_carbohydrate": 8.6,
                "estimated_fat": 6.2,
            }
            for slot in ("breakfast", "lunch", "snack", "dinner")
        }
        for _ in range(7)
    ]


def test_canonical_trace_has_seven_days_and_single_item_ids():
    canonical, projected = materialize_canonical_week_diet(_valid_week(), runtime=load_v4_food_data())
    assert canonical["trace_schema_version"] == TRACE_SCHEMA_VERSION == "FOOD_TRACE_V4_2"
    assert canonical["trace_materialization_status"] == "FULL"
    assert len(canonical["days"]) == 7
    ids = [item["food_item_id"] for day in canonical["days"] for meal in day["meals"].values() for item in meal["food_items"]]
    assert len(ids) == len(set(ids))
    assert all(item["food_item_type"] == "STANDARD_COMPONENT" for day in canonical["days"] for meal in day["meals"].values() for item in meal["food_items"])
    assert projected[0]["breakfast"]["components"][0]["ingredient_amount"][0]["amount"] == 200


def test_invalid_legacy_scale_is_explicit_missing_not_old_amount_fallback():
    week = _valid_week()
    week[0]["breakfast"]["components"][0]["portion_scale"] = 2.0
    canonical, projected = materialize_canonical_week_diet(week, runtime=load_v4_food_data())
    assert canonical["trace_materialization_status"] == "MISSING"
    item = canonical["days"][0]["meals"]["breakfast"]["food_items"][0]
    assert item["execution_materialization_status"] == "FAIL"
    assert projected[0]["breakfast"]["components"][0]["status"] == "MATERIALIZATION_FAIL"


def test_ai_generated_dish_off_grid_is_not_silently_materialized():
    week = _valid_week()
    week[0]["breakfast"]["components"] = [{
        "food_item_type": "AI_GENERATED_DISH",
        "generated_dish_id": "GD-001",
        "dish_name": "测试生成菜",
        "simple_method": "清蒸",
        "ingredients": [{"ingredient_id": "ING003", "algorithmic_amount": 22, "unit": "g"}],
    }]
    canonical, _ = materialize_canonical_week_diet(week, runtime=load_v4_food_data())
    item = canonical["days"][0]["meals"]["breakfast"]["food_items"][0]
    assert item["food_item_type"] == "AI_GENERATED_DISH"
    assert item["generated_dish_id"] == "GD-001"
    assert item["execution_materialization_status"] == "EXECUTABLE_SELECTION_REQUIRED"
    assert canonical["trace_materialization_status"] == "MISSING"
