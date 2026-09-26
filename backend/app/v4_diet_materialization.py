"""Canonical week-level V4 diet materialization and compatibility projections."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .v4_food_data import V4FoodDataError, V4FoodRuntime, load_v4_food_data
from .v4_food_materializer import materialize_ai_generated_dish, materialize_standard_component
from .v4_nutrition_recalculation import recalculate_ingredient_nutrition


TRACE_SCHEMA_VERSION = "FOOD_TRACE_V4_2"
MATERIALIZATION_SOURCE = "COMPONENT_EXECUTION_MAPPING_V1_2"


def _mode(energy_state: dict[str, Any] | None) -> str:
    state = energy_state or {}
    return str(state.get("diet_generation_mode") or "EXACT_PROVISIONAL_REVIEW")


def _failure_item(day: int, meal: str, index: int, legacy: dict[str, Any], error: Exception) -> dict[str, Any]:
    return {
        "food_item_id": f"D{day}-{meal}-{index + 1}-{legacy.get('component_id') or 'UNKNOWN'}",
        "food_item_type": "STANDARD_COMPONENT",
        "component_id": legacy.get("component_id"),
        "component_portion_scale": legacy.get("portion_scale"),
        "category": legacy.get("category"),
        "dish_name": legacy.get("dish_name") or legacy.get("meal_name"),
        "ingredients": [],
        "simple_method": legacy.get("cooking_method") or legacy.get("brief_instructions"),
        "simple_method_status": "NEEDS_REVIEW" if not (legacy.get("cooking_method") or legacy.get("brief_instructions")) else "AVAILABLE",
        "materialization_source": MATERIALIZATION_SOURCE,
        "nutrition_status": "NEEDS_SOURCE_RECALC",
        "planned_nutrition": None,
        "nutrition_recalculation_status": "PENDING",
        "nutrition_recalculation_validation": {"status": "FAIL", "reason": str(error)},
        "execution_materialization_status": "FAIL",
        "materialization_error": str(error),
        "source_version": "V1.2",
        "review_flags": ["MATERIALIZATION_FAIL"],
    }


def _materialize_item(day: int, meal: str, index: int, legacy: dict[str, Any], *, energy_state: dict[str, Any], runtime: V4FoodRuntime) -> dict[str, Any]:
    if legacy.get("food_item_type") == "AI_GENERATED_DISH":
        proposed = legacy.get("ingredients") or legacy.get("proposed_ingredients") or []
        try:
            result = materialize_ai_generated_dish(proposed, energy_state=_mode(energy_state), runtime=runtime)
        except (V4FoodDataError, KeyError, ValueError) as exc:
            return {
                "food_item_id": f"D{day}-{meal}-{index + 1}-{legacy.get('generated_dish_id') or 'AI'}",
                "food_item_type": "AI_GENERATED_DISH",
                "generated_dish_id": legacy.get("generated_dish_id"),
                "component_id": None,
                "dish_name": legacy.get("dish_name") or legacy.get("meal_name"),
                "ingredients": [],
                "simple_method": legacy.get("simple_method"),
                "simple_method_status": "NEEDS_REVIEW",
                "materialization_source": "AI_GENERATED_DISH_EXECUTION_GRID",
                "nutrition_status": "NEEDS_SOURCE_RECALC",
                "planned_nutrition": None,
                "nutrition_recalculation_status": "PENDING",
                "nutrition_recalculation_validation": {"status": "FAIL", "reason": str(exc)},
                "execution_materialization_status": "FAIL",
                "materialization_error": str(exc),
                "source_version": "V1.2",
                "review_flags": ["MATERIALIZATION_FAIL"],
            }
        ingredients = result.get("ingredients") or []
        nutrition = recalculate_ingredient_nutrition(ingredients, runtime=runtime, energy_state=_mode(energy_state))
        return {
            "food_item_id": f"D{day}-{meal}-{index + 1}-{legacy.get('generated_dish_id') or 'AI'}",
            "food_item_type": "AI_GENERATED_DISH",
            "generated_dish_id": legacy.get("generated_dish_id"),
            "component_id": None,
            "dish_name": legacy.get("dish_name") or legacy.get("meal_name") or legacy.get("generated_dish_id"),
            "ingredients": ingredients,
            "simple_method": legacy.get("simple_method"),
            "simple_method_status": "AVAILABLE" if legacy.get("simple_method") else "NEEDS_REVIEW",
            "materialization_source": "AI_GENERATED_DISH_EXECUTION_GRID",
            "nutrition_status": nutrition["nutrition_status"],
            "planned_nutrition": nutrition["planned_nutrition"] if _mode(energy_state) != "STRUCTURE_ONLY" else None,
            "nutrition_recalculation_status": nutrition["nutrition_recalculation_status"],
            "nutrition_recalculation_validation": nutrition["nutrition_recalculation_validation"],
            "execution_materialization_status": result["execution_materialization_status"],
            "source_version": "V1.2",
            "review_flags": ["SIMPLE_METHOD_REVIEW"] if not legacy.get("simple_method") else [],
        }
    component_id = str(legacy.get("component_id") or "")
    scale = legacy.get("portion_scale")
    if scale in (None, ""):
        scale = 1.0
    try:
        result = materialize_standard_component(component_id, scale, energy_state=_mode(energy_state), runtime=runtime)
    except (V4FoodDataError, KeyError, ValueError) as exc:
        return _failure_item(day, meal, index, legacy, exc)
    nutrition = recalculate_ingredient_nutrition(result["ingredients"], runtime=runtime, energy_state=_mode(energy_state))
    method = legacy.get("cooking_method") or legacy.get("brief_instructions")
    item = {
        "food_item_id": f"D{day}-{meal}-{index + 1}-{component_id}",
        "food_item_type": "STANDARD_COMPONENT",
        "component_id": component_id,
        "component_portion_scale": float(scale),
        "category": legacy.get("category"),
        "dish_name": legacy.get("dish_name") or legacy.get("meal_name") or component_id,
        "ingredients": result["ingredients"],
        "simple_method": method,
        "simple_method_status": "AVAILABLE" if method else "NEEDS_REVIEW",
        "materialization_source": MATERIALIZATION_SOURCE,
        "nutrition_status": nutrition["nutrition_status"],
        "planned_nutrition": nutrition["planned_nutrition"] if _mode(energy_state) != "STRUCTURE_ONLY" else None,
        "nutrition_recalculation_status": nutrition["nutrition_recalculation_status"],
        "nutrition_recalculation_validation": nutrition["nutrition_recalculation_validation"],
        "execution_materialization_status": result["execution_materialization_status"],
        "source_version": "V1.2",
        "review_flags": ["SIMPLE_METHOD_REVIEW"] if not method else [],
    }
    if _mode(energy_state) == "STRUCTURE_ONLY":
        item["nutrition_status"] = "STRUCTURE_ONLY"
    return item


def _legacy_projection(canonical_meal: dict[str, Any], legacy_meal: dict[str, Any]) -> dict[str, Any]:
    items = canonical_meal.get("food_items") or []
    components: list[dict[str, Any]] = []
    for item in items:
        planned = item.get("planned_nutrition") or {}
        ingredients = deepcopy(item.get("ingredients") or [])
        components.append({
            "meal_type": legacy_meal.get("meal_type"),
            "category": item.get("category") or legacy_meal.get("category"),
            "meal_name": item.get("dish_name"),
            "dish_name": item.get("dish_name"),
            "component_id": item.get("component_id"),
            "food_item_id": item.get("food_item_id"),
            "food_item_type": item.get("food_item_type"),
            "portion_scale": item.get("component_portion_scale"),
            "ingredient_name": [{"ingredient_name": x.get("ingredient_name"), "amount": x.get("executable_amount"), "unit": x.get("unit")} for x in ingredients],
            "ingredient_amount": [{"ingredient_name": x.get("ingredient_name"), "amount": x.get("executable_amount"), "unit": x.get("unit")} for x in ingredients],
            "unit": "execution_unit",
            "simple_method": item.get("simple_method"),
            "cooking_method": item.get("simple_method"),
            "simple_method_status": item.get("simple_method_status"),
            "nutrition_status": item.get("nutrition_status"),
            "nutrition_recalculation_status": item.get("nutrition_recalculation_status"),
            "materialization_source": item.get("materialization_source"),
            "materialization_error": item.get("materialization_error"),
            "estimated_energy": planned.get("kcal") if planned else legacy_meal.get("estimated_energy"),
            "estimated_protein": planned.get("protein_g") if planned else legacy_meal.get("estimated_protein"),
            "estimated_carbohydrate": planned.get("carbohydrate_g") if planned else legacy_meal.get("estimated_carbohydrate"),
            "estimated_fat": planned.get("fat_g") if planned else legacy_meal.get("estimated_fat"),
            "nutrition_authority": "V4_RECALCULATED" if planned else "LEGACY_NON_AUTHORITATIVE",
            "legacy_estimated_nutrition": deepcopy({"energy": legacy_meal.get("estimated_energy"), "protein": legacy_meal.get("estimated_protein"), "carbohydrate": legacy_meal.get("estimated_carbohydrate"), "fat": legacy_meal.get("estimated_fat"), "authoritative": False}),
            "status": "ACTIVE" if item.get("execution_materialization_status") == "PASS" else "MATERIALIZATION_FAIL",
        })
    planned_meal = canonical_meal.get("planned_nutrition") or {}
    return {
        "meal_type": legacy_meal.get("meal_type"),
        "category": legacy_meal.get("category"),
        "meal_name": legacy_meal.get("meal_name"),
        "dish_name": " + ".join(str(x.get("dish_name") or "") for x in items),
        "component_id": components[0].get("component_id") if components else None,
        "components": components,
        "ingredient_name": [x.get("ingredient_name") for x in components],
        "ingredient_amount": [x.get("ingredient_amount") for x in components],
        "unit": "execution_unit",
        "raw_or_cooked_basis": legacy_meal.get("raw_or_cooked_basis") or "execution_amount",
        "weight_basis": legacy_meal.get("weight_basis") or legacy_meal.get("raw_or_cooked_basis") or "execution_amount",
        "estimated_energy": planned_meal.get("kcal") if planned_meal else legacy_meal.get("estimated_energy"),
        "estimated_protein": planned_meal.get("protein_g") if planned_meal else legacy_meal.get("estimated_protein"),
        "estimated_carbohydrate": planned_meal.get("carbohydrate_g") if planned_meal else legacy_meal.get("estimated_carbohydrate"),
        "estimated_fat": planned_meal.get("fat_g") if planned_meal else legacy_meal.get("estimated_fat"),
        "cooking_method": legacy_meal.get("cooking_method"),
        "nutrition_authority": "V4_RECALCULATED" if planned_meal else "LEGACY_NON_AUTHORITATIVE",
        "nutrition_status": canonical_meal.get("nutrition_status"),
        "nutrition_recalculation_status": canonical_meal.get("nutrition_recalculation_status"),
        "materialization_source": MATERIALIZATION_SOURCE,
    }


def materialize_canonical_week_diet(rotating_meals: list[dict[str, dict[str, Any]]], *, energy_state: dict[str, Any] | None = None, context_snapshot: dict[str, Any] | None = None, runtime: V4FoodRuntime | None = None) -> tuple[dict[str, Any], list[dict[str, dict[str, Any]]]]:
    """Materialize final legacy meals and return canonical data plus projection."""
    runtime = runtime or load_v4_food_data()
    state = energy_state or {}
    canonical_days: list[dict[str, Any]] = []
    projected_days: list[dict[str, dict[str, Any]]] = []
    all_valid = len(rotating_meals) == 7
    all_ids: list[str] = []
    for day_index in range(7):
        source_day = rotating_meals[day_index] if day_index < len(rotating_meals) else {}
        meals: dict[str, dict[str, Any]] = {}
        projected: dict[str, dict[str, Any]] = {}
        for meal_name in ("breakfast", "lunch", "snack", "dinner"):
            legacy_meal = source_day.get(meal_name)
            if not isinstance(legacy_meal, dict):
                all_valid = False
                continue
            legacy_components = legacy_meal.get("components") or [legacy_meal]
            items = [_materialize_item(day_index + 1, meal_name, i, component, energy_state=state, runtime=runtime) for i, component in enumerate(legacy_components)]
            all_ids.extend(str(item.get("food_item_id")) for item in items)
            item_valid = all(item.get("execution_materialization_status") == "PASS" for item in items)
            all_valid = all_valid and item_valid and all(item.get("dish_name") and item.get("ingredients") and item.get("simple_method") for item in items)
            planned_items = [item.get("planned_nutrition") for item in items]
            planned = None
            if items and all(value is not None for value in planned_items):
                planned = {key: round(sum(float(value.get(key) or 0) for value in planned_items), 4) for key in ("kcal", "protein_g", "carbohydrate_g", "fat_g")}
            nutrition_status = "ACTIVE_RECALCULATED" if planned is not None else ("STRUCTURE_ONLY" if _mode(state) == "STRUCTURE_ONLY" else "NEEDS_SOURCE_RECALC")
            statuses = [item.get("nutrition_recalculation_status") for item in items]
            recalc_status = "COMPLETED" if statuses and all(value == "COMPLETED" for value in statuses) else ("NOT_APPLICABLE" if _mode(state) == "STRUCTURE_ONLY" else "PENDING")
            meals[meal_name] = {"meal": meal_name, "food_items": items, "planned_nutrition": planned, "nutrition_status": nutrition_status, "nutrition_recalculation_status": recalc_status}
            projected[meal_name] = _legacy_projection(meals[meal_name], legacy_meal)
        canonical_days.append({"day": day_index + 1, "meals": meals})
        projected_days.append(projected)
    unique_ids = len(all_ids) == len(set(all_ids))
    trace_status = "FULL" if all_valid and unique_ids else "MISSING"
    trace_validation = {
        "status": "PASS" if trace_status == "FULL" else "FAIL",
        "all_7_days_present": len(canonical_days) == 7,
        "all_planned_meals_mapped": all_valid,
        "all_food_item_ids_unique": unique_ids,
        "all_patient_visible_amounts_are_executable": all_valid,
        "all_items_have_dish_name": all(bool(item.get("dish_name")) for day in canonical_days for meal in day["meals"].values() for item in meal["food_items"]),
        "all_items_have_structured_ingredients": all(bool(item.get("ingredients")) for day in canonical_days for meal in day["meals"].values() for item in meal["food_items"]),
    }
    canonical = {"trace_schema_version": TRACE_SCHEMA_VERSION, "trace_materialization_status": trace_status, "generation_context": deepcopy(context_snapshot or {}), "days": canonical_days, "trace_validation": trace_validation}
    return canonical, projected_days
