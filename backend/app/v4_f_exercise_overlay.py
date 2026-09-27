"""Minimal, evidence-traceable F complexity overlay for Exercise.

The module deliberately does not own phenotype or safety decisions.  It only
consumes the already-derived V4 contract and applies changes that can be
expressed by the existing V3 action metadata.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_EDUCATION_ONLY = ("不知道怎么运动", "第一次学习", "需要示范")
_PAIN = ("疼痛", "痛")
_TIME = ("时间少", "时间不足", "时间限制")


def _items(value: Any) -> list[str]:
    if value in (None, "", [], {}):
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    for item in values:
        text = str(item).strip()
        if not text:
            continue
        # Assessment answers commonly contain a semicolon-delimited checklist.
        result.extend(part.strip() for part in text.replace("；", ";").split(";") if part.strip())
    return result


def derive_complexity_overlay_trace(payload: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    """Classify the facts already present in the assessment, without new rules."""
    overlay = str(contract.get("complexity_overlay") or "none").upper()
    metabolic = _items(payload.get("q43_metabolicConditions") or payload.get("metabolic_conditions"))
    barriers = _items(payload.get("q51_executionBarriers") or payload.get("execution_barriers"))
    source_facts: list[dict[str, Any]] = []
    trigger_reasons: list[str] = []
    education_facts: list[str] = []

    if metabolic:
        source_facts.append({"field": "q43_metabolicConditions", "values": metabolic, "evidence_type": "complexity_evidence"})
        if overlay == "F":
            trigger_reasons.append("MULTIPLE_METABOLIC_COMORBIDITIES")
    for fact in barriers:
        if any(token in fact for token in _EDUCATION_ONLY):
            education_facts.append(fact)
            source_facts.append({"field": "q51_executionBarriers", "value": fact, "evidence_type": "education_only"})
            continue
        source_facts.append({"field": "q51_executionBarriers", "value": fact, "evidence_type": "complexity_evidence"})
        if any(token in fact for token in _PAIN):
            trigger_reasons.append("PAIN_LIMITATION")
        if any(token in fact for token in _TIME):
            trigger_reasons.append("TIME_CONSTRAINT")
        if fact:
            trigger_reasons.append("MATERIAL_EXECUTION_BURDEN")

    trigger_reasons = list(dict.fromkeys(trigger_reasons))
    major = overlay == "F" and bool(trigger_reasons or metabolic)
    return {
        "overlay": "F" if overlay == "F" else "none",
        "major_complexity_trigger_present": major,
        "material_execution_burden_present": bool(overlay == "F" and (metabolic or any(f for f in barriers if f not in education_facts))),
        "trigger_reasons": trigger_reasons,
        "education_only": bool(education_facts) and not bool(trigger_reasons or metabolic),
        "source_facts": source_facts,
    }


def _supports_segmentation(action: dict[str, Any]) -> bool:
    text = " ".join(str(action.get(key) or "") for key in ("duration_range", "candidate_dose", "dose", "reps_range"))
    return "分段" in text or "/段" in text


def _strategy(status: str, *, reasons: list[str] | None = None, source_support: list[str] | None = None, affected: list[str] | None = None, changes: list[dict[str, Any]] | None = None, reason: str | None = None) -> dict[str, Any]:
    result = {
        "applicability": status,
        "patient_fact_reasons": list(reasons or []),
        "source_support": list(source_support or []),
        "affected_action_ids": list(affected or []),
        "changes": list(changes or []),
    }
    if reason:
        result["reason"] = reason
    return result


def apply_f_exercise_overlay(
    schedule: list[dict[str, Any]],
    *,
    contract: dict[str, Any],
    complexity_trace: dict[str, Any],
    action_catalog: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply only existing-range split semantics and progression hold."""
    base = deepcopy(schedule)
    if str(contract.get("complexity_overlay") or "none").upper() != "F":
        return base, {
            "applied": False,
            "strategies": {name: _strategy("NOT_APPLIED", reason="NO_COMPLEXITY_OVERLAY") for name in (
                "SPLIT_OR_SHORTEN", "SLOW_PROGRESSION", "REDUCE_ACTION_COUNT",
                "SEATED_OR_SUPPORTED", "REDUCE_COORDINATION_DEMAND", "INCREASE_SUPERVISION",
            )},
            "progression_policy": {"automatic_progression": True, "status": "UPSTREAM_DEFAULT"},
            "complexity_reduction": {"applied": False, "reasons": [], "what_was_reduced": {"action_count": False, "duration": False, "frequency": False, "coordination_demand": False, "equipment_demand": False}},
            "resistance_coverage": _resistance_coverage(base, reduced=False),
            "before_after_audit": {"base": _schedule_snapshot(base), "final": _schedule_snapshot(base)},
        }

    fact_reasons = [x for x in ("TIME_CONSTRAINT", "PAIN_LIMITATION") if x in complexity_trace.get("trigger_reasons", [])]
    if not fact_reasons:
        fact_reasons = ["COMPLEXITY_OVERLAY_F"]
    final = deepcopy(base)
    split_ids: set[str] = set()
    split_changes: list[dict[str, Any]] = []
    all_ids: set[str] = set()
    for day in final:
        for group in ("aerobic", "resistance", "flexibility", "functional_activity", "recovery", "warmup"):
            for action in day.get(group) or []:
                action_id = str(action.get("exercise_id") or action.get("action_id") or "")
                if not action_id:
                    continue
                original_range = action.get("duration_range") or action.get("candidate_dose") or action.get("dose")
                all_ids.add(action_id)
                if group == "aerobic" and not _supports_segmentation(action) and action_catalog:
                    # Prefer an already-declared alternative whose own dose
                    # metadata supports segmentation.  This is an existing
                    # catalogue substitution, not a new action or dose.
                    alternatives = action.get("alternative_ids") or action.get("alternative_action_ids") or []
                    replacement = next(
                        (
                            deepcopy(action_catalog[str(candidate)])
                            for candidate in alternatives
                            if str(candidate) in action_catalog and _supports_segmentation(action_catalog[str(candidate)])
                        ),
                        None,
                    )
                    if replacement is not None:
                        replacement["f_overlay_replaced_action_id"] = action_id
                        action.clear()
                        action.update(replacement)
                        all_ids.discard(action_id)
                        action_id = str(action.get("exercise_id") or action.get("action_id") or action_id)
                        all_ids.add(action_id)
                if group == "aerobic" and _supports_segmentation(action):
                    split_ids.add(action_id)
                    action["f_overlay_adjustment"] = {
                        "strategy": "SPLIT_OR_SHORTEN",
                        "original_allowed_range": original_range,
                        "selected_dose": action.get("duration_range") or action.get("candidate_dose") or action.get("dose"),
                        "selection_basis": "EXISTING_RANGE_WITH_SEGMENTATION_OR_DECLARED_ALTERNATIVE",
                        "overlay_reason": list(fact_reasons),
                    }
                action["progression_policy"] = {
                    "automatic_progression": False,
                    "status": "HOLD_FOR_REVIEW",
                    "reasons": ["COMPLEXITY_OVERLAY_F", *fact_reasons],
                }
    for action_id in sorted(split_ids):
        replacement_from = next(
            (
                action.get("f_overlay_replaced_action_id")
                for day in final
                for group in ("aerobic", "resistance", "flexibility", "functional_activity", "recovery", "warmup")
                for action in (day.get(group) or [])
                if str(action.get("exercise_id") or action.get("action_id")) == action_id
            ),
            None,
        )
        split_changes.append({"action_id": action_id, "replaced_action_id": replacement_from, "selection": "existing lower-bound/segmentation expression", "new_numeric_value": False})
    split_status = "APPLIED" if split_ids else "UNCERTAIN"
    strategies = {
        "SPLIT_OR_SHORTEN": _strategy(split_status, reasons=fact_reasons, source_support=["existing action duration_range/candidate_dose segmentation"], affected=sorted(split_ids), changes=split_changes, reason=None if split_ids else "NO_EXISTING_SEGMENTATION_RANGE"),
        "SLOW_PROGRESSION": _strategy("APPLIED", reasons=fact_reasons, source_support=["existing progression_rule; automatic progression held for review"], affected=sorted(all_ids), changes=[{"automatic_progression": False, "status": "HOLD_FOR_REVIEW"}]),
        "REDUCE_ACTION_COUNT": _strategy("NOT_APPLIED", reasons=fact_reasons, reason="NO_DETERMINISTIC_SOURCE_SUPPORTED_REDUCTION_RULE"),
        "SEATED_OR_SUPPORTED": _strategy("UNCERTAIN", reasons=[], reason="NO_EXPLICIT_BALANCE_OR_SUPPORT_FACT"),
        "REDUCE_COORDINATION_DEMAND": _strategy("UNCERTAIN", reasons=[], reason="NO_EXPLICIT_COORDINATION_LIMITATION_FACT"),
        "INCREASE_SUPERVISION": _strategy("UNCERTAIN", reasons=[], reason="NO_EXPLICIT_SUPERVISION_NEED_FACT"),
    }
    progression_policy = {
        "automatic_progression": False,
        "status": "HOLD_FOR_REVIEW",
        "reasons": ["COMPLEXITY_OVERLAY_F", *fact_reasons],
    }
    complexity_reduction = {
        "applied": True,
        "reasons": [*fact_reasons, "COMPLEXITY_OVERLAY_F"],
        "what_was_reduced": {
            "action_count": False,
            "duration": bool(split_ids),
            "frequency": False,
            "coordination_demand": False,
            "equipment_demand": False,
        },
        "duration_change_basis": "existing_range_with_segmentation" if split_ids else None,
    }
    return final, {
        "applied": True,
        "strategies": strategies,
        "progression_policy": progression_policy,
        "complexity_reduction": complexity_reduction,
        "resistance_coverage": _resistance_coverage(final, reduced=False),
        "before_after_audit": {"base": _schedule_snapshot(base), "final": _schedule_snapshot(final)},
    }


