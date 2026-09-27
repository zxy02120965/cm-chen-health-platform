"""Structured presentation projection for the Week1 backend plan.

This module deliberately contains no clinical selection or recalculation.  It
only copies existing plan fields and canonical roots into a stable, ordered
11-key presentation contract.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PLAN_VIEW_KEYS = (
    "patient_summary",
    "assessment",
    "weekly_goals",
    "nutrition_basis",
    "nutrition_plan",
    "exercise_plan",
    "pulmonary_rehab_plan",
    "monitoring",
    "safety",
    "weekly_review",
    "clinician_review",
)


_DISPLAY_STATUS = {
    "ACTIVE": "已确认",
    "PROVISIONAL": "候选",
    "UNAVAILABLE": "暂无法形成精确目标",
}


def _display_status(status: Any) -> str | None:
    return _DISPLAY_STATUS.get(str(status)) if status is not None else None


def _root_validation(root: Any) -> dict[str, Any]:
    value = root.get("trace_validation") if isinstance(root, dict) else None
    return deepcopy(value) if isinstance(value, dict) else {"status": "MISSING"}


def _food_provenance_summary(root: dict[str, Any]) -> dict[str, Any]:
    provenance = ((root.get("generation_context") or {}).get("asset_provenance") or {})
    return {
        "manifest_relative_path": provenance.get("manifest_relative_path"),
        "ingredient_master": {
            "role": (provenance.get("ingredient_master") or {}).get("role"),
            "version": (provenance.get("ingredient_master") or {}).get("version"),
        },
        "food_execution": {
            "role": (provenance.get("food_execution") or {}).get("role"),
            "version": (provenance.get("food_execution") or {}).get("version"),
        },
    }


def _weekly_review_projection(plan: dict[str, Any]) -> dict[str, Any]:
    raw = deepcopy(plan.get("weekly_review") or {})
    if not raw:
        return {"status": "NOT_DUE", "display_status": "尚未到复评时间", "items": [], "reason": "首周尚未完成"}
    # The existing first-week generator emits DATA_INSUFFICIENT before any
    # execution records exist.  Keep that raw value for audit, while exposing
    # the presentation contract's NOT_DUE wording without adding a new review
    # algorithm.
    if raw.get("decision") == "DATA_INSUFFICIENT" and raw.get("confidence") == "LOW":
        return {
            "status": "NOT_DUE",
            "display_status": "尚未到复评时间",
            "raw_decision": raw.get("decision"),
            "items": [],
            "reason": raw.get("reason") or "首周尚未完成",
        }
    return {
        "status": raw.get("status") or raw.get("decision") or "PENDING",
        "display_status": raw.get("display") or raw.get("decision"),
        "items": deepcopy(raw.get("recommended_changes") or raw.get("allowed_changes") or []),
        "raw": raw,
    }


def build_plan_view(plan: dict[str, Any]) -> dict[str, Any]:
    """Build the fixed 11-key presentation projection from existing data."""
    diet_root = plan.get("diet_plan_trace") or {}
    exercise_root = plan.get("exercise_plan_trace") or {}
    pulmonary_root = plan.get("pulmonary_rehab_trace") or {}
    energy_state = plan.get("energy_state") or {}
    energy_target = energy_state.get("energy_target") or {}
    stage_goals = plan.get("stage_goals") or {}
    validation = plan.get("validation_result") or {}
    artifact_manifest = plan.get("artifact_manifest") or {}

    nutrition_status = energy_target.get("status")
    protein_target = (plan.get("diet_plan") or {}).get("protein_target")
    weekly_derived = deepcopy(exercise_root.get("weekly_schedule_derived") or {})
    pulmonary_source = pulmonary_root.get("source_provenance") or {}

    # Dict insertion order is the public contract order.
    return {
        "patient_summary": {
            "patient_id": plan.get("patient_id"),
            "display_identity": plan.get("patient_display_name") or plan.get("patient_name"),
            "primary_nutrition_phenotype": plan.get("primary_nutrition_phenotype"),
            "complexity_overlay": plan.get("complexity_overlay"),
            "display_phenotype": plan.get("display_phenotype"),
            "safety_level": plan.get("safety_level"),
            "surgery_window": plan.get("surgery_window"),
            "core_direction": stage_goals.get("overall_goal"),
        },
        "assessment": {
            "status": "AVAILABLE" if plan.get("primary_nutrition_phenotype") else "PENDING",
            "primary_nutrition_phenotype": plan.get("primary_nutrition_phenotype"),
            "complexity_overlay": plan.get("complexity_overlay"),
            "display_phenotype": plan.get("display_phenotype"),
            "missing_data": deepcopy(plan.get("missing_data") or []),
            "uncertain_items": deepcopy(plan.get("uncertain_items") or []),
        },
        "weekly_goals": {
            "status": "AVAILABLE" if stage_goals else "PENDING",
            "items": deepcopy(stage_goals),
            "reason": None if stage_goals else "当前没有独立 goals object",
        },
        "nutrition_basis": {
            "energy": {
                "status": nutrition_status,
                "display_status": _display_status(nutrition_status),
                "candidate_kcal": energy_target.get("provisional_energy_target_kcal"),
                "source": energy_state.get("source"),
            },
            "protein": {
                "status": "AVAILABLE" if protein_target is not None else "UNAVAILABLE",
                "target": protein_target,
            },
            "diet_generation_mode": energy_state.get("diet_generation_mode"),
            "provenance_summary": _food_provenance_summary(diet_root),
            "review_state": deepcopy(plan.get("nutrition_review") or {}),
        },
        "nutrition_plan": {
            "status": diet_root.get("trace_materialization_status") or "MISSING",
            "display_status": "已形成结构化周计划" if diet_root.get("trace_materialization_status") == "FULL" else "待补充",
            "diet_generation_mode": energy_state.get("diet_generation_mode"),
            "days": deepcopy(diet_root.get("days") or []),
            "patient_projection": deepcopy(plan.get("weekly_schedule") or []),
            "trace_validation": _root_validation(diet_root),
            "provenance_summary": _food_provenance_summary(diet_root),
        },
        "exercise_plan": {
            "status": exercise_root.get("trace_materialization_status") or "MISSING",
            "display_status": "已形成结构化周计划" if exercise_root.get("trace_materialization_status") == "FULL" else "待补充",
            "weekly_summary": {
                "declared": deepcopy(exercise_root.get("weekly_schedule_declared") or {}),
                "derived": weekly_derived,
                "schedule_consistency": deepcopy(exercise_root.get("schedule_consistency_validation") or {}),
            },
            "days": deepcopy(exercise_root.get("daily_schedule") or []),
            "patient_projection": deepcopy(plan.get("exercise_plan") or []),
            "dose_status": sorted({
                action.get("dose_status")
                for day in (exercise_root.get("daily_schedule") or [])
                for session in (day.get("sessions") or [])
                for action in (session.get("actions") or [])
                if action.get("dose_status") is not None
            }),
            "trace_validation": _root_validation(exercise_root),
        },
        "pulmonary_rehab_plan": {
            "status": pulmonary_root.get("trace_materialization_status") or "MISSING",
            "display_status": "已形成结构化周计划" if pulmonary_root.get("trace_materialization_status") == "FULL" else "待补充",
            "selected_action_ids": deepcopy(pulmonary_root.get("selected_action_ids") or []),
            "minimum_sufficient_set": deepcopy(pulmonary_root.get("minimum_sufficient_set") or {}),
            "days": deepcopy(pulmonary_root.get("daily_schedule") or []),
            "patient_projection": deepcopy(plan.get("pulmonary_prehab_plan") or []),
            "p05_gate": deepcopy(pulmonary_root.get("p05_gate") or {}),
            "p06_gate": deepcopy(pulmonary_root.get("p06_gate") or {}),
            "dose_status": pulmonary_root.get("pulmonary_dose_status"),
            "source_status": {
                "source_version": pulmonary_source.get("source_version"),
                "knowledge_status": pulmonary_source.get("knowledge_status"),
                "mdt_confirmed": pulmonary_source.get("mdt_confirmed"),
            },
            "trace_validation": _root_validation(pulmonary_root),
        },
        "monitoring": {
            "status": "SCHEDULED" if plan.get("monitoring_plan") else "NOT_SCHEDULED",
            "items": deepcopy((plan.get("monitoring_plan") or {}).get("items") or []),
            "plan": deepcopy(plan.get("monitoring_plan") or {}),
            "record_requirements": deepcopy(plan.get("daily_record_requirements") or {}),
        },
        "safety": {
            "safety_level": plan.get("safety_level"),
            "reason_codes": deepcopy(plan.get("safety_reason_codes") or []),
            "stop_conditions": (plan.get("safety_rules") or {}).get("stop_conditions"),
            "precautions": (plan.get("safety_rules") or {}).get("precautions"),
            "blocked_modules": deepcopy((plan.get("safety_rules") or {}).get("blocked_modules") or []),
            "manual_review_required": bool(plan.get("manual_review_required")),
        },
        "weekly_review": _weekly_review_projection(plan),
        "clinician_review": {
            "plan_status": plan.get("status"),
            "review_status": plan.get("review_status") or "NOT_REVIEWED",
            "review_eligible": plan.get("review_eligible"),
            "manual_review_required": bool(plan.get("manual_review_required")),
            "warnings": deepcopy((validation.get("contract_validator") or {}).get("warnings") or []),
            "manual_review_reasons": deepcopy(plan.get("manual_review_reasons") or []),
            "publication_blockers": deepcopy(validation.get("publish_block_reasons") or []),
            "publication_validation": validation.get("publish_validation"),
            "publication_blocked": bool(plan.get("publication_blocked")),
            "audit": {
                "artifact_manifest_status": artifact_manifest.get("status"),
                "all_required_roots_full": artifact_manifest.get("all_required_roots_full"),
            },
            "review_note": plan.get("review_note"),
        },
    }
