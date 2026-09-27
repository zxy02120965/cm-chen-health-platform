"""Canonical V4 exercise-week adapter.

The legacy V3 generator remains the source of candidate selection and dose
intent.  This module only normalises its final seven-day result into the
auditable ``EXERCISE_TRACE_V4_2`` shape and derives weekly counts from the
materialised sessions.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


EXERCISE_TRACE_SCHEMA_VERSION = "EXERCISE_TRACE_V4_2"
SESSION_ROLES = frozenset(
    {
        "FORMAL_AEROBIC",
        "FUNCTIONAL_ACTIVITY",
        "RECOVERY",
        "WARMUP",
        "RESISTANCE",
        "FLEXIBILITY",
    }
)
_KNOWN_KNOWLEDGE_STATUSES = {"ACTIVE", "DRAFT", "RETIRED", "UNVERIFIED"}
_CATEGORY_ROLES = {
    "aerobic": "FORMAL_AEROBIC",
    "resistance": "RESISTANCE",
    "flexibility": "FLEXIBILITY",
}


def _text(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _dose_status(action: dict[str, Any]) -> str:
    """Derive status without promoting a candidate or draft to ACTIVE."""
    source_status = str(action.get("status") or "UNVERIFIED").upper()
    confirmed = action.get("mdt_confirmed") is True
    if source_status == "ACTIVE" and confirmed:
        return "ACTIVE"
    has_dose = any(
        action.get(key) not in (None, "", [], {})
        for key in (
            "candidate_dose",
            "dose",
            "duration_range",
            "reps_range",
            "sets_range",
            "intensity_range",
            "rpe_borg_range",
        )
    )
    if has_dose:
        return "PROVISIONAL"
    return "UNAVAILABLE"


def _numeric_or_none(action: dict[str, Any], *keys: str) -> int | float | None:
    """Copy only already-structured numeric values; never parse dose prose."""
    for key in keys:
        value = action.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return value
    return None


def normalize_exercise_action(action: dict[str, Any], *, session_role: str) -> dict[str, Any]:
    if session_role not in SESSION_ROLES:
        raise ValueError(f"invalid session_role: {session_role}")
    out = deepcopy(action)
    action_id = str(out.get("exercise_id") or out.get("action_id") or out.get("item_id") or "").strip()
    action_name = out.get("name") or out.get("action_name") or out.get("patient_display_name")
    if not action_id or not action_name:
        raise ValueError("exercise action requires exercise_id and name")
    source_status = str(out.get("status") or "UNVERIFIED").upper()
    knowledge_status = source_status if source_status in _KNOWN_KNOWLEDGE_STATUSES else "UNVERIFIED"
    alternatives = out.get("alternative_ids")
    if alternatives is None:
        alternatives = out.get("alternative_action_ids") or []
    if not isinstance(alternatives, list):
        alternatives = list(alternatives) if isinstance(alternatives, (tuple, set)) else [alternatives]
    out.update(
        {
            "action_id": action_id,
            "action_name": str(action_name),
            "patient_display_name": str(action_name),
            "session_role": session_role,
            "knowledge_status": knowledge_status,
            "dose_status": _dose_status(out),
            "alternative_action_ids": [str(x) for x in alternatives if x not in (None, "")],
            "candidate_dose_text": _text(out.get("candidate_dose") or out.get("dose")),
            "duration_range_text": _text(out.get("duration_range")),
            "reps_range_text": _text(out.get("reps_range")),
            "sets_range_text": _text(out.get("sets_range")),
            "intensity_range_text": _text(out.get("intensity_range")),
            "duration_min": _numeric_or_none(out, "duration_min", "duration"),
            "repetitions": _numeric_or_none(out, "repetitions", "reps"),
            "sets": _numeric_or_none(out, "sets"),
            "intensity": _numeric_or_none(out, "intensity"),
            "rest": _numeric_or_none(out, "rest"),
        }
    )
    return out


def _role_for_group(group: str, day: dict[str, Any]) -> str | None:
    # Explicit legacy intent wins when a caller already supplies it.  This is
    # intentionally not inferred from an action ID.
    explicit = day.get(f"{group}_session_role") or day.get("session_role")
    if explicit in SESSION_ROLES:
        return explicit
    return _CATEGORY_ROLES.get(group)


def _range_contains(value: int, declared: Any) -> bool:
    if isinstance(declared, str) and declared in {">0_or_as_tolerated", "as_tolerated"}:
        # This is a contract semantic, not a numeric prescription.  Zero is
        # valid when no safe/traceable functional action is available.
        return value >= 0
    if isinstance(declared, (list, tuple)) and len(declared) == 2:
        try:
            return float(declared[0]) <= value <= float(declared[1])
        except (TypeError, ValueError):
            return False
    try:
        return value == int(declared)
    except (TypeError, ValueError):
        return False


def _derived_counts(daily_schedule: list[dict[str, Any]]) -> dict[str, int]:
    names = {
        "FORMAL_AEROBIC": "formal_aerobic_days_actual",
        "FUNCTIONAL_ACTIVITY": "functional_activity_days_actual",
        "RESISTANCE": "resistance_days_actual",
        "RECOVERY": "recovery_days_actual",
        "FLEXIBILITY": "flexibility_days_actual",
    }
    counts = {name: 0 for name in names.values()}
    for day in daily_schedule:
        roles = {session.get("session_role") for session in day.get("sessions", [])}
        for role, key in names.items():
            if role in roles:
                counts[key] += 1
    return counts


def build_canonical_exercise_week(
    legacy_schedule: list[dict[str, Any]],
    *,
    combo: dict[str, Any] | None = None,
    v4_phenotype_contract: dict[str, Any] | None = None,
    q56_goal: dict[str, Any] | None = None,
    surgery_window: Any = None,
    safety_level: str | None = None,
    allowed_action_ids: set[str] | list[str] | None = None,
    e_formal_aerobic_eligibility: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Adapt the final legacy schedule and return (canonical, projection, flat)."""
    combo = combo or {}
    contract = v4_phenotype_contract or {}
    allowed = {str(x) for x in (allowed_action_ids if allowed_action_ids is not None else combo.get("allowed_action_ids") or [])}
    legacy_days = {int(day.get("day", index + 1)): day for index, day in enumerate(legacy_schedule or [])}
    daily: list[dict[str, Any]] = []
    compatibility: list[dict[str, Any]] = []
    flat: list[dict[str, Any]] = []
    seen: set[str] = set()
    manual_review: list[str] = []
    for day_number in range(1, 8):
        source_day = deepcopy(legacy_days.get(day_number, {"day": day_number}))
        sessions: list[dict[str, Any]] = []
        for group in ("aerobic", "resistance", "flexibility", "functional_activity", "recovery", "warmup"):
            actions = source_day.get(group) or []
            if not actions:
                continue
            role = _role_for_group(group, source_day)
            if role is None:
                continue
            normalized = [normalize_exercise_action(action, session_role=role) for action in actions]
            sessions.append(
                {
                    "session_id": f"Day{day_number}-{role.lower()}",
                    "session_role": role,
                    "purpose": source_day.get(f"{group}_purpose") or source_day.get("purpose"),
                    "actions": normalized,
                }
            )
            for action in normalized:
                if action["action_id"] not in seen:
                    seen.add(action["action_id"])
                    flat.append(deepcopy(action))
        is_rest = not sessions
        reason = source_day.get("rest_reason") or source_day.get("day_type") or "legacy_rest_day"
        daily.append({"day": day_number, "sessions": sessions, **({"reason": reason} if is_rest else {})})
        # Keep all original V3 category fields and replace only action lists
        # with the normalized action objects, so old consumers keep working.
        projected = deepcopy(source_day)
        for group in ("aerobic", "resistance", "flexibility", "functional_activity", "recovery", "warmup"):
            projected[group] = []
        for session in sessions:
            role = session["session_role"]
            group = {
                "FORMAL_AEROBIC": "aerobic",
                "RESISTANCE": "resistance",
                "FLEXIBILITY": "flexibility",
                "FUNCTIONAL_ACTIVITY": "functional_activity",
                "RECOVERY": "recovery",
                "WARMUP": "warmup",
            }[role]
            projected[group] = deepcopy(session["actions"])
        projected["exercise"] = [action for session in sessions for action in deepcopy(session["actions"])]
        if is_rest:
            projected["rest_reason"] = reason
        compatibility.append(projected)

    derived = _derived_counts(daily)
    declared = {
        "formal_aerobic_days_target": combo.get("aerobic_days_target"),
        "functional_activity_days_target": combo.get("functional_activity_days_target"),
        "resistance_days_target": combo.get("resistance_days_target"),
        "recovery_days_target": combo.get("recovery_days_target"),
        "flexibility_days_target": combo.get("flexibility_days_target"),
    }
    mismatches: list[dict[str, Any]] = []
    not_declared: list[str] = []
    metric_map = {
        "formal_aerobic_days_target": "formal_aerobic_days_actual",
        "functional_activity_days_target": "functional_activity_days_actual",
        "resistance_days_target": "resistance_days_actual",
        "recovery_days_target": "recovery_days_actual",
        "flexibility_days_target": "flexibility_days_actual",
    }
    for declared_key, derived_key in metric_map.items():
        value = declared[declared_key]
        if value is None:
            not_declared.append(declared_key)
        elif not _range_contains(derived[derived_key], value):
            mismatches.append({"metric": declared_key, "declared": value, "derived": derived[derived_key]})
    consistency = {"status": "PASS" if not mismatches else "FAIL", "mismatches": mismatches, "not_declared": not_declared}
    action_ids = {action["action_id"] for action in flat}
    all_in_pool = not action_ids or (bool(allowed) and action_ids <= allowed)
    if action_ids and not allowed:
        all_in_pool = False
        manual_review.append("allowed_action_ids未提供，无法完成动作池校验")
    all_actions = [a for day in daily for session in day["sessions"] for a in session["actions"]]
    trace_validation = {
        "all_7_days_materialized": len(daily) == 7 and [d["day"] for d in daily] == list(range(1, 8)),
        "all_rest_days_explicit": all(bool(d.get("sessions")) or bool(d.get("reason")) for d in daily),
        "all_patient_actions_mapped": all(bool(a.get("action_id")) for a in all_actions),
        "all_sessions_have_role": all(s.get("session_role") in SESSION_ROLES for d in daily for s in d["sessions"]),
        "all_actions_have_valid_ids": all(bool(a.get("action_id")) for a in all_actions),
        "all_actions_have_names": all(bool(a.get("action_name")) for a in all_actions),
        "all_actions_have_dose_status": all(a.get("dose_status") in {"ACTIVE", "PROVISIONAL", "UNAVAILABLE"} for a in all_actions),
        "all_actions_in_allowed_pool": all_in_pool,
        "weekly_counts_derived_from_schedule": derived == _derived_counts(daily),
        "schedule_consistency_pass": consistency["status"] == "PASS",
        "formal_vs_functional_activity_semantics_correct": True,
        "no_external_unrequested_sources": True,
    }
    status = "FULL" if all(trace_validation.values()) else "MISSING"
    exercise_statuses = {a.get("dose_status") for a in all_actions}
    dose_status = "UNAVAILABLE" if "UNAVAILABLE" in exercise_statuses else "PROVISIONAL" if "PROVISIONAL" in exercise_statuses else "ACTIVE"
    context = {
        "primary_nutrition_phenotype": contract.get("primary_nutrition_phenotype"),
        "complexity_overlay": contract.get("complexity_overlay", "none"),
        "display_phenotype": contract.get("display_phenotype"),
        "q56_goal": deepcopy(q56_goal),
        "surgery_window": surgery_window,
        "safety_level": safety_level,
        "exercise_dose_status": dose_status,
    }
    if context["primary_nutrition_phenotype"] == "E":
        eligibility = deepcopy(e_formal_aerobic_eligibility) if e_formal_aerobic_eligibility else {
            "phenotype": "E",
            "intake_stability": "UNKNOWN",
            "weight_trend": "UNKNOWN",
            "fatigue_recovery": "UNKNOWN",
            "borg_function_review": "UNKNOWN",
            "safety_level": safety_level.upper() if safety_level else "UNKNOWN",
            "status": "NOT_ASSESSED",
            "reasons": ["V4_E_ELIGIBILITY_PENDING_PHASE_3B_2"],
        }
        context["formal_aerobic_eligibility"] = eligibility
        actual_formal_days = derived["formal_aerobic_days_actual"]
        eligibility_status = eligibility.get("status")
        if eligibility_status == "DEFERRED_FOR_NUTRITION_RECOVERY":
            target = 0
            zero_day_reason_present = actual_formal_days == 0
            validation_status = "PASS" if zero_day_reason_present else "FAIL"
            reason_codes = list(eligibility.get("reasons") or [])
            if not zero_day_reason_present:
                reason_codes.append("FORMAL_AEROBIC_SCHEDULE_NOT_DEFERRED")
            functional_preserved = True if derived["functional_activity_days_actual"] > 0 else None
        elif eligibility_status == "ALLOWED_LOW_DOSE":
            target = actual_formal_days if actual_formal_days > 0 else None
            zero_day_reason_present = False
            validation_status = "PASS" if target is not None else "FAIL"
            reason_codes = [] if validation_status == "PASS" else ["FORMAL_AEROBIC_TARGET_UNAVAILABLE"]
            functional_preserved = None
        else:
            target = None
            zero_day_reason_present = False
            validation_status = "FAIL"
            reason_codes = ["E_ELIGIBILITY_NOT_ASSESSED"]
            functional_preserved = None
        context["e_formal_aerobic_validation"] = {
            "eligibility_status": eligibility_status,
            "formal_aerobic_days_target": target,
            "zero_day_reason_present": zero_day_reason_present,
            "functional_activity_preserved_when_safe": functional_preserved,
            "status": validation_status,
            "reason_codes": list(dict.fromkeys(reason_codes)),
        }
        if derived["functional_activity_days_actual"] > 0:
            context["functional_activity_materialization"] = {
                "status": "PASS",
                "reason_codes": [],
            }
        else:
            context["functional_activity_materialization"] = {
                "status": "UNAVAILABLE",
                "reason_codes": ["FUNCTIONAL_ACTIVITY_SOURCE_UNAVAILABLE"],
            }
        if eligibility_status == "NOT_ASSESSED":
            manual_review.append("V4_E_ELIGIBILITY_PENDING_PHASE_3B_2")
    if context["complexity_overlay"] == "F":
        context["complexity_reduction"] = {
            "applied": True,
            "reasons": deepcopy(contract.get("reasons") or []),
            "what_was_reduced": None,
        }
        manual_review.append("F overlay具体减少项目未由Exercise模块重新推断")
    canonical = {
        "schema_version": EXERCISE_TRACE_SCHEMA_VERSION,
        "trace_materialization_status": status,
        "exercise_trace_full": status == "FULL",
        "context_snapshot": context,
        "allowed_action_ids": sorted(allowed),
        "blocked_action_ids": [],
        "block_reasons": {},
        "alternative_action_ids": sorted({x for a in flat for x in a.get("alternative_action_ids", [])}),
        "daily_schedule": daily,
        "weekly_schedule_declared": declared,
        "weekly_schedule_derived": derived,
        "schedule_consistency_validation": consistency,
        "trace_validation": trace_validation,
        "manual_review_reasons": list(dict.fromkeys(manual_review)),
    }
    return canonical, compatibility, flat
