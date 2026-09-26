"""Deterministic execution materialization for the frozen V4 food assets.

This module is intentionally independent from the legacy V1.7 generator.  It
turns frozen component mappings (or a future AI dish proposal) into executable
amounts without changing the clinical source data.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from .v4_food_data import (
    IngredientRecord,
    V4FoodDataError,
    V4FoodRuntime,
    load_v4_food_data,
)


MATERIALIZATION_FAILURE = "STANDARD_COMPONENT_MATERIALIZATION_FAIL"
_EPSILON = Decimal("0.0000001")


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise V4FoodDataError(f"amount must be numeric: {value!r}") from exc


def _close(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= _EPSILON


def _grid_values(ingredient: IngredientRecord) -> list[Decimal]:
    minimum = _decimal(ingredient.min_amount)
    maximum = _decimal(ingredient.max_amount)
    step = _decimal(ingredient.step)
    values: list[Decimal] = []
    current = minimum
    while current <= maximum + _EPSILON:
        values.append(current)
        current += step
    if not values or not _close(values[-1], maximum):
        # The asset's max need not be an exact step endpoint; it remains a
        # legal explicit boundary when the workbook says so.
        values.append(maximum)
    return sorted(set(values))


def _validate_discrete_and_package(ingredient: IngredientRecord, amount: Decimal) -> bool:
    rule = (ingredient.discrete_rule or "").strip()
    if not rule:
        return True
    # Egg/unit rules in the frozen master use 50 g as the whole-unit grid.  A
    # candidate must already be on the Ingredient Master grid; this check
    # prevents fractional units even when a caller supplies a decimal amount.
    if "整枚" in rule or "半枚" in rule or "whole_unit" in rule:
        return _close(amount % Decimal("50"), Decimal("0"))
    # Package/net-content rules are represented by their explicit min/max/step
    # grid in the manifest-selected Ingredient Master.  Do not invent package sizes here.
    if "包装" in rule or "净含量" in rule:
        return True
    return True


def validate_execution_amount(ingredient: IngredientRecord, amount: Any) -> bool:
    """Return whether *amount* is legal under the frozen execution grid."""
    candidate = _decimal(amount)
    minimum = _decimal(ingredient.min_amount)
    maximum = _decimal(ingredient.max_amount)
    step = _decimal(ingredient.step)
    if candidate < minimum - _EPSILON or candidate > maximum + _EPSILON:
        return False
    ratio = (candidate - minimum) / step
    if not _close(ratio, ratio.to_integral_value()):
        return False
    return _validate_discrete_and_package(ingredient, candidate)


def _legal_candidates(ingredient: IngredientRecord, algorithmic_amount: Any) -> tuple[Decimal | None, Decimal | None]:
    candidate = _decimal(algorithmic_amount)
    minimum = _decimal(ingredient.min_amount)
    maximum = _decimal(ingredient.max_amount)
    if candidate < minimum - _EPSILON or candidate > maximum + _EPSILON:
        raise V4FoodDataError(f"AI_GENERATED_DISH execution failed: algorithmic amount outside bounds for {ingredient.ingredient_id}")
    values = _grid_values(ingredient)
    in_range = [
        value for value in values
        if minimum <= value <= maximum
        and validate_execution_amount(ingredient, value)
    ]
    if not in_range:
        raise V4FoodDataError(f"no legal execution amount for {ingredient.ingredient_id}")
    lower = max((value for value in in_range if value < candidate), default=None)
    upper = min((value for value in in_range if value > candidate), default=None)
    return lower, upper


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def _recalculation_result(*, changed: bool, energy_state: str, recalculated: bool) -> dict[str, Any]:
    if not changed:
        status = "NOT_APPLICABLE"
    elif recalculated:
        status = "COMPLETED"
    elif energy_state == "STRUCTURE_ONLY":
        status = "NOT_APPLICABLE"
    else:
        status = "PENDING"
    return {
        "algorithmic_amounts_changed": changed,
        "nutrition_recalculation_required": changed,
        "nutrition_recalculation_status": status,
    }


def _ingredient_or_fail(runtime: V4FoodRuntime, ingredient_id: str) -> IngredientRecord:
    ingredient = runtime.ingredient(ingredient_id)
    if not ingredient.execution_eligible:
        raise V4FoodDataError(
            f"{MATERIALIZATION_FAILURE}: ingredient {ingredient_id} is not execution eligible"
        )
    return ingredient


def materialize_standard_component(
    component_id: str,
    component_portion_scale: Any,
    *,
    energy_state: str = "EXACT_PROVISIONAL_REVIEW",
    nutrition_recalculated: bool = False,
    runtime: V4FoodRuntime | None = None,
) -> dict[str, Any]:
    """Materialize one frozen STANDARD_COMPONENT at an allowed scale."""
    runtime = runtime or load_v4_food_data()
    component = runtime.component(component_id)
    try:
        scale = float(component_portion_scale)
    except (TypeError, ValueError):
        raise V4FoodDataError(f"{MATERIALIZATION_FAILURE}: invalid scale") from None
    if not component.execution_eligible:
        raise V4FoodDataError(f"{MATERIALIZATION_FAILURE}: component {component_id} is not execution eligible")
    if scale not in component.allowed_scales:
        raise V4FoodDataError(f"{MATERIALIZATION_FAILURE}: scale {scale} is not allowed for {component_id}")
    mappings = component.mappings_by_scale.get(scale, ())
    if not mappings:
        raise V4FoodDataError(f"{MATERIALIZATION_FAILURE}: missing mapping for {component_id}/{scale}")

    ingredients: list[dict[str, Any]] = []
    changed = False
    for mapping in mappings:
        ingredient = _ingredient_or_fail(runtime, mapping.ingredient_id)
        executable = _decimal(mapping.executable_amount)
        if mapping.unit != ingredient.unit or not validate_execution_amount(ingredient, executable):
            raise V4FoodDataError(
                f"{MATERIALIZATION_FAILURE}: illegal mapping for {component_id}/{mapping.ingredient_id}"
            )
        algorithmic = _decimal(mapping.algorithmic_amount)
        changed = changed or not _close(algorithmic, executable)
        ingredients.append({
            "ingredient_id": mapping.ingredient_id,
            "ingredient_name": mapping.ingredient_name,
            "algorithmic_amount": _number(algorithmic),
            "algorithmic_amount_patient_visible": False,
            "executable_amount": _number(executable),
            "executable_amount_patient_visible": True,
            "unit": mapping.unit,
            "execution_rule_status": mapping.execution_rule_status,
            "execution_eligible": ingredient.execution_eligible,
            "exact_nutrition_eligible": ingredient.exact_nutrition_eligible,
            "nutrition_source_pending": ingredient.nutrition_source_pending,
            "requires_clinician_review": ingredient.requires_clinician_review,
        })

    result = {
        "food_item_type": "STANDARD_COMPONENT",
        "component_id": component.component_id,
        "component_portion_scale": scale,
        "ingredients": ingredients,
        "execution_materialization_status": "PASS",
        "exact_nutrition_eligible": component.exact_nutrition_eligible,
        "nutrition_status": component.nutrition_status,
        "nutrition_source_pending": component.nutrition_source_pending,
        "requires_clinician_review": component.requires_clinician_review,
        "standard_component_materialization": {
            "selected_scale_in_allowed_component_scales": True,
            "mapped_ingredient_amounts_loaded": True,
            "patient_amounts_equal_mapped_executable_amounts": True,
            "execution_materialization_status": "PASS",
            "exact_nutrition_eligible": component.exact_nutrition_eligible,
            "nutrition_status": component.nutrition_status,
            "nutrition_source_pending": component.nutrition_source_pending,
            "requires_clinician_review": component.requires_clinician_review,
            "status": "PASS",
        },
    }
    result["portion_materialization_result"] = _recalculation_result(
        changed=changed,
        energy_state=energy_state,
        recalculated=nutrition_recalculated,
    )
    return result


def materialize_ai_generated_dish(
    proposed_ingredients: Iterable[Mapping[str, Any]],
    *,
    energy_state: str = "EXACT_PROVISIONAL_REVIEW",
    nutrition_recalculated: bool = False,
    runtime: V4FoodRuntime | None = None,
) -> dict[str, Any]:
    """Validate and execute a future AI dish proposal on the frozen grid."""
    runtime = runtime or load_v4_food_data()
    output: list[dict[str, Any]] = []
    changed = False
    for proposal in proposed_ingredients:
        ingredient_id = str(proposal.get("ingredient_id") or "")
        if not ingredient_id:
            raise V4FoodDataError("AI_GENERATED_DISH execution failed: missing ingredient_id")
        ingredient = _ingredient_or_fail(runtime, ingredient_id)
        unit = str(proposal.get("unit") or "")
        if unit != ingredient.unit:
            raise V4FoodDataError(f"AI_GENERATED_DISH execution failed: unit mismatch for {ingredient_id}")
        algorithmic = _decimal(proposal.get("algorithmic_amount"))
        if validate_execution_amount(ingredient, algorithmic):
            executable = algorithmic
            execution_status = "PASS"
            lower = upper = None
        else:
            lower, upper = _legal_candidates(ingredient, algorithmic)
            executable = None
            execution_status = "EXECUTABLE_SELECTION_REQUIRED"
        output.append({
            "ingredient_id": ingredient.ingredient_id,
            "ingredient_name": ingredient.ingredient_name,
            "algorithmic_amount": _number(algorithmic),
            "algorithmic_amount_patient_visible": False,
            "executable_amount": None if executable is None else _number(executable),
            "executable_amount_patient_visible": executable is not None,
            "unit": ingredient.unit,
            "candidate_min": ingredient.min_amount,
            "candidate_max": ingredient.max_amount,
            "candidate_step": ingredient.step,
            "execution_rule_status": execution_status,
            "lower_legal_candidate": None if lower is None else _number(lower),
            "upper_legal_candidate": None if upper is None else _number(upper),
            "execution_eligible": ingredient.execution_eligible,
            "exact_nutrition_eligible": ingredient.exact_nutrition_eligible,
            "nutrition_source_pending": ingredient.nutrition_source_pending,
            "requires_clinician_review": ingredient.requires_clinician_review,
        })
        changed = changed or executable is not None and not _close(algorithmic, executable)
    selection_required = any(item["execution_rule_status"] == "EXECUTABLE_SELECTION_REQUIRED" for item in output)
    result = {
        "food_item_type": "AI_GENERATED_DISH",
        "ingredients": output,
        "ingredient_execution_validation": output,
        "execution_materialization_status": "EXECUTABLE_SELECTION_REQUIRED" if selection_required else "PASS",
    }
    result["portion_materialization_result"] = _recalculation_result(
        changed=changed,
        energy_state=energy_state,
        recalculated=nutrition_recalculated,
    )
    return result
