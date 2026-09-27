"""Canonical pulmonary trace adapter for the legacy V2 pulmonary catalogue.

The adapter deliberately keeps the existing P01-P06 selector and dose text as
the source of truth.  It adds an auditable V4 trace and compatibility
projections without promoting the legacy DRAFT catalogue to ACTIVE.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any


PULMONARY_TRACE_SCHEMA_VERSION = "PULMONARY_TRACE_V4_2"
_PULMONARY_IDS = tuple(f"P0{i}" for i in range(1, 7))


def _source_provenance(actions: list[dict[str, Any]]) -> dict[str, Any]:
    """Build provenance from the actual DOCX and parsed catalogue metadata."""
    try:
        from . import v2_knowledge

        source_name = next(
            (str(item.get("source_document")) for item in actions if item.get("source_document")),
            None,
        )
        source_path = None
        if source_name:
            candidate = v2_knowledge.RULES / source_name
            if candidate.exists():
                source_path = candidate
        if source_path is None:
            paths = sorted(v2_knowledge.RULES.glob("*肺预康复知识库*.docx"))
            source_path = paths[0] if paths else None
        if source_path is None:
            return {
                "source_asset": source_name,
                "source_path": None,
                "source_version": next((item.get("source_version") for item in actions if item.get("source_version")), "V2.0"),
                "sha256": None,
                "knowledge_status": "DRAFT",
                "mdt_confirmed": False,
                "provenance_status": "SOURCE_FILE_UNAVAILABLE",
            }
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        version = next((item.get("source_version") for item in actions if item.get("source_version")), None)
        status = next((item.get("status") or item.get("knowledge_status") for item in actions if item.get("status") or item.get("knowledge_status")), "DRAFT")
        return {
            "source_asset": source_path.name,
            "source_path": source_path.relative_to(v2_knowledge.ROOT).as_posix(),
            "source_version": version,
            "sha256": digest,
            "knowledge_status": status,
            "mdt_confirmed": all(bool(item.get("mdt_confirmed")) for item in actions) if actions else False,
            "provenance_status": "VERIFIED_FROM_RUNTIME_SOURCE_FILE",
        }
    except Exception:
        return {
            "source_asset": None,
            "source_path": None,
            "source_version": None,
            "sha256": None,
            "knowledge_status": "DRAFT",
            "mdt_confirmed": False,
            "provenance_status": "PROVENANCE_UNAVAILABLE",
        }


def _dose_status(action: dict[str, Any]) -> str:
    if action.get("pulmonary_id") == "P06":
        # The source deliberately defers OPEP dose to the device and clinician
        # order; it is not an executable numeric dose for this trace.
        return "UNAVAILABLE"
    return "PROVISIONAL" if action.get("candidate_dose") or action.get("dose_range") else "UNAVAILABLE"


def _action_for_trace(action: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(action)
    pid = str(item.get("pulmonary_id") or "")
    item["action_id"] = pid
    item["action_name"] = item.get("name") or item.get("action_name") or pid
    item["purpose"] = item.get("purpose")
    item["dose"] = item.get("candidate_dose") or item.get("dose_range")
    item["dose_status"] = _dose_status(item)
    item["source_version"] = item.get("source_version") or provenance.get("source_version")
    item["knowledge_status"] = item.get("status") or item.get("knowledge_status") or provenance.get("knowledge_status")
    item["mdt_confirmed"] = bool(item.get("mdt_confirmed", provenance.get("mdt_confirmed", False)))
    item["source_provenance"] = deepcopy(provenance)
    return item


def _context_snapshot(payload: dict[str, Any], safety_level: str, dose_status: str, overlay: str | None, p06_gate: dict[str, Any], p05_gate: dict[str, Any]) -> dict[str, Any]:
    symptoms = payload.get("q12_respiratorySymptoms", payload.get("respiratory_symptoms", [])) or []
    text = " ".join(str(value) for value in symptoms)
    dyspnea = any(token in text for token in ("气促", "呼吸节律", "呼吸困难"))
    sputum = any(token in text for token in ("咳痰", "痰液", "排痰", "分泌物"))
    return {
        "safety_level": safety_level,
        "pulmonary_dose_status": dose_status,
        "dyspnea_or_rhythm_issue": dyspnea,
        "sputum_present": sputum,
        "sputum_clearance_difficulty": sputum,
        "opep_device_available": bool(p06_gate.get("device_available")),
        "opep_clinician_order_or_guidance": bool(p06_gate.get("clinician_order_or_guidance", p06_gate.get("clinician_ordered"))),
        "surgery_window": payload.get("q6_surgeryWindow", payload.get("surgery_window")),
        "complexity_overlay": overlay or "none",
    }


def _minimum_sufficient_set(selected: list[dict[str, Any]], context: dict[str, Any], p03_indicated: bool, p04_indicated: bool, p06_gate: dict[str, Any]) -> dict[str, Any]:
    selected_ids = list(dict.fromkeys(str(item.get("pulmonary_id")) for item in selected if item.get("pulmonary_id")))
    omitted = [pid for pid in _PULMONARY_IDS if pid not in selected_ids]
    needs = ["BASE_BREATHING_CONTROL"]
    if context.get("dyspnea_or_rhythm_issue"):
        needs.append("DYSPNEA_OR_RHYTHM_CONTROL")
    if context.get("sputum_clearance_difficulty"):
        needs.append("AIRWAY_CLEARANCE")
    if p03_indicated:
        needs.append("THORACIC_EXPANSION")
    if p04_indicated:
        needs.append("BREATH_UPPER_LIMB_COORDINATION")
    reasons = {}
    if "P03" in omitted:
        reasons["P03"] = "NO_EXPLICIT_CLINICIAN_INDICATION"
    if "P04" in omitted:
        reasons["P04"] = "NO_EXPLICIT_CLINICIAN_INDICATION"
    if "P05" in omitted:
        reasons["P05"] = "NO_SKILL_LEARNING_OR_CLEARANCE_NEED"
    if "P06" in omitted:
        reasons["P06"] = "P06_THREE_PART_GATE_NOT_SATISFIED"
    return {
        "required_needs": needs,
        "selected_action_ids": selected_ids,
        "omitted_action_ids": omitted,
        "omission_reasons": reasons,
        "excessive_task_load_avoided": len(selected_ids) < len(_PULMONARY_IDS),
    }


def _validate_trace(root: dict[str, Any]) -> dict[str, Any]:
    days = root.get("daily_schedule") or []
    actions = [action for day in days for action in day.get("actions", [])]
    p05 = root.get("p05_gate") or {}
    p06 = root.get("p06_gate") or {}
    minimum = root.get("minimum_sufficient_set") or {}
    overlay = root.get("pulmonary_complexity_overlay") or {}
    overlay_consistent = True
    if root.get("context_snapshot", {}).get("complexity_overlay") == "F":
        strategy = (overlay.get("strategy") or {}).get("REDUCE_OPTIONAL_TASK_LOAD") or {}
        overlay_consistent = bool(overlay.get("overlay") == "F" and strategy.get("after_action_ids") == root.get("selected_action_ids"))
    checks = {
        "all_7_days_materialized": len(days) == 7 and [day.get("day") for day in days] == list(range(1, 8)),
        "all_patient_actions_mapped": all(action.get("action_id") in _PULMONARY_IDS for action in actions),
        "all_actions_from_p01_to_p06": all(action.get("action_id") in _PULMONARY_IDS for action in actions),
        "all_actions_have_name": all(action.get("action_name") for action in actions),
        "all_actions_have_dose_or_explicit_unavailable_status": all(action.get("dose") or action.get("dose_status") == "UNAVAILABLE" for action in actions),
        "minimum_sufficient_set_respected": bool(minimum.get("required_needs") is not None and minimum.get("selected_action_ids") == root.get("selected_action_ids")),
        "p05_condition_respected": (not p05.get("selected")) or (
            p05.get("dose_source_available") is True
            and ((p05.get("mode") == "SKILL_LEARNING" and p05.get("skill_learning") is True and p05.get("clinical_need_for_clearance") is False)
                 or (p05.get("mode") == "AIRWAY_CLEARANCE" and p05.get("clinical_need_for_clearance") is True))
        ),
        "p06_gate_respected": bool(p06.get("eligible") is False or (p06.get("sputum_or_clearance_need") and p06.get("device_available") and p06.get("clinician_order_or_guidance") is True)),
        "no_external_unrequested_sources": all((action.get("source_provenance") or {}).get("source_version") for action in actions),
        "f_overlay_consistent": overlay_consistent,
    }
    checks["status"] = "PASS" if all(checks.values()) else "FAIL"
    return checks


def _pulmonary_snapshot(root: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_action_ids": deepcopy(root.get("selected_action_ids") or []),
        "omitted_action_ids": deepcopy((root.get("minimum_sufficient_set") or {}).get("omitted_action_ids") or []),
        "daily_action_ids": {
            str(day.get("day")): [action.get("action_id") for action in day.get("actions", [])]
            for day in root.get("daily_schedule", [])
        },
        "p05_gate": deepcopy(root.get("p05_gate") or {}),
        "p06_gate": deepcopy(root.get("p06_gate") or {}),
        "dose": {
            action.get("action_id"): {"dose": action.get("dose"), "dose_status": action.get("dose_status")}
            for day in root.get("daily_schedule", [])
            for action in day.get("actions", [])
            if action.get("action_id")
        },
        "source_provenance": deepcopy(root.get("source_provenance") or {}),
    }


def apply_pulmonary_f_overlay(trace: dict[str, Any], complexity_trace: dict[str, Any] | None) -> dict[str, Any]:
    """Defer only optional P05 skill learning for an evidence-backed F overlay."""
    root = deepcopy(trace)
    base_snapshot = _pulmonary_snapshot(root)
    overlay = str((root.get("context_snapshot") or {}).get("complexity_overlay") or "none").upper()
    reasons = [str(reason) for reason in (complexity_trace or {}).get("trigger_reasons", []) if str(reason) != "EDUCATION_ONLY"] if overlay == "F" else []
    has_complexity_evidence = bool((complexity_trace or {}).get("material_execution_burden_present") or reasons)
    p05 = root.get("p05_gate") or {}
    p05_optional = bool(p05.get("selected") and p05.get("mode") == "SKILL_LEARNING" and not p05.get("sputum_or_clearance_need"))
    applied = overlay == "F" and has_complexity_evidence and p05_optional
    if applied:
        reasons = list(dict.fromkeys([*reasons, "COMPLEXITY_OVERLAY_F"]))
        for day in root.get("daily_schedule", []):
            day["actions"] = [action for action in day.get("actions", []) if action.get("action_id") != "P05"]
            day["empty_reason"] = None if day.get("actions") else "NO_PULMONARY_ACTIONS_SCHEDULED"
        root["selected_action_ids"] = [action_id for action_id in root.get("selected_action_ids", []) if action_id != "P05"]
        minimum = root.get("minimum_sufficient_set") or {}
        minimum["selected_action_ids"] = deepcopy(root["selected_action_ids"])
        minimum["omitted_action_ids"] = [action_id for action_id in _PULMONARY_IDS if action_id not in root["selected_action_ids"]]
        omission_reasons = minimum.setdefault("omission_reasons", {})
        omission_reasons["P05"] = "OPTIONAL_SKILL_LEARNING_DEFERRED_FOR_COMPLEXITY"
        minimum.setdefault("omission_reason_text", {})["P05"] = "无当前痰液/排痰需要；本周因复杂度、时间和疼痛执行负担，优先保留1–2个基础动作，P05技能学习延后复评。"
        root["minimum_sufficient_set"] = minimum
        root["p05_gate"] = {
            "selected": False,
            "mode": "NOT_SELECTED",
            "skill_learning": False,
            "clinical_need_for_clearance": False,
            "reason": "OPTIONAL_SKILL_LEARNING_DEFERRED_FOR_COMPLEXITY",
            "sputum_or_clearance_need": False,
            "dose_source_available": bool(p05.get("dose_source_available")),
        }
        root["manual_review_reasons"] = list(dict.fromkeys([*(root.get("manual_review_reasons") or []), "OPTIONAL_P05_SKILL_LEARNING_DEFERRED_FOR_COMPLEXITY"]))
    after_snapshot = _pulmonary_snapshot(root)
    root["base_pulmonary_before_f_overlay"] = base_snapshot
    root["final_pulmonary_after_f_overlay"] = after_snapshot
    root["pulmonary_complexity_overlay"] = {
        "overlay": "F" if overlay == "F" else "none",
        "applied": applied,
        "source_reasons": reasons,
        "strategy": {
            "REDUCE_OPTIONAL_TASK_LOAD": {
                "applicability": "APPLIED" if applied else "NOT_APPLIED",
                "before_action_ids": base_snapshot["selected_action_ids"],
                "after_action_ids": after_snapshot["selected_action_ids"],
                "removed_or_deferred_action_ids": ["P05"] if applied else [],
                "reasons": reasons + (["OPTIONAL_SKILL_LEARNING_DEFERRED_FOR_COMPLEXITY"] if applied else []),
            }
        },
        "unchanged_actions": ["P01", "P02"],
        "unsupported_strategies": {
            "dose_reduction": {"status": "NOT_APPLIED", "reason": "PULMONARY_DOSE_UNCHANGED"},
            "seated_or_supported": {"status": "NOT_APPLIED", "reason": "NO_EXPLICIT_SUPPORT_FACT"},
            "increased_supervision": {"status": "NOT_APPLIED", "reason": "NO_EXPLICIT_SUPERVISION_NEED"},
        },
        "permanent_exclusion": False,
    }
    root["trace_validation"] = _validate_trace(root)
    if root["trace_validation"]["status"] == "PASS":
        root["trace_materialization_status"] = "FULL"
        root["pulmonary_trace_full"] = True
    else:
        root["trace_materialization_status"] = "MISSING"
        root["pulmonary_trace_full"] = False
    return root


def build_pulmonary_trace(
    payload: dict[str, Any],
    selected_actions: list[dict[str, Any]],
    weekly_schedule: list[dict[str, Any]],
    *,
    safety_level: str,
    pulmonary_dose_status: str,
    selection_trace: dict[str, Any],
    complexity_overlay: str | None = None,
) -> dict[str, Any]:
    provenance = _source_provenance(selected_actions)
    context = _context_snapshot(payload, safety_level, pulmonary_dose_status, complexity_overlay, selection_trace.get("p06_gate", {}), selection_trace.get("p05_gate", {}))
    p05_gate = deepcopy(selection_trace.get("p05_gate") or {
        "selected": any(item.get("pulmonary_id") == "P05" for item in selected_actions),
        "mode": "NOT_SELECTED",
        "skill_learning": False,
        "clinical_need_for_clearance": False,
        "reason": None,
        "sputum_or_clearance_need": False,
        "dose_source_available": False,
    })
    legacy_p06_gate = selection_trace.get("p06_gate") or {}
    p06_gate = {
        "sputum_or_clearance_need": False,
        "device_available": False,
        "clinician_order_or_guidance": False,
        "eligible": False,
    }
    # Keep clinician_ordered as an internal selector key only.  The canonical
    # trace uses the frozen contract name clinician_order_or_guidance.
    p06_gate.update({
        "sputum_or_clearance_need": bool(legacy_p06_gate.get("sputum_or_clearance_need")),
        "device_available": bool(legacy_p06_gate.get("device_available")),
        "clinician_order_or_guidance": bool(legacy_p06_gate.get("clinician_order_or_guidance", legacy_p06_gate.get("clinician_ordered"))),
        "eligible": bool(legacy_p06_gate.get("eligible")),
    })
    traced_actions = [_action_for_trace(item, provenance) for item in selected_actions]
    by_key = {(item.get("pulmonary_id"), item.get("pulmonary_mode")): item for item in traced_actions}
    daily = []
    for day in range(1, 8):
        legacy = next((item for item in weekly_schedule if int(item.get("day", 0)) == day), {})
        actions = []
        for item in legacy.get("pulmonary_prehab", []) or []:
            key = (item.get("pulmonary_id"), item.get("pulmonary_mode"))
            actions.append(deepcopy(by_key.get(key) or _action_for_trace(item, provenance)))
        daily.append({"day": day, "actions": actions, "empty_reason": None if actions else "NO_PULMONARY_ACTIONS_SCHEDULED"})
    root = {
        "schema_version": PULMONARY_TRACE_SCHEMA_VERSION,
        "trace_materialization_status": "MISSING",
        "pulmonary_trace_full": False,
        "pulmonary_dose_status": pulmonary_dose_status,
        "context_snapshot": context,
        "source_provenance": provenance,
        "minimum_sufficient_set": _minimum_sufficient_set(traced_actions, context, bool(selection_trace.get("p03_indicated")), bool(selection_trace.get("p04_indicated")), p06_gate),
        "selected_action_ids": list(dict.fromkeys(item.get("pulmonary_id") for item in selected_actions if item.get("pulmonary_id"))),
        "blocked_action_ids": ["P06"] if not p06_gate.get("eligible") else [],
        "blocked_actions": ([{"action_id": "P06", "dose_status": "UNAVAILABLE", "reason": "P06_THREE_PART_GATE_NOT_SATISFIED"}] if not p06_gate.get("eligible") else []),
        "daily_schedule": daily,
        "p05_gate": p05_gate,
        "p06_gate": p06_gate,
        "manual_review_reasons": ["PULMONARY_SOURCE_DRAFT"],
    }
    validation = _validate_trace(root)
    root["trace_validation"] = validation
    if validation["status"] == "PASS":
        root["trace_materialization_status"] = "FULL"
        root["pulmonary_trace_full"] = True
    return root


def project_pulmonary_plan(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Project the canonical root back to the legacy flat patient field."""
    unique: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()
    for day in trace.get("daily_schedule", []):
        for action in day.get("actions", []):
            key = (action.get("pulmonary_id"), action.get("pulmonary_mode"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(deepcopy(action))
    return unique


def project_weekly_schedule(trace: dict[str, Any], weekly_schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_day = {int(day.get("day")): day for day in trace.get("daily_schedule", [])}
    projected = deepcopy(weekly_schedule)
    for day in projected:
        day_number = int(day.get("day", 0))
        day["pulmonary_prehab"] = deepcopy((by_day.get(day_number) or {}).get("actions", []))
    return projected
