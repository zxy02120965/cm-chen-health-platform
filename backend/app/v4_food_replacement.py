"""Approved executable FOOD replacements.

Closure replacements in the legacy engine remain an internal nutrition
optimization.  This adapter is the separate patient/doctor-facing contract:
only MDT V1.4 approved IDs are considered, then every candidate goes through
the manifest-backed V1.3 execution and nutrition gates.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .v4_food_data import V4FoodDataError, V4FoodRuntime, load_v4_food_data
from .v4_food_materializer import materialize_standard_component
from .v4_nutrition_recalculation import recalculate_ingredient_nutrition


def _mode(energy_state: dict[str, Any] | None) -> str:
    return str((energy_state or {}).get("diet_generation_mode") or "EXACT_PROVISIONAL_REVIEW")


def _allowed_scale(item: dict[str, Any]) -> float | None:
    scales = item.get("portion_options") or []
    try:
        values = [float(value) for value in scales]
    except (TypeError, ValueError):
        return None
    if not values:
        return None
    preferred = item.get("portion_scale")
    try:
        preferred = float(preferred)
    except (TypeError, ValueError):
        preferred = None
    if preferred in values:
        return preferred
    return min(values)


def _candidate_base(item: dict[str, Any], source_component_id: str, slot: str) -> dict[str, Any]:
    return {
        "replacement_for_component_id": source_component_id,
        "replacement_component_id": str(item.get("component_id")),
        "replacement_group": item.get("approved_replacement_group"),
        "meal_slot": slot,
        "food_item_type": "STANDARD_COMPONENT",
        "dish_name": item.get("dish_name") or item.get("name"),
        "source_version": item.get("source_version"),
        "source_asset_role": item.get("source_asset_role") or "MDT_STANDARD_COMPONENT_EXECUTION",
        "materialization_source": "MDT_STANDARD_COMPONENT_EXECUTION_V1.3",
        "replacement_integrity": {"status": "NOT_AVAILABLE", "reason_codes": []},
    }


def _rejected(base: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    result = deepcopy(base)
    result.update({
        "component_portion_scale": None,
        "ingredients": [],
        "planned_nutrition": None,
        "nutrition_status": status,
        "execution_status": status,
        "nutrition_recalculation_status": "PENDING" if status == "SOURCE_PENDING" else "NOT_APPLICABLE",
        "materialization_status": "NOT_MATERIALIZED",
        "replacement_integrity": {"status": status, "reason_codes": [reason]},
    })
    return result


def _materialize_candidate(item: dict[str, Any], source_component_id: str, slot: str, *, energy_state: dict[str, Any], runtime: V4FoodRuntime) -> dict[str, Any]:
    base = _candidate_base(item, source_component_id, slot)
    mode = _mode(energy_state)
    if mode != "STRUCTURE_ONLY" and item.get("exact_nutrition_eligible") is not True:
        return _rejected(base, "SOURCE_PENDING", "REPLACEMENT_SOURCE_PENDING")
    scale = _allowed_scale(item)
    if scale is None:
        return _rejected(base, "UNAVAILABLE", "NO_EXECUTABLE_REPLACEMENT_AT_LEGAL_SCALE")
    try:
        materialized = materialize_standard_component(str(item.get("component_id")), scale, energy_state=mode, runtime=runtime)
        nutrition = recalculate_ingredient_nutrition(materialized.get("ingredients") or [], runtime=runtime, energy_state=mode)
    except (V4FoodDataError, KeyError, ValueError) as exc:
        return _rejected(base, "UNAVAILABLE", f"MATERIALIZATION_FAILED:{exc}")
    result = deepcopy(base)
    result.update({
        "component_portion_scale": scale,
        "ingredients": deepcopy(materialized.get("ingredients") or []),
        "simple_method": item.get("cooking_method") or item.get("brief_instructions"),
        "planned_nutrition": nutrition.get("planned_nutrition") if mode != "STRUCTURE_ONLY" else None,
        "nutrition_status": nutrition.get("nutrition_status"),
        "execution_status": materialized.get("execution_materialization_status"),
        "nutrition_recalculation_status": nutrition.get("nutrition_recalculation_status"),
        "materialization_status": "MATERIALIZED",
        "materialization_source": "MDT_STANDARD_COMPONENT_EXECUTION_V1.3",
        "replacement_integrity": {"status": "PASS", "reason_codes": []},
    })
    return result


def attach_approved_replacements(
    rotating_meals: list[dict[str, dict[str, Any]]],
    catalog_foods: list[dict[str, Any]],
    *,
    payload: dict[str, Any],
    energy_state: dict[str, Any],
    runtime: V4FoodRuntime | None = None,
    eligibility_checker: Any | None = None,
) -> dict[str, Any]:
    """Attach approved replacement objects to the final selected meals."""
    runtime = runtime or load_v4_food_data()
    catalog = {str(item.get("component_id")): item for item in catalog_foods if item.get("component_id")}
    summary: list[dict[str, Any]] = []
    mode = _mode(energy_state)
    for day_index, day in enumerate(rotating_meals, start=1):
        for slot in ("breakfast", "lunch", "snack", "dinner"):
            meal = day.get(slot)
            if not isinstance(meal, dict):
                continue
            for component in meal.get("components") or []:
                source_id = str(component.get("component_id") or "")
                source = catalog.get(source_id)
                approved_ids = list((source or {}).get("replacement_ids") or component.get("replacement_options") or [])
                replacements: list[dict[str, Any]] = []
                if source is None or not approved_ids:
                    availability = "NO_APPROVED_STRUCTURED_REPLACEMENT"
                else:
                    availability = "AVAILABLE"
                    for candidate_id in approved_ids:
                        candidate = catalog.get(str(candidate_id))
                        if candidate is None:
                            continue
                        candidate_slots = candidate.get("meal_type") or []
                        if isinstance(candidate_slots, str):
                            candidate_slots = [candidate_slots]
                        if slot not in candidate_slots and "any" not in candidate_slots:
                            continue
                        if slot == "breakfast" and candidate.get("breakfast_allowed") == "NO":
                            continue
                        if candidate.get("category") != source.get("category"):
                            continue
                        if source.get("approved_replacement_group") and candidate.get("approved_replacement_group") != source.get("approved_replacement_group"):
                            continue
                        allowed = eligibility_checker(candidate, payload) if eligibility_checker else _food_allowed(candidate, payload)
                        if not allowed:
                            continue
                        replacements.append(_materialize_candidate(candidate, source_id, slot, energy_state=energy_state, runtime=runtime))
                component["replacements"] = replacements
                component["replacement_availability"] = availability
                component["replacement_integrity"] = {
                    "status": "PASS" if any(item.get("replacement_integrity", {}).get("status") == "PASS" for item in replacements) else ("SOURCE_PENDING" if any(item.get("replacement_integrity", {}).get("status") == "SOURCE_PENDING" for item in replacements) else "NOT_AVAILABLE"),
                    "approved_candidate_count": len(approved_ids),
                    "materialized_candidate_count": sum(item.get("replacement_integrity", {}).get("status") == "PASS" for item in replacements),
                }
                summary.append({"day": day_index, "meal": slot, "component_id": source_id, "replacement_availability": availability, "replacements": deepcopy(replacements)})
    return {"status": "PASS", "mode": mode, "items": summary, "approved_metadata_only": True}


def validate_replacement_root(root: dict[str, Any]) -> dict[str, Any]:
    """Validate physically stored replacement objects without re-generating them."""
    from .v4_food_selection import build_manifest_backed_food_catalog

    catalog, _ = build_manifest_backed_food_catalog()
    catalog_by_id = {str(item.get("component_id")): item for item in catalog}
    issues: list[dict[str, Any]] = []
    checked = 0
    for day in root.get("days") or []:
        for meal_name, meal in (day.get("meals") or {}).items():
            for item in meal.get("food_items") or []:
                for replacement in item.get("replacements") or []:
                    checked += 1
                    integrity = replacement.get("replacement_integrity") or {}
                    status = integrity.get("status")
                    source = catalog_by_id.get(str(item.get("component_id") or ""))
                    candidate = catalog_by_id.get(str(replacement.get("replacement_component_id") or ""))
                    if source is None or candidate is None or str(candidate.get("component_id")) not in set(source.get("replacement_ids") or []):
                        issues.append({"day": day.get("day"), "meal": meal_name, "component_id": item.get("component_id"), "reason": "REPLACEMENT_NOT_APPROVED_IN_V14"})
                        continue
                    candidate_slots = candidate.get("meal_type") or []
                    if isinstance(candidate_slots, str):
                        candidate_slots = [candidate_slots]
                    if meal_name not in candidate_slots and "any" not in candidate_slots:
                        issues.append({"day": day.get("day"), "meal": meal_name, "component_id": item.get("component_id"), "reason": "REPLACEMENT_MEAL_SLOT_MISMATCH"})
                    if candidate.get("category") != source.get("category"):
                        issues.append({"day": day.get("day"), "meal": meal_name, "component_id": item.get("component_id"), "reason": "REPLACEMENT_CATEGORY_MISMATCH"})
                    if status == "PASS" and candidate.get("exact_nutrition_eligible") is not True:
                        issues.append({"day": day.get("day"), "meal": meal_name, "component_id": item.get("component_id"), "reason": "SOURCE_PENDING_REPLACEMENT_MARKED_PASS"})
                    if status == "PASS":
                        required = ("replacement_for_component_id", "replacement_component_id", "replacement_group", "component_portion_scale", "ingredients", "nutrition_recalculation_status")
                        if any(replacement.get(key) in (None, "", []) for key in required):
                            issues.append({"day": day.get("day"), "meal": meal_name, "component_id": item.get("component_id"), "reason": "INCOMPLETE_MATERIALIZED_REPLACEMENT"})
                    elif status not in {"SOURCE_PENDING", "NOT_AVAILABLE", "UNAVAILABLE"}:
                        issues.append({"day": day.get("day"), "meal": meal_name, "reason": "INVALID_REPLACEMENT_STATUS"})
    return {"status": "PASS" if not issues else "FAIL", "checked": checked, "issues": issues, "no_text_only_fake_replacements": not any(not item.get("replacement_component_id") for item in issues)}


def _food_allowed(food: dict[str, Any], payload: dict[str, Any]) -> bool:
    allergy = payload.get("q32_foodAllergy") or payload.get("food_allergy") or []
    intolerance = payload.get("q33_foodIntolerance") or payload.get("food_intolerance") or []
    if isinstance(allergy, str):
        allergy = [allergy]
    if isinstance(intolerance, str):
        intolerance = [intolerance]
    text = " ".join(str(food.get(key) or "") for key in ("name", "dish_name", "ingredients", "contraindications"))
    if any(str(item) in text for item in allergy):
        return False
    if any("乳糖不耐" in str(item) for item in intolerance) and any(token in text for token in ("牛奶", "奶", "酸奶", "乳")):
        return False
    return not (any("麸质" in str(item) for item in intolerance) and any(token in text for token in ("小麦", "面包", "全麦")))
