"""Golden Case comparison helpers (reference-only; never generation input)."""
from __future__ import annotations
from typing import Any

MATCH = "MATCH"
ACCEPTABLE_DIFFERENCE = "ACCEPTABLE_DIFFERENCE"
FAIL = "FAIL"
NOT_COMPARABLE_PENDING = "NOT_COMPARABLE_PENDING"

def classify(expected: Any, actual: Any, *, pending: bool = False, tolerance: float | None = None) -> str:
    if pending:
        return NOT_COMPARABLE_PENDING
    if expected == actual:
        return MATCH
    if tolerance is not None:
        try:
            if abs(float(expected) - float(actual)) <= tolerance:
                return ACCEPTABLE_DIFFERENCE
        except (TypeError, ValueError):
            pass
    return FAIL

def compare_contract(reference: dict[str, Any], actual: dict[str, Any], *, pending_fields: set[str] | None = None) -> dict[str, str]:
    fields = ("phenotype", "safety_level", "goal_source", "management_period", "energy_mode", "prescription_ratio", "daily_energy_target_kcal", "protein_target", "diet_plan", "exercise_plan", "pulmonary_prehab_plan", "monitoring_plan", "safety_rules", "missing_data", "mdt_pending_items", "validation_result", "publication_status")
    pending_fields = pending_fields or set()
    return {field: classify(reference.get(field), actual.get(field), pending=field in pending_fields) for field in fields}
