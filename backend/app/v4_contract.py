"""Small, deterministic V4 phenotype contract.

This module is intentionally independent from the legacy V2 engine.  The
legacy ``phenotype_code`` remains available to callers while V4 consumers use
the explicit nutrition phenotype and complexity overlay fields below.
"""

from __future__ import annotations

import re
from typing import Any


PRIMARY_PHENOTYPES = frozenset({"A", "B", "C", "D", "E"})
OVERLAYS = frozenset({"F", "none"})
DISPLAY_PHENOTYPES = PRIMARY_PHENOTYPES | {"F"}
_NEGATIVE = {"无", "没有", "否", "none", "no", "无明显异常", "无明显困难", "无明显障碍"}
_COMPLEXITY_BARRIERS = {"不会操作设备", "无法独立执行", "执行障碍", "复杂共病管理"}
_EATING_DIFFICULTIES = {"早饱", "恶心", "呕吐", "腹胀", "腹泻", "便秘", "吞咽困难", "咀嚼困难", "反流"}


def _value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _items(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    for item in values:
        text = str(item.get("label") or item.get("code") if isinstance(item, dict) else item).strip()
        result.extend(part.strip() for part in re.split(r"[；;、,，]", text) if part.strip())
    return [item for item in result if item.lower() not in _NEGATIVE]


def _number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def derive_v4_phenotype(payload: dict[str, Any]) -> dict[str, Any]:
    """Derive V4's A–E nutrition phenotype plus optional F overlay.

    F is deliberately limited to multi-morbidity/execution complexity.  A
    routine education request is not a complexity overlay by itself.
    """
    payload = payload or {}
    height = _number(_value(payload, "height_cm", "q14_height"))
    weight = _number(_value(payload, "weight_kg", "q15_weight"))
    bmi = _number(_value(payload, "bmi"))
    if bmi is None and height and weight:
        bmi = weight / (height / 100) ** 2
    body_fat = _number(_value(payload, "body_fat_pct", "q18_bodyFat"))
    smi = _number(_value(payload, "smi", "q26_smi"))
    skeletal_muscle = _number(_value(payload, "q24_skeletalMuscle"))
    metabolic = _items(_value(payload, "metabolic_conditions", "q43_metabolicConditions"))
    barriers = _items(_value(payload, "execution_barriers", "q51_executionBarriers"))
    difficulties = set(_items(_value(payload, "q31_eatingDifficulties")))
    weight_change = str(_value(payload, "recent_weight_intake", "q28_weightChange") or "")
    intake = str(_value(payload, "q30_intake") or "")
    appetite = str(_value(payload, "q29_appetite") or "")
    diet = set(_items(_value(payload, "q34_dietPattern")))

    evidence_present = any(
        value is not None for value in (bmi, body_fat, smi, skeletal_muscle)
    ) or bool(metabolic or difficulties or weight_change or intake or appetite or diet or barriers)
    if not evidence_present:
        primary = None
        reasons = ["缺少可判定A–E的营养/体成分/摄入证据"]
    elif (
        "不明原因下降" in weight_change
        or "明显下降" in appetite
        or "减少50%" in intake
        or "几乎无法进食" in intake
    ):
        primary = "E"
        reasons = ["近期非意愿下降/摄入不足"]
    elif (
        (bmi is not None and bmi < 18.5)
        or bool(difficulties & _EATING_DIFFICULTIES)
        or "减少25%" in intake
        or "下降" in appetite
    ):
        primary = "D"
        reasons = ["低体重或营养风险"]
    else:
        low_muscle = (smi is not None and smi < 5.7) or (
            body_fat is not None and body_fat >= 35 and skeletal_muscle is not None and skeletal_muscle < 20
        ) or (skeletal_muscle is not None and skeletal_muscle < 18)
        if low_muscle or "长期节食" in diet or "蛋白质不足" in diet or (
            "疼痛限制" in barriers and "不知道怎么运动" in barriers
        ):
            primary = "C"
            reasons = ["高体脂伴肌肉/功能风险"]
        elif metabolic or (bmi is not None and bmi >= 28):
            primary = "B"
            reasons = ["肥胖或代谢异常"]
        else:
            primary = "A"
            reasons = ["超重/高体脂倾向"]

    complexity = "F" if len(metabolic) >= 4 or (
        len(metabolic) >= 3 and bool(set(barriers) & _COMPLEXITY_BARRIERS)
    ) else "none"
    if complexity == "F":
        reasons = [*reasons, "多重共病或执行复杂度达到F overlay条件"]
    display = "F" if complexity == "F" else primary
    contract = {
        "primary_nutrition_phenotype": primary,
        "complexity_overlay": complexity,
        "display_phenotype": display,
        "reasons": reasons,
        "source": "deterministic_v4_contract",
    }
    return validate_phenotype_contract(contract)


def validate_phenotype_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a V4 phenotype contract, raising on invalid state."""
    primary = contract.get("primary_nutrition_phenotype")
    overlay = contract.get("complexity_overlay")
    display = contract.get("display_phenotype")
    if primary is not None and primary not in PRIMARY_PHENOTYPES:
        raise ValueError("primary_nutrition_phenotype must be A-E or null")
    if overlay not in OVERLAYS:
        raise ValueError("complexity_overlay must be F or none")
    if overlay == "F" and primary is None:
        raise ValueError("F overlay requires an underlying A-E phenotype")
    expected_display = "F" if overlay == "F" else primary
    if display != expected_display:
        raise ValueError("display_phenotype is inconsistent with the V4 contract")
    return dict(contract)


build_phenotype_contract = derive_v4_phenotype