def _schedule_snapshot(schedule: list[dict[str, Any]]) -> dict[str, Any]:
    days = []
    for day in schedule:
        items = []
        for group in ("aerobic", "resistance", "flexibility", "functional_activity", "recovery", "warmup"):
            for action in day.get(group) or []:
                items.append({
                    "action_id": action.get("exercise_id") or action.get("action_id"),
                    "session_group": group,
                    "session_role": day.get(f"{group}_session_role"),
                    "duration_range": action.get("duration_range"),
                    "repetitions": action.get("repetitions"),
                    "sets": action.get("sets"),
                })
        days.append({"day": day.get("day"), "actions": items})
    return {"days": days}


def _resistance_coverage(schedule: list[dict[str, Any]], *, reduced: bool) -> dict[str, Any]:
    actual = sorted({str(action.get("exercise_id") or action.get("action_id")) for day in schedule for action in (day.get("resistance") or []) if action.get("exercise_id") or action.get("action_id")})
    status = "ADEQUATE" if actual and not reduced else "REDUCED_WITH_REASON" if actual else "UNKNOWN"
    return {
        "coverage_status": status,
        "domains_planned": ["RESISTANCE"] if actual else [],
        "domains_actually_covered": ["RESISTANCE"] if actual else [],
        "missing_domains": [],
        "reduction_reasons": [],
        "action_ids": actual,
    }
