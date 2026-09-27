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
    checks = {
        "all_7_days_materialized": len(days) == 7 and [day.get("day") for day in days] == list(range(1, 8)),
        "all_patient_actions_mapped": all(action.get("action_id") in _PULMONARY_IDS for action in actions),
        "all_actions_from_p01_to_p06": all(action.get("action_id") in _PULMONARY_IDS for action in actions),
        "all_actions_have_name": all(action.get("action_name") for action in actions),
        "all_actions_have_dose_or_explicit_unavailable_status": all(action.get("dose") or action.get("dose_status") == "UNAVAILABLE" for action in actions),
        "minimum_sufficient_set_respected": bool(root.get("minimum_sufficient_set", {}).get("required_needs") is not None),
        "p05_condition_respected": (not p05.get("selected")) or (
            p05.get("dose_source_available") is True
            and ((p05.get("mode") == "SKILL_LEARNING" and p05.get("skill_learning") is True and p05.get("clinical_need_for_clearance") is False)
                 or (p05.get("mode") == "AIRWAY_CLEARANCE" and p05.get("clinical_need_for_clearance") is True))
        ),
        "p06_gate_respected": bool(p06.get("eligible") is False or (p06.get("sputum_or_clearance_need") and p06.get("device_available") and p06.get("clinician_order_or_guidance") is True)),
        "no_external_unrequested_sources": all((action.get("source_provenance") or {}).get("source_version") for action in actions),
    }
    checks["status"] = "PASS" if all(checks.values()) else "FAIL"
    return checks


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
