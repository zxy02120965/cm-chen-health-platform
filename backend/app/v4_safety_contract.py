"""Deterministic V4 project-level Safety Contract Floor.

The existing clinical Safety Gate remains authoritative for clinical signals.
This module only applies the ACTIVE project workflow floor derived from the V4
nutrition phenotype and complexity overlay.  It intentionally introduces no
numeric clinical thresholds.
"""

from __future__ import annotations

from typing import Any, Iterable


_LEVEL_RANK = {"green": 0, "yellow": 1, "red": 2}
_FLOOR_REASONS = {
    "C": "MUSCLE_FUNCTION_RISK_REVIEW",
    "D": "NUTRITION_RISK_REVIEW",
    "F": "COMPLEXITY_EXECUTION_REVIEW",
}


def _normalize_level(value: Any) -> str:
    level = str(value or "green").strip().lower()
    if level not in _LEVEL_RANK:
        raise ValueError(f"unsupported safety level: {value!r}")
    return level


def _dedupe(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result


def apply_v4_safety_contract_floor(
    *,
    existing_safety_level: Any,
    existing_reason_codes: Iterable[Any] | None = None,
    primary_nutrition_phenotype: str | None,
    complexity_overlay: str | None,
) -> dict[str, Any]:
    """Apply the V4 minimum workflow Safety level without changing clinical rules.

    Severity is monotonic: RED and YELLOW are never downgraded.  C, D, and F
    only establish a minimum of YELLOW and contribute fixed audit reason codes.
    """

    existing = _normalize_level(existing_safety_level)
    reasons = _dedupe(existing_reason_codes or [])
    floor_sources: list[str] = []

    primary = str(primary_nutrition_phenotype or "").strip().upper()
    overlay = str(complexity_overlay or "none").strip()
    if primary in {"C", "D"}:
        reason = _FLOOR_REASONS[primary]
        if reason not in reasons:
            reasons.append(reason)
        floor_sources.append(f"primary_nutrition_phenotype:{primary}")
    if overlay == "F":
        reason = _FLOOR_REASONS["F"]
        if reason not in reasons:
            reasons.append(reason)
        floor_sources.append("complexity_overlay:F")

    required = "yellow" if floor_sources else "green"
    final = required if _LEVEL_RANK[required] > _LEVEL_RANK[existing] else existing
    return {
        "safety_level": final,
        "safety_reason_codes": reasons,
        "safety_floor_applied": bool(floor_sources),
        "safety_floor_raised": _LEVEL_RANK[final] > _LEVEL_RANK[existing],
        "safety_floor_sources": floor_sources,
    }

