import pytest

from app.v4_food_data import V4FoodDataError, load_v4_food_data
from app.v4_food_materializer import (
    materialize_ai_generated_dish,
    materialize_standard_component,
    validate_execution_amount,
)


@pytest.fixture(scope="module")
def runtime():
    return load_v4_food_data()


def _active_component(runtime):
    return next(component for component in runtime.components.values() if component.active)


def test_standard_component_uses_frozen_execution_mapping(runtime):
    component = _active_component(runtime)
    scale = next(scale for scale in component.allowed_scales if any(
        mapping.algorithmic_amount != mapping.executable_amount
        for mapping in component.mappings_by_scale[scale]
    ))
    result = materialize_standard_component(component.component_id, scale, runtime=runtime)
    assert result["food_item_type"] == "STANDARD_COMPONENT"
    assert result["standard_component_materialization"]["status"] == "PASS"
    for actual, expected in zip(result["ingredients"], component.mappings_by_scale[scale]):
        assert actual["executable_amount"] == expected.executable_amount
        assert actual["algorithmic_amount_patient_visible"] is False
        assert actual["executable_amount_patient_visible"] is True
    assert result["portion_materialization_result"]["algorithmic_amounts_changed"] is True


def test_standard_component_rejects_invalid_scale_and_missing_component(runtime):
    component = _active_component(runtime)
    invalid = max(component.allowed_scales) + 0.25
    with pytest.raises(V4FoodDataError, match="STANDARD_COMPONENT_MATERIALIZATION_FAIL"):
        materialize_standard_component(component.component_id, invalid, runtime=runtime)
    with pytest.raises(V4FoodDataError, match="unknown component_id"):
        materialize_standard_component("DOES_NOT_EXIST", 1.0, runtime=runtime)


def test_pending_component_is_execution_valid_but_not_exact_eligible(runtime):
    component = next(component for component in runtime.components.values() if not component.active)
    result = materialize_standard_component(component.component_id, component.allowed_scales[0], runtime=runtime)
    assert result["standard_component_materialization"]["execution_materialization_status"] == "PASS"
    assert result["standard_component_materialization"]["exact_nutrition_eligible"] is False
    assert result["standard_component_materialization"]["nutrition_source_pending"] is True
    assert result["standard_component_materialization"]["requires_clinician_review"] is True
    assert all(item["execution_eligible"] for item in result["ingredients"])
    assert all(item["exact_nutrition_eligible"] is False for item in result["ingredients"])


def test_execution_grid_min_max_step_and_discrete_rules(runtime):
    ingredient = runtime.ingredient("ING003")
    assert validate_execution_amount(ingredient, ingredient.min_amount)
    assert validate_execution_amount(ingredient, ingredient.max_amount)
    assert validate_execution_amount(ingredient, 20)
    assert not validate_execution_amount(ingredient, 22)
    assert not validate_execution_amount(ingredient, ingredient.max_amount + ingredient.step)

    egg = runtime.ingredient("ING019")
    assert validate_execution_amount(egg, 50)
    assert validate_execution_amount(egg, 100)
    assert not validate_execution_amount(egg, 75)

    package = runtime.ingredient("ING022")
    assert package.execution_eligible is True
    assert package.exact_nutrition_eligible is True
    assert validate_execution_amount(package, 150)
    assert not validate_execution_amount(package, 125)


def test_ai_generated_dish_materializes_to_legal_grid(runtime):
    result = materialize_ai_generated_dish(
        [{"ingredient_id": "ING003", "algorithmic_amount": 22, "unit": "g"}],
        runtime=runtime,
    )
    item = result["ingredients"][0]
    assert item["algorithmic_amount"] == 22
    assert item["executable_amount"] is None
    assert item["algorithmic_amount_patient_visible"] is False
    assert item["executable_amount_patient_visible"] is False
    assert item["execution_rule_status"] == "EXECUTABLE_SELECTION_REQUIRED"
    assert item["lower_legal_candidate"] == 20
    assert item["upper_legal_candidate"] == 25
    assert result["execution_materialization_status"] == "EXECUTABLE_SELECTION_REQUIRED"


def test_ai_generated_dish_legal_candidate_passes_without_nearest_selection(runtime):
    result = materialize_ai_generated_dish(
        [{"ingredient_id": "ING003", "algorithmic_amount": 20, "unit": "g"}],
        runtime=runtime,
    )
    item = result["ingredients"][0]
    assert result["execution_materialization_status"] == "PASS"
    assert item["executable_amount"] == 20
    assert item["execution_rule_status"] == "PASS"
    assert item["executable_amount_patient_visible"] is True


def test_ai_generated_dish_rejects_unit_or_inactive_ingredient(runtime):
    with pytest.raises(V4FoodDataError, match="unit mismatch"):
        materialize_ai_generated_dish(
            [{"ingredient_id": "ING003", "algorithmic_amount": 20, "unit": "ml"}],
            runtime=runtime,
        )
    pending = next(ingredient for ingredient in runtime.ingredients.values() if not ingredient.active)
    pending_result = materialize_ai_generated_dish(
        [{"ingredient_id": pending.ingredient_id, "algorithmic_amount": pending.min_amount, "unit": pending.unit}],
        runtime=runtime,
    )
    assert pending_result["ingredients"][0]["execution_eligible"] is True
    assert pending_result["ingredients"][0]["exact_nutrition_eligible"] is False
    with pytest.raises(V4FoodDataError, match="outside bounds"):
        materialize_ai_generated_dish(
            [{"ingredient_id": "ING003", "algorithmic_amount": 1000, "unit": "g"}],
            runtime=runtime,
        )


def test_nutrition_recalculation_state_semantics(runtime):
    component = _active_component(runtime)
    changed_scale = next(scale for scale in component.allowed_scales if any(
        mapping.algorithmic_amount != mapping.executable_amount
        for mapping in component.mappings_by_scale[scale]
    ))
    active = materialize_standard_component(
        component.component_id,
        changed_scale,
        energy_state="EXACT_ACTIVE",
        runtime=runtime,
    )
    assert active["portion_materialization_result"]["nutrition_recalculation_status"] == "PENDING"
    provisional = materialize_standard_component(
        component.component_id,
        changed_scale,
        energy_state="EXACT_PROVISIONAL_REVIEW",
        runtime=runtime,
    )
    assert provisional["portion_materialization_result"]["nutrition_recalculation_status"] == "PENDING"
    structure = materialize_standard_component(
        component.component_id,
        changed_scale,
        energy_state="STRUCTURE_ONLY",
        runtime=runtime,
    )
    assert structure["portion_materialization_result"]["nutrition_recalculation_required"] is True
    assert structure["portion_materialization_result"]["nutrition_recalculation_status"] == "NOT_APPLICABLE"
    completed = materialize_standard_component(
        component.component_id,
        changed_scale,
        energy_state="EXACT_ACTIVE",
        nutrition_recalculated=True,
        runtime=runtime,
    )
    assert completed["portion_materialization_result"]["nutrition_recalculation_status"] == "COMPLETED"
