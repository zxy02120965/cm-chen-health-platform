"""Root-derived artifact manifest for the Week1 canonical plan."""

from __future__ import annotations

from typing import Any


REQUIRED_ROOTS = (
    "diet_plan_trace",
    "exercise_plan_trace",
    "pulmonary_rehab_trace",
)


def _validation_status(root: dict[str, Any], *, kind: str) -> str:
    validation = root.get("trace_validation")
    if not isinstance(validation, dict):
        return "FAIL"
    explicit = validation.get("status")
    if explicit in {"PASS", "FAIL"}:
        return explicit
    # Exercise's sealed trace contract stores boolean validation fields and
    # exposes schedule consistency separately rather than a status field.
    if kind == "exercise":
        booleans = [value for key, value in validation.items() if key != "status"]
        schedule = root.get("schedule_consistency_validation") or {}
        schedule_pass = schedule.get("status") == "PASS" or validation.get("schedule_consistency_pass") is True
        return "PASS" if booleans and all(value is True for value in booleans) and schedule_pass else "FAIL"
    return "FAIL"


def _trace_entry(root: Any, *, kind: str) -> dict[str, Any]:
    present = isinstance(root, dict)
    if not present:
        return {
            "present": False,
            "materialization": "MISSING",
            "schema_version": None,
            "days_materialized": 0,
            "validation_status": "FAIL",
            **({"schedule_consistency_pass": False} if kind == "exercise" else {}),
        }

    days = root.get("days") if kind == "diet" else root.get("daily_schedule")
    days_materialized = len(days) if isinstance(days, list) else 0
    materialization = root.get("trace_materialization_status")
    schema_version = root.get("trace_schema_version") if kind == "diet" else root.get("schema_version")
    validation_status = _validation_status(root, kind=kind)
    entry = {
        "present": True,
        "materialization": materialization,
        "schema_version": schema_version,
        "days_materialized": days_materialized,
        "validation_status": validation_status,
    }
    if kind == "exercise":
        schedule = root.get("schedule_consistency_validation") or {}
        entry["schedule_consistency_pass"] = bool(
            schedule.get("status") == "PASS"
            or (root.get("trace_validation") or {}).get("schedule_consistency_pass") is True
        )
    return entry


def build_artifact_manifest(
    diet_plan_trace: Any,
    exercise_plan_trace: Any,
    pulmonary_rehab_trace: Any,
) -> dict[str, Any]:
    """Derive the aggregate artifact state exclusively from canonical roots."""
    roots = {
        "diet_plan_trace": diet_plan_trace,
        "exercise_plan_trace": exercise_plan_trace,
        "pulmonary_rehab_trace": pulmonary_rehab_trace,
    }
    entries = {
        "diet_trace": _trace_entry(diet_plan_trace, kind="diet"),
        "exercise_trace": _trace_entry(exercise_plan_trace, kind="exercise"),
        "pulmonary_trace": _trace_entry(pulmonary_rehab_trace, kind="pulmonary"),
    }
    all_required_roots_present = all(isinstance(roots[name], dict) for name in REQUIRED_ROOTS)
    all_required_roots_full = all(
        entry["present"] and entry["materialization"] == "FULL" and entry["days_materialized"] == 7
        for entry in entries.values()
    )
    all_root_validators_pass = all(entry["validation_status"] == "PASS" for entry in entries.values())
    status = "PASS" if all_required_roots_present and all_required_roots_full and all_root_validators_pass else "FAIL"
    return {
        "derived_only_from": list(REQUIRED_ROOTS),
        **entries,
        "all_required_roots_present": all_required_roots_present,
        "all_required_roots_full": all_required_roots_full,
        "all_root_validators_pass": all_root_validators_pass,
        "status": status,
    }
