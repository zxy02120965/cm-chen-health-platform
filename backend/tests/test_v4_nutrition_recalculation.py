from app.v4_food_data import load_v4_food_data
from app.v4_food_materializer import materialize_standard_component
from app.v4_nutrition_recalculation import recalculate_ingredient_nutrition


def test_active_ingredient_values_recalculate_from_executable_amounts():
    runtime = load_v4_food_data()
    materialized = materialize_standard_component("V001", 1.0, runtime=runtime)
    result = recalculate_ingredient_nutrition(materialized["ingredients"], runtime=runtime)
    assert result["nutrition_recalculation_status"] == "COMPLETED"
    assert result["nutrition_status"] == "ACTIVE_RECALCULATED"
    assert result["nutrition_recalculation_validation"]["used_final_executable_amounts"] is True
    assert result["nutrition_recalculation_validation"]["used_legacy_component_estimates"] is False
    assert result["planned_nutrition"]["kcal"] == 117.2


def test_pending_source_never_contributes_formal_exact_nutrition():
    runtime = load_v4_food_data()
    component = next(item for item in runtime.components.values() if not item.exact_nutrition_eligible)
    materialized = materialize_standard_component(component.component_id, component.allowed_scales[0], runtime=runtime)
    result = recalculate_ingredient_nutrition(materialized["ingredients"], runtime=runtime)
    assert result["planned_nutrition"] is None
    assert result["nutrition_status"] == "NEEDS_SOURCE_RECALC"
    assert result["nutrition_recalculation_status"] == "PENDING"
    assert result["nutrition_recalculation_validation"]["pending_ingredient_ids"]


def test_structure_only_keeps_amount_change_fact_without_planned_nutrition():
    runtime = load_v4_food_data()
    component = next(item for item in runtime.components.values() if any(
        mapping.algorithmic_amount != mapping.executable_amount
        for entries in item.mappings_by_scale.values() for mapping in entries
    ))
    scale = next(scale for scale, entries in component.mappings_by_scale.items() if any(
        mapping.algorithmic_amount != mapping.executable_amount for mapping in entries
    ))
    materialized = materialize_standard_component(component.component_id, scale, energy_state="STRUCTURE_ONLY", runtime=runtime)
    assert materialized["portion_materialization_result"]["algorithmic_amounts_changed"] is True
    assert materialized["portion_materialization_result"]["nutrition_recalculation_required"] is True
    assert materialized["portion_materialization_result"]["nutrition_recalculation_status"] == "NOT_APPLICABLE"
