"""Deterministic nutrition recalculation for V4 executable ingredient amounts.

Only exact-eligible Ingredient Master values are allowed to contribute to
formal nutrition.  Pending sources remain structurally executable but produce
an explicit pending result rather than an estimate.
"""

from __future__ import annotations

from typing import Any, Iterable

from .v4_food_data import V4FoodRuntime


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def recalculate_ingredient_nutrition(
    ingredients: Iterable[dict[str, Any]],
    *,
    runtime: V4FoodRuntime,
    energy_state: str = "EXACT_PROVISIONAL_REVIEW",
) -> dict[str, Any]:
    """Recalculate one food item's nutrition from final executable amounts.

    Values in Ingredient Master are per 100 execution units.  This function
    deliberately refuses to combine pending-source rows with exact values.
    """
    rows = list(ingredients)
    pending: list[str] = []
    missing_values: list[str] = []
    totals = {"kcal": 0.0, "protein_g": 0.0, "carbohydrate_g": 0.0, "fat_g": 0.0}
    for row in rows:
        ingredient_id = str(row.get("ingredient_id") or "")
        try:
            ingredient = runtime.ingredient(ingredient_id)
        except Exception:
            pending.append(ingredient_id or "<missing>")
            continue
        if not ingredient.exact_nutrition_eligible:
            pending.append(ingredient_id)
            continue
        amount = _number(row.get("executable_amount"))
        if amount is None:
            missing_values.append(ingredient_id)
            continue
        nutrient_values = (
            ingredient.energy_kcal_per100g,
            ingredient.protein_g_per100g,
            ingredient.carbohydrate_g_per100g,
            ingredient.fat_g_per100g,
        )
        if any(value is None for value in nutrient_values):
            missing_values.append(ingredient_id)
            continue
        factor = amount / 100.0
        totals["kcal"] += float(ingredient.energy_kcal_per100g) * factor
        totals["protein_g"] += float(ingredient.protein_g_per100g) * factor
        totals["carbohydrate_g"] += float(ingredient.carbohydrate_g_per100g) * factor
        totals["fat_g"] += float(ingredient.fat_g_per100g) * factor

    exact = not pending and not missing_values
    mode = str(energy_state or "")
    if exact:
        status = "COMPLETED"
        planned = {key: round(value, 4) for key, value in totals.items()}
        nutrition_status = "ACTIVE_RECALCULATED"
    else:
        status = "PENDING" if mode != "STRUCTURE_ONLY" else "NOT_APPLICABLE"
        planned = None
        nutrition_status = "NEEDS_SOURCE_RECALC"
    return {
        "planned_nutrition": planned,
        "nutrition_status": nutrition_status,
        "nutrition_source_pending": not exact,
        "requires_clinician_review": not exact,
        "nutrition_recalculation_validation": {
            "status": status,
            "energy_state": mode,
            "pending_ingredient_ids": pending,
            "missing_nutrient_value_ids": missing_values,
            "used_final_executable_amounts": True,
            "used_legacy_component_estimates": False,
        },
        "nutrition_recalculation_status": status,
    }
