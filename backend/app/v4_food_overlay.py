"""Execution-complexity overlay for FOOD plans.

This adapter consumes an already-derived ``complexity_overlay``.  It does
not own phenotype or energy decisions and it only reuses components selected
by the existing FOOD generator.  Candidate changes are accepted only when a
caller-provided nutrition-closure check succeeds.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


_SUPPORTED_REASONS = {
    "TIME_CONSTRAINT",
    "PAIN_LIMITATION",
    "MATERIAL_EXECUTION_BURDEN",
    "COMPLEXITY_OVERLAY_F",
}
_MEAL_ORDER = ("breakfast", "lunch", "snack", "dinner")


def _component_ids(meal: dict[str, Any] | None) -> tuple[str, ...]:
    return tuple(
        str(component.get("component_id") or "")
        for component in (meal or {}).get("components") or []
    )


def _day_pattern(day: dict[str, Any]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple((meal, _component_ids(day.get(meal))) for meal in _MEAL_ORDER)


def summarize_food_week(week: list[dict[str, Any]]) -> dict[str, Any]:
    """Return deterministic, component-level complexity metrics."""
    patterns = [_day_pattern(day) for day in week]
    meal_component_counts = [
        {
            meal: len((day.get(meal) or {}).get("components") or [])
            for meal in _MEAL_ORDER
        }
        for day in week
    ]
    breakfast_component_counts = [counts["breakfast"] for counts in meal_component_counts]
    return {
        "weekly_unique_menu_patterns": len(set(patterns)),
        "meal_component_counts": meal_component_counts,
        "breakfast_component_counts": breakfast_component_counts,
        "patterns": patterns,
    }


def _closure_passes(
    day_number: int,
    day: dict[str, Any],
    validator: Callable[[int, dict[str, Any]], bool] | None,
) -> bool:
    return bool(validator and validator(day_number, deepcopy(day)))


def _source_reasons(values: list[str] | None) -> list[str]:
    reasons = [str(value) for value in values or [] if str(value) in _SUPPORTED_REASONS]
    return list(dict.fromkeys(reasons)) or ["COMPLEXITY_OVERLAY_F"]


def apply_f_food_complexity_overlay(
    base_week: list[dict[str, Any]],
    *,
    primary_nutrition_phenotype: str | None,
    complexity_overlay: str | None,
    source_reasons: list[str] | None,
    closure_validator: Callable[[int, dict[str, Any]], bool] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply only source-backed FOOD execution simplification.

    The adapter never creates a component or amount.  It removes an optional
    breakfast vegetable only when the existing closure accepts the resulting
    meal, then tries to repeat up to three already-selected full-day patterns.
    """
    base = deepcopy(base_week)
    before = summarize_food_week(base)
    overlay = str(complexity_overlay or "none").upper()
    reasons = _source_reasons(source_reasons)
    empty_strategy = {
        "status": "NOT_APPLIED",
        "affected_days": [],
        "reasons": [],
    }
    if overlay != "F":
        return base, {
            "overlay": "none",
            "applied": False,
            "source_reasons": [],
            "before": before,
            "strategies": {
                "SIMPLIFY_BREAKFAST": deepcopy(empty_strategy),
                "REDUCE_MENU_ROTATION_COMPLEXITY": {
                    "status": "NOT_APPLIED",
                    "before_patterns": before["weekly_unique_menu_patterns"],
                    "after_patterns": before["weekly_unique_menu_patterns"],
                },
                "REDUCE_RECORDING_BURDEN": deepcopy(empty_strategy),
            },
            "after": before,
            "preserved": {
                "underlying_primary_phenotype": primary_nutrition_phenotype,
                "energy_direction": True,
                "executable_amounts_legal": True,
                "nutrition_closure": True,
            },
            "permanent_exclusion": False,
        }

    final = deepcopy(base)
    simplified_days: list[int] = []
    for index, day in enumerate(final):
        breakfast = day.get("breakfast") or {}
        components = list(breakfast.get("components") or [])
        vegetable_indices = [
            position
            for position, component in enumerate(components)
            if component.get("category") == "vegetable"
        ]
        if not vegetable_indices:
            continue
        candidate = deepcopy(day)
        candidate_breakfast = candidate.get("breakfast") or {}
        candidate_components = list(candidate_breakfast.get("components") or [])
        # The existing breakfast contract makes the vegetable optional.  The
        # last vegetable is removed deterministically; no new food rule or
        # amount is introduced.
        candidate_components.pop(vegetable_indices[-1])
        candidate_breakfast["components"] = candidate_components
        if _closure_passes(index + 1, candidate, closure_validator):
            final[index] = candidate
            simplified_days.append(index + 1)

    after_breakfast = summarize_food_week(final)

    # Keep at most three complete patterns, but only when each repeated day
    # remains within the existing closure.  This is a complexity reduction,
    # not a requirement that every F week has exactly three patterns.
    templates: list[dict[str, Any]] = []
    seen_patterns: set[tuple[tuple[str, tuple[str, ...]], ...]] = set()
    for day in final:
        pattern = _day_pattern(day)
        if pattern in seen_patterns:
            continue
        seen_patterns.add(pattern)
        templates.append(deepcopy(day))
        if len(templates) == 3:
            break

    repeated_days: list[int] = []
    if after_breakfast["weekly_unique_menu_patterns"] > 3:
        for index, day in enumerate(final):
            template = templates[index % len(templates)] if templates else None
            if template is None or _day_pattern(day) == _day_pattern(template):
                continue
            if _closure_passes(index + 1, template, closure_validator):
                final[index] = deepcopy(template)
                repeated_days.append(index + 1)

    after = summarize_food_week(final)
    breakfast_status = "APPLIED" if simplified_days else "NOT_APPLIED"
    pattern_status = "APPLIED" if after["weekly_unique_menu_patterns"] < before["weekly_unique_menu_patterns"] else "NOT_APPLIED"
    recording_status = "APPLIED" if simplified_days or repeated_days else "NOT_APPLIED"
    return final, {
        "overlay": "F",
        "applied": bool(simplified_days or repeated_days),
        "source_reasons": reasons,
        "before": before,
        "strategies": {
            "SIMPLIFY_BREAKFAST": {
                "status": breakfast_status,
                "affected_days": simplified_days,
                "reasons": reasons,
            },
            "REDUCE_MENU_ROTATION_COMPLEXITY": {
                "status": pattern_status,
                "before_patterns": before["weekly_unique_menu_patterns"],
                "candidate_patterns": after_breakfast["weekly_unique_menu_patterns"],
                "after_patterns": after["weekly_unique_menu_patterns"],
                "affected_days": repeated_days,
                "reasons": reasons,
            },
            "REDUCE_RECORDING_BURDEN": {
                "status": recording_status,
                "affected_days": sorted(set(simplified_days + repeated_days)),
                "reasons": reasons,
            },
        },
        "after": after,
        "preserved": {
            "underlying_primary_phenotype": primary_nutrition_phenotype,
            "energy_direction": True,
            "executable_amounts_legal": True,
            "nutrition_closure": None,
        },
        "permanent_exclusion": False,
    }
