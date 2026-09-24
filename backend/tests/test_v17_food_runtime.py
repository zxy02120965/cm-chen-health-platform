from app.v2_engine import _close_day_meals, _portion_options_for
import pytest

from app.v2_knowledge import OFFICIAL_FOOD_SHEET, OFFICIAL_FOOD_WORKBOOK, _load_official_food_components, structured_catalog


def test_v17_is_the_runtime_food_source_and_is_complete():
    foods = structured_catalog()["FOOD"]
    assert OFFICIAL_FOOD_WORKBOOK.exists()
    assert OFFICIAL_FOOD_SHEET == "FOOD_OFFICIAL_V1.7"
    assert len(foods) == 49
    assert len({item["component_id"] for item in foods}) == 49
    assert all(item["source_version"] == "V1.7" for item in foods)
    assert all(item["source_document"] == OFFICIAL_FOOD_WORKBOOK.name for item in foods)
    required = ("base_portion", "weight_basis", "portion_min", "portion_max", "portion_step", "energy_kcal", "protein_g", "carbohydrate_g", "fat_g")
    for item in foods:
        assert all(item.get(field) not in (None, "", []) for field in required)
        assert item["portion_min"] > 0
        assert item["portion_max"] >= item["portion_min"]
        assert item["portion_step"] > 0


def test_v17_subcategory_mapping_is_intentionally_narrow():
    foods = {item["component_id"]: item for item in structured_catalog()["FOOD"]}
    assert foods["C009"]["subcategory"] == "whole_grain"
    assert foods["C010"]["subcategory"] == "mixed_grain"
    assert foods["C006"]["subcategory"] == "unknown"
    assert all(foods[f"V{i:03d}"]["subcategory"] == "unknown" for i in range(1, 13))


def test_v17_min_max_step_are_canonical_portion_boundaries():
    options = _portion_options_for({"portion_min": 0.5, "portion_max": 2.0, "portion_step": 0.25, "portion_options": [9.0]})
    assert options == [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
    assert min(options) >= 0.5
    assert max(options) <= 2.0


def test_legacy_portion_options_and_final_fallback_remain_compatible():
    assert _portion_options_for({"portion_options": [0.5, 1.0, 1.5]}) == [0.5, 1.0, 1.5]
    assert _portion_options_for({}) == [1.0]


def test_missing_official_workbook_fails_explicitly_without_legacy_fallback(tmp_path):
    with pytest.raises(FileNotFoundError):
        _load_official_food_components(tmp_path / "missing.xlsx")


def test_vegetable_closure_strategy_remains_fixed_at_one():
    vegetable = {
        "category": "vegetable", "component_id": "V001", "name": "蔬菜",
        "ingredient_name": "蔬菜", "ingredient_amount": 200, "unit": "g",
        "raw_or_cooked_basis": "raw_weight", "estimated_energy": 80,
        "estimated_protein": 4, "estimated_carbohydrate": 10, "estimated_fat": 2,
        "portion_min": 0.5, "portion_max": 2.0, "portion_step": 0.25,
    }
    meals = {"lunch": {"components": [vegetable]}}
    _close_day_meals(1, meals, daily_energy=80, protein_target=4, carb_range=None, fat_range=None, meal_distribution={"lunch": 100})
    assert meals["lunch"]["components"][0].get("portion_scale", 1.0) == 1.0
