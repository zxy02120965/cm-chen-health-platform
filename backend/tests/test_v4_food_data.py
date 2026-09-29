from pathlib import Path

import pytest

from app.v4_food_data import ASSET_ROOT, MANIFEST_PATH, load_v4_food_data


def test_v4_runtime_uses_manifest_assets_not_legacy_outputs():
    runtime = load_v4_food_data()
    assert runtime.manifest_path == MANIFEST_PATH
    assert runtime.ingredient_source.parent == ASSET_ROOT / "data"
    assert runtime.food_source.parent == ASSET_ROOT / "data"
    assert "outputs" not in str(runtime.ingredient_source).lower()
    assert "outputs" not in str(runtime.food_source).lower()
    assert runtime.ingredient_source.name.endswith("V1.4.xlsx")
    assert runtime.food_source.name.endswith("V1.4.xlsx")


def test_v4_runtime_has_unique_component_and_ingredient_ids():
    runtime = load_v4_food_data()
    assert len(runtime.ingredients) == 48
    assert len(runtime.components) == 49
    assert len(set(runtime.ingredients)) == 48
    assert len(set(runtime.components)) == 49


def test_all_component_execution_mappings_resolve_to_ingredient_master():
    runtime = load_v4_food_data()
    for component in runtime.components.values():
        for mappings in component.mappings_by_scale.values():
            for mapping in mappings:
                assert mapping.ingredient_id in runtime.ingredients


def test_ingredient_execution_bounds_are_complete_and_valid():
    runtime = load_v4_food_data()
    for ingredient in runtime.ingredients.values():
        assert ingredient.min_amount > 0
        assert ingredient.max_amount >= ingredient.min_amount
        assert ingredient.step > 0


def test_pending_source_keeps_execution_eligibility_separate_from_exact_nutrition():
    runtime = load_v4_food_data()
    pending = next(ingredient for ingredient in runtime.ingredients.values() if not ingredient.exact_nutrition_eligible)
    assert pending.execution_eligible is True
    assert pending.exact_nutrition_eligible is False
    assert pending.nutrition_source_pending is True
    assert pending.requires_clinician_review is True


def test_formal_runtime_does_not_depend_on_v17_or_outputs():
    runtime = load_v4_food_data()
    assert Path(runtime.food_source).is_relative_to(ASSET_ROOT)
    assert Path(runtime.ingredient_source).is_relative_to(ASSET_ROOT)
