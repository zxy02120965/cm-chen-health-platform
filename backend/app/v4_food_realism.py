"""Deterministic meal-realism projection for the frozen FOOD contract.

This module only evaluates the final selected meal structure.  It does not
select components, change amounts, or create a publication blocker.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _component_category(component: dict[str, Any]) -> str:
    return str(component.get("category") or "").strip().lower()


def assess_meal_realism(
    meal_slot: str,
    components: list[dict[str, Any]],
    *,
    complexity_overlay: str | None = None,
) -> dict[str, Any]:
    """Evaluate only the meal architectures defined by FOOD V4.2.4."""
    slot = str(meal_slot or "").lower()
    categories = [_component_category(item) for item in components]
    staple_count = categories.count("staple")
    protein_count = categories.count("protein")
    vegetable_count = categories.count("vegetable")
    snack_count = categories.count("snack")
    reasons: list[str] = []

    if slot == "breakfast":
        coherent = staple_count == 1 and protein_count >= 1 and protein_count <= 1
        if coherent:
            reasons.append("BREAKFAST_STAPLE_PLUS_PROTEIN")
        else:
            reasons.append("BREAKFAST_ARCHITECTURE_REVIEW")
        unnecessary_fragmentation = protein_count > 1
        redundant_side_dishes = vegetable_count > 1
    elif slot in {"lunch", "dinner"}:
        coherent = staple_count == 1 and protein_count >= 1 and vegetable_count >= 1 and vegetable_count <= 2
        reasons.append("MAIN_MEAL_STAPLE_PROTEIN_VEGETABLES" if coherent else "MAIN_MEAL_ARCHITECTURE_REVIEW")
        unnecessary_fragmentation = protein_count > 1 or vegetable_count > 2
        redundant_side_dishes = vegetable_count > 2
    elif slot == "snack":
        coherent = snack_count == 1 and len(components) == 1
        reasons.append("SNACK_SINGLE_FUNCTION" if coherent else "SNACK_ARCHITECTURE_REVIEW")
        unnecessary_fragmentation = len(components) > 1
        redundant_side_dishes = False
    else:
        coherent = bool(components)
        reasons.append("UNSPECIFIED_MEAL_SLOT" if not coherent else "COMPONENTS_PRESENT")
        unnecessary_fragmentation = False
        redundant_side_dishes = False

    if complexity_overlay == "F":
        burden = "MODERATE" if coherent else "HIGH"
        reasons.append("F_COMPLEXITY_CONTEXT")
    else:
        burden = "LOW" if coherent else "MODERATE"
    validation = {
        "status": "PASS" if coherent and not unnecessary_fragmentation and not redundant_side_dishes else "REVIEW",
        "reason_codes": reasons,
    }
    return {
        "primary_protein_item_count": protein_count,
        "secondary_protein_item_present": protein_count > 1,
        "secondary_protein_rationale": None,
        "protein_patch_for_numeric_closure": False,
        "coherent_meal_structure": coherent,
        "coherent_meal_structure_reason_codes": reasons[:],
        "unnecessary_fragmentation": unnecessary_fragmentation,
        "unnecessary_fragmentation_reason_codes": ["MULTIPLE_PRIMARY_PROTEINS" if protein_count > 1 else "EXCESS_COMPONENT_FRAGMENTATION"] if unnecessary_fragmentation else [],
        "redundant_side_dishes": redundant_side_dishes,
        "redundant_side_dishes_reason_codes": ["REDUNDANT_VEGETABLE_SIDES"] if redundant_side_dishes else [],
        "household_execution_burden": burden,
        "meal_realism_validation": validation,
    }


def annotate_week_meal_realism(
    rotating_meals: list[dict[str, dict[str, Any]]],
    *,
    complexity_overlay: str | None = None,
) -> dict[str, Any]:
    """Attach meal realism to every final legacy meal and return a summary."""
    records: list[dict[str, Any]] = []
    for day_index, day in enumerate(rotating_meals, start=1):
        for slot in ("breakfast", "lunch", "snack", "dinner"):
            meal = day.get(slot)
            if not isinstance(meal, dict):
                continue
            realism = assess_meal_realism(slot, list(meal.get("components") or []), complexity_overlay=complexity_overlay)
            meal["meal_realism"] = deepcopy(realism)
            records.append({"day": day_index, "meal": slot, **deepcopy(realism)})
    failures = [record for record in records if record["meal_realism_validation"].get("status") != "PASS"]
    return {
        "status": "PASS" if not failures else "REVIEW",
        "all_meals_have_realism_check": len(records) == sum(1 for day in rotating_meals for slot in ("breakfast", "lunch", "snack", "dinner") if isinstance(day.get(slot), dict)),
        "all_meals_coherent": all(record["coherent_meal_structure"] is True for record in records),
        "no_unnecessary_fragmentation": all(record["unnecessary_fragmentation"] is False for record in records),
        "no_unjustified_numeric_protein_patches": all(not record.get("protein_patch_for_numeric_closure") for record in records),
        "meals": records,
    }


def validate_meal_realism_root(root: dict[str, Any]) -> dict[str, Any]:
    """Validate the fields physically stored in the canonical root."""
    days = root.get("days") or []
    meals = [meal for day in days for meal in (day.get("meals") or {}).values()]
    checks = {
        "all_meals_have_realism_check": all(isinstance(meal.get("meal_realism"), dict) for meal in meals),
        "all_meals_coherent": all((meal.get("meal_realism") or {}).get("coherent_meal_structure") is True for meal in meals),
        "no_unnecessary_fragmentation": all((meal.get("meal_realism") or {}).get("unnecessary_fragmentation") is False for meal in meals),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", **checks}
