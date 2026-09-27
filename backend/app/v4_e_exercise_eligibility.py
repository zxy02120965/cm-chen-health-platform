"""Deterministic E-phenotype formal-aerobic eligibility contract.

This module deliberately consumes explicit questionnaire semantics only.  It
does not invent BORG/6MWT/fatigue thresholds and it is only invoked for the E
nutrition phenotype.  The legacy exercise generator remains responsible for
action selection and dose text.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


INTAKE_STATES = {"STABLE", "REDUCED", "MARKEDLY_REDUCED", "UNKNOWN"}
WEIGHT_STATES = {"STABLE", "CONTINUING_LOSS", "UNKNOWN"}
FATIGUE_STATES = {"ACCEPTABLE", "LIMITED", "POOR", "UNKNOWN"}
BORG_STATES = {"ACCEPTABLE", "LIMITED", "UNKNOWN"}
ELIGIBILITY_STATES = {"DEFERRED_FOR_NUTRITION_RECOVERY", "ALLOWED_LOW_DOSE", "NOT_ASSESSED"}


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return "；".join(str(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}:{val}" for key, val in value.items())
    return "" if value is None else str(value)


def _first(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _intake_stability(payload: dict[str, Any]) -> str:
    value = _first(payload, "intake_stability", "q30_intake", "intake_status")
    text = _text(value).strip()
    if not text:
        return "UNKNOWN"
    if "减少50%" in text or "明显减少50%" in text:
        return "MARKEDLY_REDUCED"
    if text in {"正常", "稳定", "摄入稳定", "趋稳", "STABLE"}:
        return "STABLE"
    if "减少25%" in text or text in {"减少", "下降", "REDUCED"}:
        return "REDUCED"
    return "UNKNOWN"


def _weight_trend(payload: dict[str, Any]) -> str:
    value = _first(payload, "weight_trend", "q28_weightChange", "recent_weight_trend")
    text = _text(value).strip()
    if not text:
        return "UNKNOWN"
    if text in {"稳定", "无变化", "保持稳定", "STABLE"}:
        return "STABLE"
    # "不明原因下降" is a historical event, not proof of a continuing trend.
    if any(token in text for token in ("继续下降", "持续下降", "仍在下降", "进行性下降", "CONTINUING_LOSS")):
        return "CONTINUING_LOSS"
    return "UNKNOWN"


def _fatigue_recovery(payload: dict[str, Any]) -> str:
    value = _first(payload, "fatigue_recovery", "fatigue_status", "recovery_status")
    text = _text(value).strip()
    barriers = _text(_first(payload, "q51_executionBarriers", "execution_barriers"))
    text = "；".join(part for part in (text, barriers) if part)
    if not text:
        return "UNKNOWN"
    if any(token in text for token in ("明显疲劳", "严重疲劳", "恢复差", "恢复不良", "无法恢复", "POOR")):
        return "POOR"
    if any(token in text for token in ("疲劳", "恢复有限", "次日疲劳", "LIMITED")):
        return "LIMITED"
    if any(token in text for token in ("恢复良好", "无疲劳", "可接受", "ACCEPTABLE")):
        return "ACCEPTABLE"
    return "UNKNOWN"


def _borg_function_review(payload: dict[str, Any]) -> str:
    # Numeric BORG/6MWT values are intentionally not interpreted here: no
    # ACTIVE threshold is frozen for this phase.  An explicit normalized enum
    # may be supplied by a clinician-facing input in a later phase.
    value = _first(payload, "borg_function_review", "function_review")
    text = _text(value).strip().upper()
    if text in {"ACCEPTABLE", "LIMITED", "UNKNOWN"}:
        return text
    return "UNKNOWN"


def _safety(value: Any) -> str:
    text = _text(value).strip().upper()
    return text if text in {"GREEN", "YELLOW", "RED"} else "UNKNOWN"


def derive_e_formal_aerobic_eligibility(
    payload: dict[str, Any],
    *,
    safety_level: str | None,
    primary_nutrition_phenotype: str | None,
    existing_reason_codes: list[str] | None = None,
) -> dict[str, Any] | None:
    """Derive the E eligibility state without numeric clinical thresholds."""
    if primary_nutrition_phenotype != "E":
        return None
    intake = _intake_stability(payload)
    weight = _weight_trend(payload)
    fatigue = _fatigue_recovery(payload)
    borg = _borg_function_review(payload)
    safety = _safety(safety_level)
    reasons: list[str] = []
    if intake == "MARKEDLY_REDUCED":
        reasons.append("MARKEDLY_REDUCED_INTAKE")
    if weight == "CONTINUING_LOSS":
        reasons.append("CONTINUING_WEIGHT_LOSS")
    if fatigue == "POOR":
        reasons.append("POOR_RECOVERY")
    # A yellow label alone is not an exercise blocker.  Only explicit,
    # exercise-relevant Safety reason codes may contribute SAFETY_BURDEN.
    exercise_safety_codes = {
        "EXERCISE_STOP_REQUIRED",
        "RESPIRATORY_EXERCISE_REVIEW",
        "LOW_SPO2_EXERCISE_REVIEW",
        "EXERCISE_SYMPTOM_BURDEN",
        "CHEST_SYMPTOM_EXERCISE_REVIEW",
    }
    safety_burden = bool(set(existing_reason_codes or []) & exercise_safety_codes)
    if safety_burden:
        reasons.append("SAFETY_BURDEN")

    nutrition_blocker = any(code in reasons for code in ("MARKEDLY_REDUCED_INTAKE", "CONTINUING_WEIGHT_LOSS", "POOR_RECOVERY"))
    # A workflow YELLOW label is not, by itself, an exercise blocker.  Defer
    # only for explicit nutrition/recovery facts or an existing RED safety
    # state; exercise-specific Safety burden requires an explicit reason code.
    if nutrition_blocker or safety == "RED":
        if nutrition_blocker:
            reasons.append("NUTRITION_RECOVERY_PRIORITY")
        status = "DEFERRED_FOR_NUTRITION_RECOVERY"
    elif all(value != "UNKNOWN" for value in (intake, weight, fatigue, borg, safety)) and safety == "GREEN":
        status = "ALLOWED_LOW_DOSE"
    else:
        status = "NOT_ASSESSED"
    return {
        "phenotype": "E",
        "intake_stability": intake,
        "weight_trend": weight,
        "fatigue_recovery": fatigue,
        "borg_function_review": borg,
        "safety_level": safety,
        "status": status,
        "reasons": list(dict.fromkeys(reasons)),
        "source_trace": {
            "intake_stability": "intake_stability/q30_intake",
            "weight_trend": "weight_trend/q28_weightChange",
            "fatigue_recovery": "fatigue_recovery/fatigue_status/recovery_status/q51_executionBarriers",
            "borg_function_review": "borg_function_review/function_review (numeric q27 BORG/6MWT not thresholded)",
            "safety_level": "final_v4_safety_level",
            "safety_burden": "existing_reason_codes only; YELLOW alone is not sufficient",
        },
    }


def apply_e_eligibility_to_schedule(
    legacy_schedule: list[dict[str, Any]],
    eligibility: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply only the E deferred gate to the final legacy schedule.

    Existing aerobic sessions are removed when deferred.  No new action or
    dose is invented; an explicit functional/recovery category is preserved
    if the upstream candidate already supplied one.
    """
    schedule = deepcopy(legacy_schedule)
    combo_adjustment: dict[str, Any] = {}
    if eligibility.get("status") != "DEFERRED_FOR_NUTRITION_RECOVERY":
        return schedule, combo_adjustment
    for day in schedule:
        day["aerobic"] = []
        day["exercise"] = [
            *deepcopy(day.get("resistance") or []),
            *deepcopy(day.get("flexibility") or []),
            *deepcopy(day.get("functional_activity") or []),
            *deepcopy(day.get("recovery") or []),
            *deepcopy(day.get("warmup") or []),
        ]
        has_activity = bool(day["exercise"])
        day["is_training"] = has_activity
        day["training"] = has_activity
        day["rest_day"] = not has_activity
        if day.get("resistance"):
            day["day_type"] = "抗阻日"
        elif day.get("flexibility"):
            day["day_type"] = "柔韧日"
        elif day.get("functional_activity") or day.get("recovery"):
            day["day_type"] = "恢复日/日常活动"
        else:
            day["day_type"] = "恢复日/日常活动"
    combo_adjustment["formal_aerobic_days_target"] = 0
    combo_adjustment["functional_activity_days_target"] = ">0_or_as_tolerated"
    return schedule, combo_adjustment
