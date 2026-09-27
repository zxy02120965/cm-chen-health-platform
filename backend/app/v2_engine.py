"""Deterministic V2.0/V2.1 clinical plan primitives with V3.0 exercise scheduling.

This module is deliberately conservative: numeric candidates from the reviewed
V2 documents are carried as candidate values and are only promoted to a
patient-facing prescription when an ACTIVE MDT configuration explicitly
authorises them.  It provides one contract for the rule generator and the
future AI gateway.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from itertools import product
from typing import Any
import re

Q56_PRIMARY = {
    "STANDARD_FAT_LOSS": "标准减脂",
    "ENHANCED_FAT_LOSS": "强化减脂",
    "WEIGHT_MAINTENANCE_MUSCLE_PRESERVATION": "体重维持/保肌",
    "NUTRITION_RECOVERY_WEIGHT_GAIN": "营养恢复/增重",
    "STOP_WEIGHT_LOSS": "停止继续下降",
    "MUSCLE_GAIN": "增肌",
    "METABOLIC_CONTROL": "代谢控制",
    "FUNCTION_IMPROVEMENT": "提高运动能力",
    "PULMONARY_IMPROVEMENT": "改善肺功能",
    "COMPREHENSIVE_PREOP": "术前综合准备",
}

AF_DEFAULTS = {
    "A": {"mode": "STANDARD_FAT_LOSS", "ratio": 0.85, "protein_g_per_kg": 1.2},
    "B": {"mode": "STANDARD_FAT_LOSS", "ratio": 0.80, "protein_g_per_kg": 1.2},
    "C": {"mode": "MUSCLE_PRESERVATION", "ratio": 1.00, "protein_g_per_kg": 1.5},
    "D": {"mode": "NUTRITION_RECOVERY", "ratio": 1.10, "protein_g_per_kg": 1.3},
    "E": {"mode": "STOP_WEIGHT_LOSS", "ratio": 1.15, "protein_g_per_kg": 1.5},
    "F": {"mode": "SAFE_EXECUTABLE", "ratio": 1.00, "protein_g_per_kg": 1.2},
}

# Values used by questionnaire controls to mean an explicit negative answer.
# Keep these separate from null/[] so missing information is never interpreted
# as a confirmed absence of disease or symptoms.
NEGATIVE_TOKENS = {"无", "没有", "否", "none", "no", "无明显异常", "无明显困难", "无明显障碍", "从不", "不饮"}
UNCERTAIN_TOKENS = {"不清楚", "未知", "不确定", "unknown", "uncertain"}


def normalize_selection(value: Any) -> dict[str, Any]:
    """Normalize a scalar/multi-select answer without changing persisted data."""
    if value is None:
        return {"state": "missing", "explicit_none": [], "uncertain": [], "positive_items": []}
    if isinstance(value, (list, tuple)):
        values = []
        for item in value:
            if isinstance(item, str) and any(sep in item for sep in ("；", ";", "、", ",", "，")):
                values.extend(part.strip() for part in re.split(r"[；;、,，]", item) if part.strip())
            else:
                values.append(item)
    elif isinstance(value, str) and any(sep in value for sep in ("；", ";", "、", ",", "，")):
        values = [part.strip() for part in re.split(r"[；;、,，]", value) if part.strip()]
    else:
        values = [value]
    if not values or all(v in (None, "") for v in values):
        return {"state": "empty", "explicit_none": [], "uncertain": [], "positive_items": []}
    explicit_none, uncertain, positive = [], [], []
    for item in values:
        text = str(item.get("label") or item.get("code") if isinstance(item, dict) else item).strip()
        lower = text.lower()
        if text in NEGATIVE_TOKENS or lower in NEGATIVE_TOKENS:
            explicit_none.append(item)
        elif text in UNCERTAIN_TOKENS or lower in UNCERTAIN_TOKENS:
            uncertain.append(item)
        else:
            positive.append(item)
    state = "explicit_none" if explicit_none and not positive and not uncertain else ("positive" if positive else "uncertain" if uncertain else "empty")
    return {"state": state, "explicit_none": explicit_none, "uncertain": uncertain, "positive_items": positive}


def normalize_payload_choices(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return normalization metadata for all choice-like questionnaire fields."""
    keys = [k for k, v in payload.items() if isinstance(v, (list, tuple, str))]
    return {key: normalize_selection(payload.get(key)) for key in keys}

FOODS = [
    {"component_id": "C002", "name": "糙米饭基础份", "ingredient_name": "糙米", "ingredient_amount": 50, "unit": "g", "raw_or_cooked_basis": "生重/干重", "cooking_method": "蒸煮", "kcal_estimate": 174, "protein_g": 3.9, "carbohydrate_g": 37.5, "fat_g": 1.4, "replacement_options": ["C001", "C003"], "knowledge_item_id": "C002", "knowledge_version": "V2.0", "tags": ["全谷", "标准减脂"]},
    {"component_id": "P001", "name": "清蒸鲈鱼", "ingredient_name": "鲈鱼、植物油", "ingredient_amount": "100g + 3g", "unit": "g", "raw_or_cooked_basis": "可食部/烹调油单列", "cooking_method": "清蒸", "kcal_estimate": 132, "protein_g": 18.6, "carbohydrate_g": 0, "fat_g": 6.4, "replacement_options": ["P003", "P008"], "knowledge_item_id": "P001", "knowledge_version": "V2.0", "tags": ["优质蛋白", "保肌"]},
    {"component_id": "V001", "name": "清炒西兰花", "ingredient_name": "西兰花、植物油", "ingredient_amount": "200g + 4g", "unit": "g", "raw_or_cooked_basis": "可食部/烹调油单列", "cooking_method": "少油炒", "kcal_estimate": 96, "protein_g": 6.0, "carbohydrate_g": 12.0, "fat_g": 4.0, "replacement_options": ["V002", "V003"], "knowledge_item_id": "V001", "knowledge_version": "V2.0", "tags": ["非淀粉蔬菜"]},
    {"component_id": "S001", "name": "无糖酸奶", "ingredient_name": "原味无糖酸奶", "ingredient_amount": 150, "unit": "g", "raw_or_cooked_basis": "包装净含量", "cooking_method": "即食", "kcal_estimate": 90, "protein_g": 6.0, "carbohydrate_g": 8.0, "fat_g": 3.0, "replacement_options": ["S002", "S003"], "knowledge_item_id": "S001", "knowledge_version": "V2.0", "tags": ["加餐", "保肌"]},
]

EXERCISES = {
    "A01": {"exercise_id": "A01", "name": "缓慢步行", "purpose": "低门槛建立活动习惯", "position": "平坦安全环境", "steps": "先慢走热身，保持自然呼吸，按耐受分段完成。", "duration_or_reps": None, "sets": None, "intensity": None, "rest": None, "frequency": None, "precautions": "保持安全环境，必要时有人陪同。", "stop_conditions": "胸痛、明显气促、头晕或不适立即停止并联系医护。", "alternatives": ["A03", "R04"], "video_id": None, "source_version": "V2.0", "mdt_confirmed": False},
    "A02": {"exercise_id": "A02", "name": "快步走", "purpose": "改善有氧耐力和功能", "position": "平坦安全环境", "steps": "慢走热身后进入可控步速，不屏气。", "duration_or_reps": None, "sets": None, "intensity": None, "rest": None, "frequency": None, "precautions": "仅在功能和安全状态允许时选择。", "stop_conditions": "胸痛、明显气促、头晕或不适立即停止并联系医护。", "alternatives": ["A04", "A01"], "video_id": None, "source_version": "V2.0", "mdt_confirmed": False},
    "R04": {"exercise_id": "R04", "name": "坐姿腿屈伸", "purpose": "低体能下肢功能与保肌", "position": "坐稳在椅子上", "steps": "缓慢伸膝至可耐受范围，再控制回位，避免甩腿。", "duration_or_reps": None, "sets": None, "intensity": None, "rest": None, "frequency": None, "precautions": "膝痛明显时停止。", "stop_conditions": "疼痛、胸闷、头晕或明显疲劳立即停止。", "alternatives": ["R05", "A01"], "video_id": None, "source_version": "V2.0", "mdt_confirmed": False},
}

PULMONARY = {
    "P01": {"pulmonary_id": "P01", "name": "缩唇呼吸", "purpose": "气促控制、延长呼气", "position": "坐位/半卧/站位，优先稳定体位", "steps": "鼻吸约2秒，缩唇缓慢呼气约4–6秒，不需用力。", "dose": None, "frequency": None, "indication": "气促或呼吸节律问题优先", "contraindication": "明显加重症状时转人工", "stop_conditions": "过度换气、头晕、胸痛或明显气促立即停止。", "equipment": None, "alternative": "P02", "video_id": None, "source_version": "V2.0", "mdt_confirmed": False},
    "P02": {"pulmonary_id": "P02", "name": "腹式呼吸", "purpose": "膈肌参与、呼吸控制", "position": "坐位或仰卧位", "steps": "一手胸前一手腹部，鼻吸腹起、口呼腹落，不强迫深吸。", "dose": None, "frequency": None, "indication": "基础呼吸控制", "contraindication": "明显不适时停止", "stop_conditions": "头晕、胸痛或呼吸困难加重立即停止。", "equipment": None, "alternative": "P01", "video_id": None, "source_version": "V2.0", "mdt_confirmed": False},
    "P03": {"pulmonary_id": "P03", "name": "胸廓扩张训练", "purpose": "胸廓活动与深吸气练习", "position": "坐位或站位，平衡差优先坐位", "steps": "配合双上肢外展/扩胸缓慢吸气，回位时呼气。", "dose": None, "frequency": None, "indication": "胸廓活动需求", "contraindication": "肩痛或胸痛明显时降级", "stop_conditions": "疼痛、头晕或明显气促立即停止。", "equipment": None, "alternative": "P04", "video_id": None, "source_version": "V2.0", "mdt_confirmed": False},
}

# Explicitly opt-in development profile.  It is never loaded by production
# request handlers; tests may pass it to build_v2_plan to exercise the full
# contract while MDT values/catalog entries are still PENDING in production.
V2_CANDIDATE_TEST_PROFILE = {
    "environment": "TEST_ONLY",
    "V2-REE-FORMULA": {"status": "ACTIVE", "ree_formula_id": "MSJ", "ree_formula_version": "V2-CANDIDATE", "cross_check_threshold": 0.20},
    "V2-PAL-RULE": {
        "status": "ACTIVE", "default": 1.40, "sedentary": 1.20, "light": 1.375, "moderate": 1.55,
        # Candidate mapping from the frozen V4 rule table.  It is deliberately
        # TEST_ONLY metadata until the hospital promotes PAL parameters.
        "candidate_by_functional_profile": {
            "high_borg_complexity": 1.30,
            "standard_functional": 1.35,
        },
    },
    "V2-AF-ENERGY-MODES": {"status": "ACTIVE", "environment": "TEST_ONLY", "modes": deepcopy(AF_DEFAULTS)},
    "V2-PROTEIN-MACROS": {"status": "ACTIVE", "environment": "TEST_ONLY", "protein_source": "AF_DEFAULT_CANDIDATE"},
    # These ranges are copied from the reviewed V2 documents.  They are
    # intentionally TEST_ONLY candidates and never become production values.
    "V2-MACRO-CANDIDATES": {"status": "ACTIVE", "environment": "TEST_ONLY", "carbohydrate_pct_range": [50, 65], "fat_pct_range": None, "source": "营养与能量计算规则V2.0"},
    "V2-MEAL-DISTRIBUTION": {"status": "ACTIVE", "environment": "TEST_ONLY", "distribution_pct_range": {"breakfast": [25, 30], "lunch": [30, 40], "dinner": [30, 35], "snack": [5, 15]}, "source": "营养与能量计算规则V2.0"},
}

# V3.0 weekly-combination rules.  These are copied from the reviewed V3
# document; dose strings themselves come from the V3 action catalogue.  They
# remain candidate/DRAFT metadata until an MDT configuration is promoted.
V3_RULE_VERSION = "V3.0"
V3_WEEKLY_RULES = {
    "A": {"aerobic_days": (4, 5), "resistance_days": (2, 3), "resistance_actions": (4, 6), "flexibility_actions": (2, 4)},
    "B": {"aerobic_days": (3, 5), "resistance_days": (2, 3), "resistance_actions": (4, 6), "flexibility_actions": (2, 4)},
    "C": {"aerobic_days": (3, 5), "resistance_days": (2, 3), "resistance_actions": (4, 6), "flexibility_actions": (2, 4)},
    "D": {"aerobic_days": (3, 5), "resistance_days": (2, 3), "resistance_actions": (3, 5), "flexibility_actions": (1, 2)},
    "E": {"aerobic_days": (2, 3), "resistance_days": (2, 3), "resistance_actions": (2, 4), "flexibility_actions": (1, 2)},
    "F": {"aerobic_days": (1, 3), "resistance_days": (1, 3), "resistance_actions": (1, 3), "flexibility_actions": (0, 1)},
}


def _v3_action_copy(item: dict[str, Any], *, session_index: int | None = None) -> dict[str, Any]:
    """Expose a stable action contract while preserving source catalogue data."""
    out = deepcopy(item)
    out.setdefault("dose", out.get("candidate_dose") or out.get("duration_range") or out.get("reps_range"))
    out.setdefault("frequency", out.get("candidate_frequency") or out.get("frequency_range"))
    if not out.get("alternative_ids"):
        alternatives = {
            "A02": ["A04", "A01"], "A05": ["A04", "A02"], "A06": ["A04", "A01"],
            "L01": ["R04", "L05"], "L02": ["R04", "L05"], "L03": ["R04", "R03"],
            "L06": ["R04", "L05"], "U01": ["R01", "R03"], "U02": ["R03", "R02"],
            "U03": ["R03", "R01"], "U04": ["R01", "R03"], "C02": ["C01"],
        }
        out["alternative_ids"] = alternatives.get(str(out.get("exercise_id")), [])
    if session_index is not None:
        out["session_index"] = session_index
    return out


def build_v3_weekly_exercise(
    catalog: dict[str, dict[str, Any]],
    phenotype: str,
    *,
    restrictions: set[str] | None = None,
    safety_level: str = "green",
    pulmonary: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Generate a Day1-Day7 V3 combination from catalogue IDs only.

    The function never invents an action or dose.  If restrictions leave too
    few actions for a documented combination, the schedule records a manual
    review reason and the validator can reject it.
    """
    rules = V3_WEEKLY_RULES.get(phenotype, V3_WEEKLY_RULES["F"])
    restrictions = restrictions or set()
    all_items = {k: v for k, v in catalog.items() if v}
    def allowed(eid: str) -> bool:
        x = all_items.get(eid)
        if not x:
            return False
        text = " ".join(str(x.get(k) or "") for k in ("name", "functional_level", "indications"))
        if "膝痛" in restrictions or "髋痛" in restrictions:
            if eid in {"L01", "L02", "L03", "L06"}: return False
        if "腰痛" in restrictions and eid in {"L03", "C02"}: return False
        if "肩痛" in restrictions and eid in {"U01", "U02", "U04", "R01", "R02"}: return False
        if "平衡差" in restrictions and (eid.startswith("U") or eid.startswith("L")):
            return False
        return True
    aerobic_ids = [x for x in ("A02", "A04", "A05", "A03", "A01") if allowed(x)]
    if phenotype in {"D", "E", "F"}:
        aerobic_ids = [x for x in ("A01", "A03", "A04", "A02") if allowed(x)]
    # Cover upper push/pull, knee-dominant lower body and calf/ankle.  The
    # order is deterministic and alternatives are still surfaced to review.
    resistance_groups = [("R02", "U02", "R01"), ("U03", "U04", "R03"), ("L01", "L06", "R04"), ("L05", "R05"), ("C01",)]
    resistance_ids: list[str] = []
    for group in resistance_groups:
        pick = next((eid for eid in group if allowed(eid) and eid in all_items), None)
        if pick: resistance_ids.append(pick)
    # Add a second lower/upper option where the documented 4-6 range requires
    # it, without exceeding the number of catalogue actions.
    for eid in ("U01", "L04", "R03", "R04", "R05", "C01"):
        if len(resistance_ids) >= rules["resistance_actions"][1]: break
        if eid not in resistance_ids and allowed(eid) and eid in all_items: resistance_ids.append(eid)
    flex_ids = [eid for eid in ("S01", "S02", "S05", "S06", "S07", "S08") if allowed(eid) and eid in all_items]
    # Use the documented upper cadence for a stable weekly candidate while
    # spacing sessions on odd days (no consecutive high-load days).
    res_day_count = 3 if phenotype in {"A", "B", "C"} else 2 if phenotype in {"D", "E"} else 1
    res_days = list(range(1, 8, 2))[:res_day_count]
    aero_days = list(range(1, rules["aerobic_days"][1] + 1))
    if phenotype in {"A", "B", "C"}:
        # Spread the five aerobic sessions across the week so the first three
        # days do not carry most of the combined aerobic/resistance load.
        aero_days = [1, 2, 4, 5, 6] if rules["aerobic_days"][1] >= 5 else [1, 2, 4, 5]
    if safety_level == "yellow":
        res_days = res_days[: max(1, min(2, len(res_days)))]
        aero_days = aero_days[: max(1, min(3, len(aero_days)))]
    if safety_level == "red":
        res_days, aero_days = [], []
    schedule: list[dict[str, Any]] = []
    flat: list[dict[str, Any]] = []
    manual: list[str] = []
    min_actions = rules["resistance_actions"][0]
    if res_days and len(resistance_ids) < min_actions:
        manual.append(f"V3抗阻组合需要至少{min_actions}个动作，当前限制后仅有{len(resistance_ids)}个")
    for day in range(1, 8):
        is_training = day in aero_days or day in res_days
        aero = []
        if day in aero_days and aerobic_ids:
            # Rotate at least two feasible forms when the catalogue allows.
            aid = aerobic_ids[(aero_days.index(day)) % len(aerobic_ids)]
            aero = [_v3_action_copy(all_items[aid], session_index=aero_days.index(day) + 1)]
            flat.extend(aero)
        resistance = []
        if day in res_days:
            session = res_days.index(day) + 1
            resistance = [_v3_action_copy(all_items[eid], session_index=session) for eid in resistance_ids[: rules["resistance_actions"][1]]]
            flat.extend(resistance)
        flexibility = []
        if day in res_days:
            flexibility = [_v3_action_copy(all_items[eid]) for eid in flex_ids[: rules["flexibility_actions"][1]]]
            flat.extend(flexibility)
        # Skill-learning items (currently P05_EDUCATION) are scheduled as a
        # one-time weekly task, not copied into all seven daily task lists.
        day_pulmonary = [
            deepcopy(item) for item in (pulmonary or [])
            if item.get("requires_daily_task", True) or day == 1
        ]
        schedule.append({
            "day": day, "is_training": is_training, "training": is_training,
            "rest_day": not is_training,
            "day_type": "有氧+抗阻" if day in aero_days and day in res_days else "有氧日" if day in aero_days else "抗阻日" if day in res_days else "恢复日/日常活动",
            "aerobic": aero, "resistance": resistance, "flexibility": flexibility,
            "exercise": [*aero, *resistance, *flexibility],
            "pulmonary_prehab": day_pulmonary,
            "session_index": (res_days.index(day) + 1 if day in res_days else None),
            "stop_conditions": "出现胸痛、胸闷、明显气促、头晕、咯血或其他不适立即停止并联系医护。",
        })
    unique_flat: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in flat:
        key = str(item.get("exercise_id") or item.get("item_id"))
        if key not in seen:
            seen.add(key)
            unique_flat.append(item)
    combo = {
        "rule_version": V3_RULE_VERSION, "phenotype": phenotype,
        "aerobic_days_target": rules["aerobic_days"], "resistance_days_target": rules["resistance_days"],
        "resistance_actions_per_session": rules["resistance_actions"],
        "aerobic_rotation_min_types": min(2, len(set(aerobic_ids))),
        "resistance_days": res_days, "aerobic_days": aero_days,
        "allowed_action_ids": sorted(set(aerobic_ids + resistance_ids + flex_ids)),
        "alternative_action_ids": sorted({alt for item in unique_flat for alt in (item.get("alternative_ids") or [])}),
        "weekly_stop_rules": ["V3安全规则覆盖训练进阶"],
        "safety_adjustment": "黄色状态降低训练频率并冻结自动进阶；红色状态停止运动任务。" if safety_level in {"yellow", "red"} else None,
        "manual_review_reasons": manual,
    }
    return unique_flat, schedule, combo

def candidate_test_profile() -> dict[str, Any]:
    """Return a deep copy with V2 catalog items for TEST_ONLY regression."""
    profile = deepcopy(V2_CANDIDATE_TEST_PROFILE)
    try:
        from .v2_knowledge import structured_catalog
        catalog = structured_catalog()
        profile["V2-FOOD-COMPONENTS"] = {"status": "ACTIVE", "environment": "TEST_ONLY", "ids": [x["component_id"] for x in catalog["FOOD"]], "items": catalog["FOOD"]}
        profile["V2-EXERCISE-ACTIONS"] = {"status": "ACTIVE", "environment": "TEST_ONLY", "ids": [x["exercise_id"] for x in catalog["EXERCISE"]], "items": catalog["EXERCISE"]}
        profile["V2-PULMONARY-ACTIONS"] = {"status": "ACTIVE", "environment": "TEST_ONLY", "ids": [x["pulmonary_id"] for x in catalog["PULMONARY"]], "items": catalog["PULMONARY"]}
    except Exception:
        profile["V2-FOOD-COMPONENTS"] = {"status": "ACTIVE", "environment": "TEST_ONLY", "ids": list(_food_by_id)}
        profile["V2-EXERCISE-ACTIONS"] = {"status": "ACTIVE", "environment": "TEST_ONLY", "ids": list(EXERCISES)}
        profile["V2-PULMONARY-ACTIONS"] = {"status": "ACTIVE", "environment": "TEST_ONLY", "ids": list(PULMONARY)}
    return profile

# The V2 catalog keeps the complete reviewed identifier space available for
# lookup.  Entries without a fully approved dose remain explicit DRAFT
# placeholders; they are never silently promoted into a prescription.
_FOOD_IDS = [f"C{i:03d}" for i in range(1, 13)] + [f"P{i:03d}" for i in range(1, 16)] + [f"V{i:03d}" for i in range(1, 13)] + [f"S{i:03d}" for i in range(1, 11)]
_food_by_id = {item["component_id"]: item for item in FOODS}
for _fid in _FOOD_IDS:
    if _fid not in _food_by_id:
        _food_by_id[_fid] = {"component_id": _fid, "name": f"{_fid} 食谱组件（待审核）", "ingredient_name": None, "ingredient_amount": None, "unit": None, "raw_or_cooked_basis": None, "cooking_method": None, "kcal_estimate": None, "protein_g": None, "carbohydrate_g": None, "fat_g": None, "replacement_options": [], "knowledge_item_id": _fid, "knowledge_version": "V2.0", "tags": [], "status": "DRAFT", "mdt_confirmed": False}
FOODS = list(_food_by_id.values())

_EXERCISE_IDS = ["A01", "A02", "A03", "A04", "A05", "A06", "C01", "C02", "L01", "L02", "L03", "L04", "L05", "L06", "R01", "R02", "R03", "R04", "R05", "S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "U01", "U02", "U03", "U04"]
for _eid in _EXERCISE_IDS:
    EXERCISES.setdefault(_eid, {"exercise_id": _eid, "name": f"{_eid} 术前动作（待审核）", "category": "术前", "purpose": None, "position": None, "steps": None, "duration_or_reps": None, "sets": None, "intensity": None, "rest": None, "frequency": None, "precautions": "仅在医护审核后执行。", "stop_conditions": "出现不适立即停止并联系医护。", "alternatives": [], "video_id": None, "source_version": "V2.0", "mdt_confirmed": False, "status": "DRAFT"})
for _pid, _name in {"P04": "呼吸-上肢协同", "P05": "有效咳嗽", "P06": "设备辅助呼吸训练"}.items():
        PULMONARY.setdefault(_pid, {"pulmonary_id": _pid, "name": _name, "purpose": None, "position": None, "steps": None, "dose": None, "frequency": None, "indication": None, "contraindication": None, "stop_conditions": "出现气促、头晕、胸痛或咯血立即停止。", "equipment": "医护指定设备" if _pid == "P06" else None, "alternative": None, "video_id": None, "source_version": "V2.0", "requires_clinician_order": _pid == "P06", "mdt_confirmed": False, "status": "DRAFT"})

# Enrich the identifier maps from the reviewed DOCX catalogue when the
# project docs are present.  The fallback maps above keep the API usable when
# packaged without documentation files.
try:
    from .v2_knowledge import structured_catalog as _structured_catalog
    _catalog = _structured_catalog()
    if len(_catalog.get("FOOD", [])) >= 49:
        FOODS = _catalog["FOOD"]
    if len(_catalog.get("EXERCISE", [])) >= 31:
        EXERCISES = {x["exercise_id"]: x for x in _catalog["EXERCISE"]}
    if len(_catalog.get("PULMONARY", [])) >= 6:
        PULMONARY = {x["pulmonary_id"]: x for x in _catalog["PULMONARY"]}
except Exception as exc:
    # Do not mask an invalid/missing V1.7 FOOD authority with the legacy
    # hard-coded menu.  The caller must see an explicit startup/data error.
    raise RuntimeError("无法加载正式 V1.7 FOOD catalog，已阻止旧数据源回退") from exc


def _value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def parse_q56(value: Any) -> dict[str, Any]:
    if not value or value in ("未设定", "未设置"):
        return {"has_clinician_goal": False}
    if isinstance(value, dict):
        result = dict(value)
        result.setdefault("has_clinician_goal", bool(result.get("primary_goal")))
        return result
    # Accept concise synthetic-case notation while preserving unknown fields.
    text = str(value)
    goal = next((key for key, label in Q56_PRIMARY.items() if key in text or label in text), None)
    return {"has_clinician_goal": bool(goal), "primary_goal": goal, "raw_text": text}


def calculate_phenotype(payload: dict[str, Any]) -> tuple[str, list[str]]:
    """Single A-F phenotype calculation entry point.

    Assessment persistence, profile/result snapshots, API presentation and
    plan generation all receive the evaluation produced by ``assess_payload``
    which delegates here.  Keep the old private name as a compatibility alias
    for existing tests/importers, but do not maintain a second algorithm.
    """
    bmi = _value(payload, "bmi")
    if bmi is None:
        h, w = _value(payload, "q14_height", "height_cm"), _value(payload, "q15_weight", "weight_kg")
        try: bmi = float(w) / (float(h) / 100) ** 2 if h and w else None
        except (TypeError, ValueError, ZeroDivisionError): bmi = None
    try: bmi = float(bmi) if bmi is not None else None
    except (TypeError, ValueError): bmi = None
    body_fat = _value(payload, "q18_bodyFat", "body_fat_pct")
    smi = _value(payload, "q26_smi", "smi")
    metabolic_norm = normalize_selection(_value(payload, "q43_metabolicConditions", "metabolic_conditions"))
    metabolic = metabolic_norm["positive_items"]
    weight_change = str(_value(payload, "q28_weightChange", "recent_weight_intake") or "")
    intake = str(_value(payload, "q30_intake") or "")
    diet_norm = normalize_selection(_value(payload, "q34_dietPattern"))
    diet = diet_norm["positive_items"]
    barriers_norm = normalize_selection(_value(payload, "q51_executionBarriers", "execution_barriers"))
    barriers = barriers_norm["positive_items"]
    appetite = str(_value(payload, "q29_appetite") or "")
    difficulties = normalize_selection(_value(payload, "q31_eatingDifficulties"))["positive_items"]
    modifiers: list[str] = []
    if "不明原因下降" in weight_change or "明显下降" in appetite or "减少50%" in intake or "几乎无法进食" in intake:
        return "E", ["近期非意愿下降/摄入不足"]
    if (bmi is not None and bmi < 18.5) or any(x in {"早饱", "恶心", "呕吐", "腹胀", "腹泻", "便秘", "吞咽困难", "咀嚼困难", "反流"} for x in difficulties) or "减少25%" in intake or "下降" in appetite:
        return "D", ["低体重或营养风险"]
    try: low_muscle = (float(smi) < 5.7 if smi is not None else False) or (float(body_fat) >= 35 and float(_value(payload, "q24_skeletalMuscle") or 999) < 20)
    except (TypeError, ValueError): low_muscle = False
    try:
        low_muscle = low_muscle or float(_value(payload, "q24_skeletalMuscle") or 999) < 18
    except (TypeError, ValueError):
        pass
    if low_muscle or "长期节食" in diet or "蛋白质不足" in diet or (len(metabolic) < 4 and "疼痛限制" in barriers and "不知道怎么运动" in barriers and _value(payload, "q27_walkTest") in (None, "", "未做（选填缺失）")):
        return "C", ["高体脂伴肌肉/功能风险"]
    if len(metabolic) >= 4 or (len(metabolic) >= 3 and "不会操作设备" in barriers):
        return "F", ["复杂共病或执行障碍"]
    if metabolic or (bmi is not None and bmi >= 28):
        return "B", ["肥胖或代谢异常"]
    if body_fat is not None: modifiers.append("高体脂")
    return "A", modifiers or ["超重/高体脂倾向"]


def _phenotype(payload: dict[str, Any]) -> tuple[str, list[str]]:
    """Backward-compatible alias for the unified phenotype calculator."""
    return calculate_phenotype(payload)


def _safety(payload: dict[str, Any], liver: dict[str, Any]) -> tuple[str, list[str]]:
    symptoms = set(normalize_selection(_value(payload, "q12_respiratorySymptoms", "respiratory_symptoms"))["positive_items"])
    reasons: list[str] = []
    if symptoms.intersection({"咯血", "胸痛", "胸闷", "静息气促", "明显胸痛"}):
        reasons.append("呼吸/胸部红色症状")
    walk = _value(payload, "q27_walkTest") or {}
    try:
        spo2 = float(str(walk.get("spo2", "")).split("-")[0].replace("%", "")) if isinstance(walk, dict) and walk.get("spo2") else None
    except (TypeError, ValueError): spo2 = None
    if spo2 is not None and spo2 < 92: reasons.append("6分钟步行血氧偏低")
    if liver.get("review"): reasons.append("肝弹性提示需专科/MDT复核")
    if reasons and any("红色" in x or "胸部红色" in x for x in reasons): return "red", reasons
    if reasons or symptoms: return "yellow", reasons or ["存在呼吸症状"]
    return "green", []


def energy_trace(payload: dict[str, Any], phenotype: str, goal: dict[str, Any], safety_level: str, *, active_configs: dict[str, Any] | None = None) -> dict[str, Any]:
    active_configs = active_configs or {}
    formula_cfg = active_configs.get("REE_FORMULA_ID") or active_configs.get("V2-REE-FORMULA") or {}
    pal_cfg = active_configs.get("PAL_MAP") or active_configs.get("V2-PAL-RULE") or {}
    formula_id = formula_cfg.get("ree_formula_id") if isinstance(formula_cfg, dict) else None
    formula_status = formula_cfg.get("status", "ACTIVE") if isinstance(formula_cfg, dict) else "PENDING"
    pal_map = pal_cfg if isinstance(pal_cfg, dict) else {}
    weight = _value(payload, "q15_weight", "weight_kg")
    try: weight = float(weight) if weight is not None else None
    except (TypeError, ValueError): weight = None
    bia = _value(payload, "q22_bmr", "bia_bmr")
    try: bia = float(bia) if bia is not None else None
    except (TypeError, ValueError): bia = None
    measured = _value(payload, "measured_ree_kcal", "measured_REE", "measured_ree")
    try: measured = float(measured) if measured is not None else None
    except (TypeError, ValueError): measured = None
    age = _value(payload, "age_years", "age")
    if age is None:
        birth_date = _value(payload, "birth_date", "birthDate")
        try:
            born = date.fromisoformat(str(birth_date)[:10])
            today = date.today()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except (TypeError, ValueError):
            age = None
    try: age = float(age) if age is not None else None
    except (TypeError, ValueError): age = None
    sex = str(_value(payload, "sex", "profile_sex") or "")
    ratio = AF_DEFAULTS.get(phenotype, AF_DEFAULTS["F"])["ratio"]
    mode = goal.get("primary_goal") if goal.get("has_clinician_goal") else AF_DEFAULTS.get(phenotype, AF_DEFAULTS["F"])["mode"]
    if mode == "ENHANCED_FAT_LOSS":
        eligible = phenotype in {"A", "B"} and safety_level == "green" and str(_value(payload, "q6_surgeryWindow") or "") not in {"2周以内"}
        ratio = 0.80 if phenotype == "A" else 0.75
        if not eligible: mode, ratio = "STANDARD_FAT_LOSS", AF_DEFAULTS.get(phenotype, AF_DEFAULTS["F"])["ratio"]
    if mode in {"WEIGHT_MAINTENANCE_MUSCLE_PRESERVATION", "MUSCLE_GAIN"}: ratio = 1.0
    if mode in {"NUTRITION_RECOVERY_WEIGHT_GAIN"}: ratio = 1.10
    if mode == "STOP_WEIGHT_LOSS": ratio = 1.15
    # P1 measured REE > P2 approved formula + PAL > P3 BIA cross-check > P4 range.
    predicted = None
    formula_callable = formula_status == "ACTIVE" or formula_status == "CANDIDATE"
    if formula_id and formula_callable and str(formula_id).upper() in {"MSJ", "MIFFLIN_ST_JEOR"} and weight and age is not None:
        # Formula is deliberately invoked only when selected by ACTIVE config.
        predicted = 10 * weight + (6.25 * float(_value(payload, "q14_height", "height_cm") or 0)) - 5 * age + (5 if sex in {"男", "M", "male"} else -161)
    pal = None
    pal_source = None
    pal_status = "UNAVAILABLE"
    activity = str(_value(payload, "activity_level", "q35_exerciseFrequency") or "default")
    explicit_candidate_pal = _value(payload, "pal_candidate", "candidate_pal", "provisional_pal")
    if explicit_candidate_pal is not None:
        try:
            pal = float(explicit_candidate_pal)
            pal_source = "PAYLOAD_CANDIDATE_PAL"
            pal_status = "CANDIDATE"
        except (TypeError, ValueError):
            pal = None
    candidate_functional_map = pal_map.get("candidate_by_functional_profile") if isinstance(pal_map, dict) else None
    if pal is None and isinstance(candidate_functional_map, dict):
        walk_text = str(_value(payload, "q27_walkTest", "six_minute_walk_m") or "")
        borg_match = re.search(r"BORG\s*[=:：]\s*(\d+(?:\.\d+)?)", walk_text, flags=re.IGNORECASE)
        borg = float(borg_match.group(1)) if borg_match else None
        profile_key = (
            "high_borg_complexity"
            if borg is not None and borg >= 5 and phenotype in {"B", "F"}
            else "standard_functional"
            if borg is not None
            else None
        )
        if profile_key and candidate_functional_map.get(profile_key) is not None:
            pal = float(candidate_functional_map[profile_key])
            pal_source = "Q27_FUNCTIONAL_CAPACITY_CANDIDATE_MAPPING"
            pal_status = "CANDIDATE"
    if pal is None and pal_map and pal_map.get(activity) is not None:
        pal = float(pal_map[activity])
        pal_source = "CONFIG_ACTIVITY_LEVEL"
        pal_status = "ACTIVE" if formula_status == "ACTIVE" and pal_map.get("status") == "ACTIVE" else "CANDIDATE"
    if pal is None and pal_map.get("default") is not None:
        pal = float(pal_map["default"])
        pal_source = "CONFIG_DEFAULT_CANDIDATE" if pal_status != "ACTIVE" else "CONFIG_DEFAULT"
        pal_status = "ACTIVE" if formula_status == "ACTIVE" and pal_map.get("status") == "ACTIVE" else "CANDIDATE"
    tee = None
    source = "P4_KCAL_PER_KG_RANGE"
    ree_value = None
    test_only_profile = active_configs.get("environment") == "TEST_ONLY"
    # In TEST_ONLY profiles a valid P3 BIA/BMR takes precedence over the
    # candidate formula.  If no P3 measurement exists, retain the historical
    # formula path so sparse legacy fixtures still exercise their P2 contract.
    formula_primary_allowed = formula_status == "ACTIVE" and (not test_only_profile or bia is None)
    if measured is not None:
        source, ree_value = "P1_MEASURED_REE", measured
        tee = round(measured * pal, 1) if pal is not None else None
    elif predicted is not None and pal is not None and formula_primary_allowed:
        source, ree_value, tee = "P2_APPROVED_FORMULA", predicted, round(predicted * pal, 1)
    elif bia is not None and pal is not None:
        source, ree_value, tee = "P3_BIA_BMR_TEMP", bia, round(bia * pal, 1)
    ref_min, ref_max = ((25 * weight, 30 * weight) if weight is not None else (None, None))
    consistency = "INSUFFICIENT_DATA"
    conflict = False
    if tee is not None and ref_min is not None:
        consistency = "WITHIN_REFERENCE" if ref_min <= tee <= ref_max else "OUTSIDE_REFERENCE_REVIEW"
    if ree_value is not None and bia is not None:
        delta = abs(ree_value - bia) / max(ree_value, 1)
        threshold = formula_cfg.get("cross_check_threshold") if isinstance(formula_cfg, dict) else None
        conflict = bool(threshold is not None and delta > float(threshold))
        if conflict: consistency = "ENERGY_ESTIMATION_CONFLICT"
    return {"ree_source": source, "measured_ree": measured, "predicted_ree": predicted, "ree_value": ree_value,
            "ree_formula_id": formula_id, "ree_formula_version": formula_cfg.get("ree_formula_version") if isinstance(formula_cfg, dict) else None,
            "bia_bmr": bia, "pal": pal, "tee_base": tee, "kcal_per_kg_reference_min": ref_min,
            "kcal_per_kg_reference_max": ref_max, "kcal_per_kg_reference_range": [ref_min, ref_max] if ref_min is not None else None,
            "consistency_check": consistency, "consistency_status": consistency, "energy_estimation_conflict": conflict,
            "prescription_mode": mode, "prescription_ratio": ratio, "daily_energy_target_kcal": round(tee * ratio, 1) if tee is not None else None,
            "primary_energy_source": source,
            "p2_formula_status": "CANDIDATE" if test_only_profile else formula_status,
            "p2_primary_eligible": formula_primary_allowed,
            "pal_source": pal_source,
            "pal_status": pal_status,
            "mdt_confirmed": bool(formula_id and formula_status == "ACTIVE" and pal is not None and not test_only_profile),
            "candidate_parameter": bool(formula_id and (formula_status == "CANDIDATE" or test_only_profile))}


def enhanced_eligibility(payload: dict[str, Any], phenotype: str, safety_level: str, goal: dict[str, Any], liver: dict[str, Any]) -> tuple[bool, list[str]]:
    """Evaluate enhanced fat-loss admission without inventing thresholds."""
    if goal.get("primary_goal") != "ENHANCED_FAT_LOSS":
        return False, ["未选择强化减脂"]
    reasons: list[str] = []
    if phenotype not in {"A", "B"}: reasons.append("主表型不属于A/B")
    if safety_level != "green": reasons.append("安全等级不是绿色")
    if _value(payload, "q6_surgeryWindow") == "2周以内": reasons.append("距手术时间过近")
    if phenotype in {"C", "D", "E"}: reasons.append("肌肉/营养保护型不进入强化减脂")
    if "不明原因下降" in str(_value(payload, "q28_weightChange") or "") or "减少50%" in str(_value(payload, "q30_intake") or ""): reasons.append("近期非意愿下降或摄入不足")
    if liver.get("review") or liver.get("uncertain"): reasons.append("Q50肝弹性资料需复核")
    barriers = normalize_selection(_value(payload, "q51_executionBarriers", "execution_barriers"))["positive_items"]
    if len(barriers) >= 3: reasons.append("执行障碍较多")
    return not reasons, reasons


def _meal(slot: str, food: dict[str, Any], *, mdt_confirmed: bool = False) -> dict[str, Any]:
    return {"meal_type": slot, "category": food.get("category"), "meal_name": food.get("meal_name") or food.get("name"), "dish_name": food.get("dish_name") or food.get("name"), "component_id": food.get("component_id"), "ingredient_name": food.get("ingredient_name") or food.get("ingredients"), "ingredient_amount": food.get("ingredient_amount") or food.get("ingredient_amounts") or food.get("amount"), "unit": food.get("unit"), "raw_or_cooked_basis": food.get("raw_or_cooked_basis"), "weight_basis": food.get("weight_basis") or food.get("raw_or_cooked_basis"), "base_portion": deepcopy(food.get("base_portion")), "cooking_method": food.get("cooking_method"), "brief_instructions": food.get("brief_instructions") or "按医护审核的份量烹调，少油少盐。", "estimated_energy": food.get("kcal_estimate", food.get("energy_kcal")), "estimated_protein": food.get("protein_g"), "estimated_carbohydrate": food.get("carbohydrate_g"), "estimated_fat": food.get("fat_g"), "portion_options": deepcopy(food.get("portion_options")) if food.get("portion_options") else None, "portion_min": food.get("portion_min"), "portion_max": food.get("portion_max"), "portion_step": food.get("portion_step"), "portion_boundary_source": food.get("portion_boundary_source"), "replacement_options": food.get("replacement_options", food.get("replacement_ids", [])), "knowledge_item_id": food.get("knowledge_item_id") or food.get("component_id"), "knowledge_version": food.get("knowledge_version") or food.get("source_version", "V2.0"), "mdt_confirmed": mdt_confirmed, "status": "候选组件，待医护确认" if not mdt_confirmed else "ACTIVE"}

def _composite_meal(slot: str, foods: list[dict[str, Any]], *, mdt_confirmed: bool) -> dict[str, Any]:
    """Combine approved component records without inventing nutrition values."""
    parts = [_meal(slot, f, mdt_confirmed=mdt_confirmed) for f in foods if f]
    # Do not put the meal object itself into ``components`` (the first item in
    # ``parts`` used to be reused as ``base``, creating a circular JSON graph
    # and making plan persistence fail).  Keep an independent meal shell and
    # deep-copied component snapshots instead.
    base = deepcopy(parts[0]) if parts else _meal(slot, {}, mdt_confirmed=mdt_confirmed)
    base["components"] = deepcopy(parts)
    base["ingredient_name"] = [p.get("ingredient_name") for p in parts]
    base["ingredient_amount"] = [p.get("ingredient_amount") for p in parts]
    base["estimated_energy"] = sum((p.get("estimated_energy") or 0) for p in parts) if all(p.get("estimated_energy") is not None for p in parts) else None
    for out, key in (("estimated_protein", "estimated_protein"), ("estimated_carbohydrate", "estimated_carbohydrate"), ("estimated_fat", "estimated_fat")):
        base[out] = sum((p.get(key) or 0) for p in parts) if all(p.get(key) is not None for p in parts) else None
    base["dish_name"] = " + ".join(str(p.get("dish_name") or "") for p in parts)
    base["knowledge_item_ids"] = [p.get("knowledge_item_id") for p in parts]
    return base


def _food_allowed(food: dict[str, Any], payload: dict[str, Any]) -> bool:
    """Apply only explicit allergy/intolerance exclusions before rotation."""
    allergy = normalize_selection(_value(payload, "q32_foodAllergy", "food_allergy"))["positive_items"]
    intolerance = normalize_selection(_value(payload, "q33_foodIntolerance", "food_intolerance"))["positive_items"]
    tags = " ".join(str(food.get(k) or "") for k in ("name", "ingredient_name", "ingredients", "allergy_tags", "intolerance_tags", "contraindications"))
    if any(str(item) in tags for item in allergy):
        return False
    if "乳糖不耐" in intolerance and any(token in tags for token in ("牛奶", "奶", "酸奶", "乳")):
        return False
    if "麸质" in intolerance and any(token in tags for token in ("小麦", "面包", "燕麦", "全麦")):
        return False
    return True


def food_candidate_score(
    food: dict[str, Any],
    payload: dict[str, Any],
    *,
    phenotype: str | None = None,
    goal: dict[str, Any] | None = None,
    energy_target: float | None = None,
    protein_target: float | None = None,
    carb_range: list[float] | None = None,
    fat_range: list[float] | None = None,
    meal_distribution: dict[str, Any] | None = None,
    slot: str = "lunch",
    history_count: int = 0,
    return_components: bool = False,
) -> tuple[float, list[str]] | tuple[float, list[str], dict[str, float]]:
    """Score an already-allowed food component for a patient/meal slot.

    This is a ranking function only. It does not introduce clinical thresholds
    or alter the existing prescription rules; it combines the available plan
    targets, patient tags and rotation history to choose among catalog items.
    """
    def number(*keys: str) -> float | None:
        for key in keys:
            value = food.get(key)
            try:
                if value not in (None, ""):
                    return float(value)
            except (TypeError, ValueError):
                continue
        return None

    score = 0.0
    components = {
        "energy_match": 0.0, "protein_match": 0.0, "phenotype_match": 0.0,
        "disease_match": 0.0, "q34_match": 0.0, "q56_match": 0.0,
        "meal_type_match": 0.0, "repetition_penalty": 0.0,
        # Macro terms are included even when no active range is available, so
        # the trace has a stable contract for clinician review/debugging.
        "carb_match": 0.0, "fat_match": 0.0,
    }
    reasons: list[str] = []
    category = str(food.get("category") or "")
    kcal = number("energy_kcal", "kcal_estimate")
    protein = number("protein_g")
    carbohydrate = number("carbohydrate_g")
    fat = number("fat_g")
    if kcal and kcal > 0:
        carb_pct = (carbohydrate or 0) * 4 / kcal * 100
        fat_pct = (fat or 0) * 9 / kcal * 100
    else:
        carb_pct = fat_pct = None

    # Meal-slot compatibility is derived from the catalog contract.
    meal_types = food.get("meal_type") or []
    if isinstance(meal_types, str):
        meal_types = [meal_types]
    if slot in meal_types:
        components["meal_type_match"] += 0.25
        reasons.append("餐次适配")
    else:
        components["meal_type_match"] -= 0.25
        reasons.append("餐次不匹配")

    # Use the configured meal distribution when present. Otherwise leave this
    # component neutral instead of inventing a meal-energy rule.
    slot_target = None
    if energy_target and isinstance(meal_distribution, dict):
        raw_share = meal_distribution.get(slot)
        if isinstance(raw_share, (list, tuple)) and len(raw_share) == 2:
            slot_target = energy_target * (float(raw_share[0]) + float(raw_share[1])) / 200
        elif isinstance(raw_share, (int, float)):
            slot_target = energy_target * float(raw_share) / 100
    if slot_target and kcal:
        energy_score = max(0.0, 1.0 - abs(kcal - slot_target) / max(slot_target, 1.0))
        components["energy_match"] += 0.45 * energy_score
        reasons.append(f"能量接近餐次目标({kcal:g}/{slot_target:g}kcal)")

    # Protein contribution is weighted more strongly for protein components and
    # when the patient's calculated target is relatively high.
    if protein is not None:
        density = protein / max(kcal or 1.0, 1.0) * 100
        protein_weight = 0.35 if category == "protein" else 0.08
        if protein_target is not None:
            weight = _value(payload, "q15_weight", "weight_kg")
            try:
                protein_per_kg = float(protein_target) / max(float(weight), 1.0)
                protein_weight *= 1.0 + min(0.8, max(0.0, protein_per_kg - 1.0))
            except (TypeError, ValueError):
                pass
        components["protein_match"] += protein_weight * min(1.0, density / 12.0)
        if category == "protein":
            reasons.append("蛋白贡献" if protein > 0 else "蛋白贡献不足")

    # Macro ranges are configuration inputs, not new medical defaults.
    if carbohydrate is not None and carb_range and len(carb_range) == 2 and carb_pct is not None:
        midpoint = (float(carb_range[0]) + float(carb_range[1])) / 2
        components["carb_match"] = 0.18 * max(0.0, 1.0 - abs(carb_pct - midpoint) / 100)
        reasons.append("碳水比例接近目标" if carb_range[0] <= carb_pct <= carb_range[1] else "碳水比例偏离目标")
    if fat is not None and fat_range and len(fat_range) == 2 and fat_pct is not None:
        midpoint = (float(fat_range[0]) + float(fat_range[1])) / 2
        components["fat_match"] = 0.18 * max(0.0, 1.0 - abs(fat_pct - midpoint) / 100)
        reasons.append("脂肪比例接近目标" if fat_range[0] <= fat_pct <= fat_range[1] else "脂肪比例偏离目标")

    text = " ".join(str(food.get(key) or "") for key in ("name", "ingredients", "disease_tags", "contraindications", "phenotype_tags", "goal_tags"))
    tags = " ".join(str(food.get(key) or "") for key in ("phenotype_tags", "goal_tags", "disease_tags", "liver_modifier_tags"))
    phenotype_labels = {"A": ("A", "标准减脂"), "B": ("B", "代谢"), "C": ("C", "保肌"), "D": ("D", "营养恢复"), "E": ("E", "停止下降"), "F": ("F", "综合")}
    if phenotype and any(token in tags for token in phenotype_labels.get(str(phenotype), ())):
        components["phenotype_match"] += 0.35
        reasons.append("表型标签适配")
    primary_goal = (goal or {}).get("primary_goal") if isinstance(goal, dict) else None
    goal_labels = {
        "STANDARD_FAT_LOSS": "标准减脂", "ENHANCED_FAT_LOSS": "强化减脂",
        "WEIGHT_MAINTENANCE_MUSCLE_PRESERVATION": "保肌", "NUTRITION_RECOVERY_WEIGHT_GAIN": "营养恢复",
        "STOP_WEIGHT_LOSS": "停止下降", "MUSCLE_GAIN": "增肌", "METABOLIC_CONTROL": "代谢控制",
        "FUNCTION_IMPROVEMENT": "运动能力", "PULMONARY_IMPROVEMENT": "肺功能",
    }
    if primary_goal and (primary_goal in tags or goal_labels.get(primary_goal, "") in tags):
        components["q56_match"] += 0.3
        reasons.append("阶段目标适配")
    diet_preferences = normalize_selection(_value(payload, "q34_dietPattern", "diet_pattern"))["positive_items"]
    if diet_preferences:
        matched_preferences = [item for item in diet_preferences if str(item) in text]
        if matched_preferences:
            components["q34_match"] += 0.22
            reasons.append("饮食结构偏好适配:" + ",".join(map(str, matched_preferences)))

    metabolic = normalize_selection(_value(payload, "q43_metabolicConditions", "metabolic_conditions"))["positive_items"]
    disease_tags = " ".join(str(food.get(key) or "") for key in ("disease_tags", "goal_tags"))
    contraindications = str(food.get("contraindications") or "")
    if metabolic:
        matched = [item for item in metabolic if str(item) in disease_tags]
        if matched:
            components["disease_match"] += 0.45 * len(matched)
            reasons.append("疾病标签适配:" + ",".join(map(str, matched)))
        diabetes = any("糖尿病" in str(item) or "糖耐量" in str(item) or "糖代谢" in str(item) for item in metabolic)
        if diabetes and "糖代谢异常" in contraindications:
            # The catalog text describes how this component should be paired,
            # rather than forbidding it; keep it eligible but lower its score
            # when no explicit low-glycemic adaptation is present.
            components["disease_match"] -= 0.18
            reasons.append("糖代谢异常规则降权")
        if diabetes and carb_pct is not None:
            components["disease_match"] -= 0.25 * min(1.0, carb_pct / 100)
            reasons.append("代谢异常降低高碳水倾向")
        lipid = any("血脂" in str(item) for item in metabolic)
        fatty_liver = any(token in str(item) for item in metabolic for token in ("脂肪肝", "MASLD"))
        if lipid and fat_pct is not None:
            components["disease_match"] -= 0.25 * min(1.0, fat_pct / 100)
            reasons.append("血脂异常规则降低高脂肪倾向")
        if fatty_liver and fat_pct is not None:
            components["disease_match"] -= 0.25 * min(1.0, fat_pct / 100)
            reasons.append("脂肪肝规则降低高脂肪倾向")
        if lipid and ("血脂异常" in contraindications or "血脂" in contraindications):
            # A documented contraindication/adaptation is evidence for the
            # disease-specific score; each disease contributes independently.
            components["disease_match"] -= 0.18
            reasons.append("血脂异常知识规则")
        if fatty_liver and ("脂肪肝" in contraindications or "MASLD" in contraindications):
            components["disease_match"] -= 0.18
            reasons.append("脂肪肝知识规则")
        hyperuricemia = any("高尿酸" in str(item) or "痛风" in str(item) for item in metabolic)
        if hyperuricemia and (any(token in text for token in ("海鲜", "内脏", "浓汤", "高尿酸", "痛风"))):
            components["disease_match"] -= 0.7
            reasons.append("高尿酸禁忌倾向")
        if hyperuricemia and ("高尿酸" in contraindications or "痛风" in contraindications):
            components["disease_match"] -= 0.2
            reasons.append("高尿酸知识规则")
        hypertension = any("高血压" in str(item) or "控盐" in str(item) for item in metabolic)
        if hypertension and any(token in text for token in ("高血压", "酱油", "蚝油", "高盐", "腌", "咸")):
            components["disease_match"] -= 0.55
            reasons.append("高血压控盐规则降权")
        if hypertension and any(token in contraindications for token in ("高血压", "控盐", "高盐", "酱油", "蚝油")):
            components["disease_match"] -= 0.2
            reasons.append("高血压知识规则")

    if history_count:
        components["repetition_penalty"] -= 0.22 * history_count
        reasons.append(f"近期使用惩罚{history_count}")
    score = sum(components.values())
    components["final_score"] = round(score, 6)
    return (round(score, 6), reasons, components) if return_components else (round(score, 6), reasons)


def _rotate_food(candidates: list[dict[str, Any]], *, day: int, slot: str, history: dict[str, list[str]], seed: int, history_key: str | None = None, score_fn=None) -> tuple[dict[str, Any] | None, bool]:
    """Pick the least recently used component, avoiding immediate repeats."""
    if not candidates:
        return None, True
    key = history_key or {"breakfast": "staple", "lunch": "staple", "dinner": "staple", "snack": "snack"}.get(slot, slot)
    used = history.setdefault(key, [])
    previous = used[-1] if used else None
    available = [x for x in candidates if x.get("component_id") != previous]
    limited = not available
    pool = available or candidates
    counts = {str(x.get("component_id")): used.count(x.get("component_id")) for x in pool}
    # Stable tie-breaking keeps tests deterministic while allowing different
    # patient payloads to produce different, safe rotations.
    def rank(item: dict[str, Any]):
        use_count = counts.get(str(item.get("component_id")), 0)
        score = score_fn(item, slot, use_count) if score_fn else 0.0
        return (-score, use_count, (seed ^ (day * 17 + len(slot) * 7 + sum(ord(c) for c in str(item.get("component_id"))))) % 997)
    ordered = sorted(pool, key=rank)
    chosen = ordered[0]
    used.append(str(chosen.get("component_id")))
    return chosen, limited


def _build_rotating_weekly_meals(items: list[dict[str, Any]], payload: dict[str, Any], *, phenotype: str | None = None, goal: dict[str, Any] | None = None, energy_target: float | None = None, protein_target: float | None = None, carb_range: list[float] | None = None, fat_range: list[float] | None = None, meal_distribution: dict[str, Any] | None = None, nutrition_trace: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], bool]:
    """Compose seven days from separate staple/protein/vegetable histories."""
    categories = {cat: [x for x in items if x.get("category") == cat and _food_allowed(x, payload) and x.get("component_id")] for cat in ("staple", "protein", "vegetable", "snack")}
    history: dict[str, list[str]] = {cat: [] for cat in categories}
    seed_text = "|".join(str(payload.get(k) or "") for k in ("patient_id", "q15_weight", "q18_bodyFat", "q43_metabolicConditions", "q56_goal"))
    seed = sum(ord(c) for c in seed_text) % 997
    limited = any(len(values) < 2 for values in categories.values() if values)
    weekly: list[dict[str, Any]] = []
    trace = nutrition_trace if nutrition_trace is not None else {}
    trace.setdefault("selected_food_reason", [])
    trace.setdefault("rejected_food_reason", [])
    for day in range(1, 8):
        meals: dict[str, dict[str, Any]] = {}
        for slot in ("breakfast", "lunch", "snack", "dinner"):
            if slot == "snack":
                score_cache: dict[tuple[str, int], tuple[float, list[str], dict[str, float]]] = {}
                def snack_score(item, slot_name, used_count):
                    score, reasons, components = food_candidate_score(item, payload, phenotype=phenotype, goal=goal, energy_target=energy_target, protein_target=protein_target, carb_range=carb_range, fat_range=fat_range, meal_distribution=meal_distribution, slot=slot_name, history_count=used_count, return_components=True)
                    score_cache[(str(item.get("component_id")), used_count)] = (round(score, 6), reasons, components)
                    return score
                snack, was_limited = _rotate_food(categories["snack"], day=day, slot=slot, history=history, seed=seed, history_key="snack", score_fn=snack_score)
                limited = limited or was_limited
                meals[slot] = _composite_meal(slot, [snack] if snack else [], mdt_confirmed=False)
                if snack:
                    prior_count = max(0, history["snack"].count(str(snack.get("component_id"))) - 1)
                    selected_score, selected_reasons, selected_components = score_cache.get((str(snack.get("component_id")), prior_count), (None, [], {}))
                    trace["selected_food_reason"].append({"day": day, "slot": slot, "component_id": snack.get("component_id"), "score": selected_score, "reasons": selected_reasons, "food_score_components": selected_components})
                continue
            parts = []
            for category in ("staple", "protein", "vegetable"):
                score_cache: dict[tuple[str, int], tuple[float, list[str], dict[str, float]]] = {}
                def category_score(item, slot_name, used_count, category_name=category):
                    score, reasons, components = food_candidate_score(item, payload, phenotype=phenotype, goal=goal, energy_target=energy_target, protein_target=protein_target, carb_range=carb_range, fat_range=fat_range, meal_distribution=meal_distribution, slot=slot_name, history_count=used_count, return_components=True)
                    # Protein contribution is a primary discriminator for the
                    # protein component, while staple/vegetable candidates are
                    # primarily governed by meal energy and macro fit.
                    if category_name == "protein":
                        protein_boost = min(0.5, (float(item.get("protein_g") or 0) / max(float(item.get("energy_kcal") or 1), 1)) * 10)
                        components["protein_match"] = components.get("protein_match", 0.0) + protein_boost
                        score = sum(value for key, value in components.items() if key != "final_score")
                        components["final_score"] = round(score, 6)
                    score_cache[(str(item.get("component_id")), used_count)] = (round(score, 6), reasons, components)
                    return score
                chosen, was_limited = _rotate_food(categories[category], day=day, slot=slot, history=history, seed=seed + len(slot), history_key=category, score_fn=category_score)
                limited = limited or was_limited
                if chosen:
                    parts.append(chosen)
                    prior_count = max(0, history[category].count(str(chosen.get("component_id"))) - 1)
                    selected_score, selected_reasons, selected_components = score_cache.get((str(chosen.get("component_id")), prior_count), (None, [], {}))
                    trace["selected_food_reason"].append({"day": day, "slot": slot, "category": category, "component_id": chosen.get("component_id"), "score": selected_score, "reasons": selected_reasons, "food_score_components": selected_components})
                    ranked = sorted(
                        ((x.get("component_id"), score_cache.get((str(x.get("component_id")), history[category].count(str(x.get("component_id")))), (None, [], {})))
                         for x in categories[category] if x.get("component_id") != chosen.get("component_id")),
                        key=lambda value: value[1][0] if value[1][0] is not None else -999,
                        reverse=True,
                    )
                    # Keep concrete rejection evidence alongside the ranked
                    # alternatives.  This lets clinicians see why a safe
                    # candidate lost (e.g. disease penalty or repetition),
                    # instead of an empty placeholder trace.
                    rejected = [
                        {"component_id": component_id, "score": values[0], "reasons": values[1], "food_score_components": values[2]}
                        for component_id, values in ranked[:3]
                    ]
                    trace["rejected_food_reason"].append({"day": day, "slot": slot, "category": category, "top_alternatives": rejected})
            meals[slot] = _composite_meal(slot, parts, mdt_confirmed=False)
        weekly.append({"day": day, "meals": meals})
    # A populated catalog with three or more breakfast candidates should not
    # silently collapse to one repeated breakfast combination.
    breakfasts = {tuple(str(x.get("component_id")) for x in (weekly[d]["meals"]["breakfast"].get("components") or [])) for d in range(7)}
    if len(categories["staple"]) >= 3 and len(breakfasts) < 3:
        limited = True
    return [day["meals"] for day in weekly], limited


# This is an engineering validation tolerance only.  It is intentionally not
# a clinical target or a new production medical rule.
VALIDATION_TOLERANCE = 0.20


def _number_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _scale_amount(value: Any, factor: float) -> Any:
    """Scale structured ingredient amounts without flattening their shape."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value) * factor, 3)
    if isinstance(value, list):
        return [_scale_amount(item, factor) for item in deepcopy(value)]
    if isinstance(value, dict):
        result = deepcopy(value)
        for key in ("amount", "value", "ingredient_amount", "quantity", "grams"):
            if key in result and _number_or_none(result[key]) is not None:
                result[key] = round(float(result[key]) * factor, 3)
        return result
    if isinstance(value, str):
        # Preserve units and the documented raw/cooked wording in a compact
        # string such as "100g + 3g" when a catalogue item uses that format.
        def replace(match: re.Match[str]) -> str:
            amount = round(float(match.group(1)) * factor, 3)
            text = f"{amount:g}"
            return text + match.group(2)
        return re.sub(r"(\d+(?:\.\d+)?)(\s*(?:g|kg|ml|个|份))", replace, value)
    return deepcopy(value)


def _portion_options_for(component: dict[str, Any]) -> list[float]:
    """Return portion multipliers from the component's V4 frozen scale set.

    A real STANDARD_COMPONENT is identified by a component_id present in the
    manifest-selected V4 runtime catalogue.  Its allowed scales are the only values
    closure/replacement may select.  Anonymous legacy test objects retain the
    old min/max/step or portion_options fallback and are not V4 runtime data.
    """
    component_id = str(component.get("component_id") or "").strip()
    if component_id:
        from .v4_food_data import V4FoodDataError, get_allowed_component_scales
        try:
            allowed = get_allowed_component_scales(component_id)
        except V4FoodDataError as exc:
            # An identified but unknown component is not a V4 candidate and
            # must not receive a fabricated default scale.  Errors loading or
            # validating the frozen asset must not silently fall back either.
            if str(exc).startswith("unknown component_id:"):
                return []
            raise
        else:
            return [float(value) for value in allowed]

    minimum = _number_or_none(component.get("portion_min"))
    maximum = _number_or_none(component.get("portion_max"))
    step = _number_or_none(component.get("portion_step"))
    if minimum is not None and maximum is not None and step is not None and minimum > 0 and maximum >= minimum and step > 0:
        values: list[float] = []
        index = 0
        epsilon = max(step, 1.0) * 1e-9
        while minimum + index * step <= maximum + epsilon:
            values.append(round(minimum + index * step, 8))
            index += 1
        # 1.0 is the neutral base portion and must remain available whenever
        # it lies inside the confirmed boundary, even for a non-aligned step.
        if minimum - epsilon <= 1.0 <= maximum + epsilon:
            values.append(1.0)
        return sorted({round(value, 4) for value in values if minimum - epsilon <= value <= maximum + epsilon})

    raw = component.get("portion_options")
    values = []
    if isinstance(raw, (list, tuple)):
        for value in raw:
            number = _number_or_none(value)
            if number is not None and number > 0:
                values.append(number)
    return sorted({round(value, 4) for value in values}) or [1.0]


def _legacy_scale_options_for(component: dict[str, Any]) -> list[float]:
    """Return the pre-V4 scale candidates for audit comparison only."""
    raw = component.get("portion_options")
    if isinstance(raw, (list, tuple)):
        values = [_number_or_none(value) for value in raw]
        return sorted({round(value, 4) for value in values if value is not None and value > 0})
    minimum = _number_or_none(component.get("portion_min"))
    maximum = _number_or_none(component.get("portion_max"))
    step = _number_or_none(component.get("portion_step"))
    if minimum is None or maximum is None or step is None or minimum <= 0 or maximum < minimum or step <= 0:
        return [1.0]
    values: list[float] = []
    index = 0
    while minimum + index * step <= maximum + max(step, 1.0) * 1e-9:
        values.append(round(minimum + index * step, 8))
        index += 1
    return sorted({round(value, 4) for value in values}) or [1.0]


def _v4_scale_coordination_diagnostic(
    rotating_meals: list[dict[str, dict[str, Any]]],
    daily_closures: list[dict[str, Any]],
    replacement_optimization: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize V4 scale coordination without becoming a clinical rule."""
    from .v4_food_data import V4FoodDataError, get_allowed_component_scales

    total = 0
    valid = 0
    prevented = 0
    no_legal = 0
    for day in rotating_meals:
        for meal in day.values():
            for component in meal.get("components") or []:
                component_id = str(component.get("component_id") or "").strip()
                if not component_id:
                    continue
                total += 1
                try:
                    allowed = tuple(get_allowed_component_scales(component_id))
                except V4FoodDataError as exc:
                    if str(exc).startswith("unknown component_id:"):
                        continue
                    no_legal += 1
                    continue
                if not allowed:
                    no_legal += 1
                    continue
                legacy_options = _legacy_scale_options_for(component)
                prevented += sum(1 for value in legacy_options if value not in allowed)
                current = _number_or_none(component.get("portion_scale"))
                if current is None:
                    current = 1.0
                if any(abs(current - value) <= 1e-6 for value in allowed):
                    valid += 1
                else:
                    no_legal += 1
    best_effort = sum(1 for closure in daily_closures if closure.get("closure_constraint_status") == "BEST_EFFORT_WITHIN_ALLOWED_SCALES")
    rejected = sum(int(item.get("scale_rejections") or 0) for item in replacement_optimization)
    status = "PASS" if no_legal == 0 else "REVIEW_REQUIRED"
    return {
        "total_standard_component_items": total,
        "items_with_valid_allowed_scale": valid,
        "invalid_legacy_scale_prevented": prevented,
        "no_legal_scale_components": no_legal,
        "closure_best_effort_count": best_effort,
        "replacement_scale_rejections": rejected,
        "status": status,
    }


def _refresh_composite_meal(meal: dict[str, Any]) -> dict[str, Any]:
    parts = meal.get("components") or []
    meal["ingredient_name"] = [part.get("ingredient_name") for part in parts]
    meal["ingredient_amount"] = [part.get("ingredient_amount") for part in parts]
    meal["estimated_energy"] = sum((part.get("estimated_energy") or 0) for part in parts) if all(part.get("estimated_energy") is not None for part in parts) else None
    for output, key in (("estimated_protein", "estimated_protein"), ("estimated_carbohydrate", "estimated_carbohydrate"), ("estimated_fat", "estimated_fat")):
        meal[output] = sum((part.get(key) or 0) for part in parts) if all(part.get(key) is not None for part in parts) else None
    meal["dish_name"] = " + ".join(str(part.get("dish_name") or "") for part in parts)
    meal["knowledge_item_ids"] = [part.get("knowledge_item_id") for part in parts]
    return meal


def _apply_component_scale(component: dict[str, Any], factor: float) -> None:
    if factor == 1:
        return
    for key in ("estimated_energy", "estimated_protein", "estimated_carbohydrate", "estimated_fat"):
        number = _number_or_none(component.get(key))
        if number is not None:
            component[key] = round(number * factor, 3)
    component["ingredient_amount"] = _scale_amount(component.get("ingredient_amount"), factor)
    component["portion_scale"] = factor


def _meal_distribution_targets(day_meals: dict[str, dict[str, Any]], daily_energy: float | None, meal_distribution: dict[str, Any] | None) -> dict[str, float]:
    if daily_energy is None or daily_energy <= 0 or not isinstance(meal_distribution, dict):
        return {}
    raw_shares: dict[str, float] = {}
    for slot, meal in day_meals.items():
        if not (meal.get("components") or []):
            continue
        value = meal_distribution.get(slot)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            low, high = _number_or_none(value[0]), _number_or_none(value[1])
            if low is not None and high is not None:
                raw_shares[slot] = max(0.0, (low + high) / 2)
        elif _number_or_none(value) is not None:
            raw_shares[slot] = max(0.0, float(value))
    total = sum(raw_shares.values())
    return {slot: round(float(daily_energy) * share / total, 3) for slot, share in raw_shares.items()} if total > 0 else {}


def _close_day_meals(day: int, day_meals: dict[str, dict[str, Any]], *, daily_energy: float | None, protein_target: float | None, carb_range: list[float] | None, fat_range: list[float] | None, meal_distribution: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Independently size one day's meals using catalogue portion choices.

    Protein and staple choices are optimized first; vegetables stay at their
    catalogue portion unless no other component can carry the meal target.
    Every day receives fresh component copies and a separate closure record.
    """
    targets = _meal_distribution_targets(day_meals, daily_energy, meal_distribution)
    protein_distribution = {slot: round(float(protein_target) * target / float(daily_energy), 3) for slot, target in targets.items()} if protein_target is not None and daily_energy else {}
    adjustments: list[dict[str, Any]] = []
    meal_actual: dict[str, float | None] = {}
    meal_target: dict[str, float | None] = {slot: targets.get(slot) for slot in day_meals}
    limited_reasons: list[str] = []

    # Decide the optimisation phase from the unscaled day's actual protein.
    # Once the protein target is already met, energy closure becomes the
    # primary objective; this prevents protein-first optimisation from
    # suppressing otherwise legitimate staple/snack energy adjustments.
    baseline_protein = 0.0
    for meal in day_meals.values():
        for component in meal.get("components") or []:
            baseline_protein += _number_or_none(component.get("estimated_protein")) or 0.0
    protein_phase = protein_target is not None and baseline_protein < float(protein_target)
    # The first pass preserves the established protein-first selection.  A
    # separate whole-day pass below handles energy closure after protein is
    # already sufficient, without re-selecting or enlarging protein foods.
    energy_phase_applied = False
    energy_adjustments: list[dict[str, Any]] = []

    for slot, meal in day_meals.items():
        parts = meal.get("components") or []
        if not parts:
            meal_actual[slot] = None
            continue
        target = targets.get(slot)
        target_protein = protein_distribution.get(slot)
        # Preserve structure and avoid changing rotation selections in place.
        meal["components"] = deepcopy(parts)
        parts = meal["components"]
        choices: list[list[float]] = []
        for component in parts:
            # Filling energy by enlarging vegetables is not an acceptable
            # fallback; their documented portion remains fixed at 1x.
            component_options = _portion_options_for(component)
            if component.get("category") == "vegetable":
                choices.append([1.0] if any(abs(value - 1.0) <= 1e-6 for value in component_options) else [])
            else:
                choices.append(component_options)
        if any(not options for options in choices):
            limited_reasons.append(f"{slot}餐次存在无可用合法份量scale的组件")
            _refresh_composite_meal(meal)
            meal["meal_energy_target"] = target
            meal["meal_energy_actual"] = meal.get("estimated_energy")
            meal_actual[slot] = _number_or_none(meal.get("estimated_energy"))
            continue
        def evaluate(scales: tuple[float, ...]) -> tuple[float, float, float, float, float]:
            energy = protein = carbohydrate = fat = 0.0
            vegetable_deviation = 0.0
            for component, scale in zip(parts, scales):
                energy += (_number_or_none(component.get("estimated_energy")) or 0.0) * scale
                protein += (_number_or_none(component.get("estimated_protein")) or 0.0) * scale
                carbohydrate += (_number_or_none(component.get("estimated_carbohydrate")) or 0.0) * scale
                fat += (_number_or_none(component.get("estimated_fat")) or 0.0) * scale
                if component.get("category") == "vegetable":
                    vegetable_deviation += abs(scale - 1.0)
            energy_error = abs(energy - target) / max(target or 1.0, 1.0) if target else 0.0
            protein_error = abs(protein - target_protein) / max(target_protein or 1.0, 1.0) if target_protein else 0.0
            macro_error = 0.0
            if energy > 0 and carb_range and len(carb_range) == 2:
                carb_pct = carbohydrate * 4 / energy * 100
                macro_error += abs(carb_pct - (float(carb_range[0]) + float(carb_range[1])) / 2) / 100
            if energy > 0 and fat_range and len(fat_range) == 2:
                fat_pct = fat * 9 / energy * 100
                macro_error += abs(fat_pct - (float(fat_range[0]) + float(fat_range[1])) / 2) / 100
            # Established first pass: close protein before making any
            # whole-day energy-only adjustment.
            objective = protein_error * 1.6 + energy_error + macro_error * 0.35
            objective += vegetable_deviation * 0.1 + sum(abs(scale - 1.0) for scale in scales) * 0.02
            return objective, energy, protein, carbohydrate, fat
        combinations = product(*choices)
        best_scales: tuple[float, ...] | None = None
        best_values: tuple[float, float, float, float, float] | None = None
        for scales in combinations:
            values = evaluate(tuple(scales))
            if best_values is None or values[0] < best_values[0]:
                best_scales, best_values = tuple(scales), values
        if best_scales is None or best_values is None:
            best_scales, best_values = tuple(1.0 for _ in parts), evaluate(tuple(1.0 for _ in parts))
        for component, scale in zip(parts, best_scales):
            if scale != 1:
                before_amount = deepcopy(component.get("ingredient_amount"))
                _apply_component_scale(component, scale)
                if protein_phase and component.get("category") == "protein":
                    reason = "increase_protein_for_protein" if scale > 1 else "decrease_component_for_excess"
                elif component.get("category") == "snack":
                    reason = "increase_snack_for_energy" if scale > 1 else "decrease_component_for_excess"
                else:
                    reason = "increase_staple_for_energy" if scale > 1 else "decrease_component_for_excess"
                adjustments.append({"day": day, "meal_type": slot, "component_id": component.get("component_id"), "from_scale": 1.0, "to_scale": scale, "from_amount": before_amount, "to_amount": component.get("ingredient_amount"), "reason": reason, "closure_phase": "protein_closure"})
        _refresh_composite_meal(meal)
        meal["meal_energy_target"] = target
        meal["meal_energy_actual"] = meal.get("estimated_energy")
        meal_actual[slot] = _number_or_none(meal.get("estimated_energy"))
        if target is not None and meal_actual[slot] is not None and abs(meal_actual[slot] - target) / max(target, 1.0) > VALIDATION_TOLERANCE:
            limited_reasons.append(f"{slot}餐次在目录份量选项内无法充分接近能量目标")

    # Phase 2: once the first pass has met the daily protein target, improve
    # the whole-day energy gap using only legal next steps on staple/snack
    # components. Protein components and vegetables are intentionally not
    # enlarged in this phase. This keeps the established protein target and
    # disease/rotation choices intact while making the energy objective explicit.
    def _totals() -> tuple[float, float, float, float]:
        return (
            sum((_number_or_none(meal.get("estimated_energy")) or 0.0) for meal in day_meals.values() if meal.get("components")),
            sum((_number_or_none(meal.get("estimated_protein")) or 0.0) for meal in day_meals.values() if meal.get("components")),
            sum((_number_or_none(meal.get("estimated_carbohydrate")) or 0.0) for meal in day_meals.values() if meal.get("components")),
            sum((_number_or_none(meal.get("estimated_fat")) or 0.0) for meal in day_meals.values() if meal.get("components")),
        )

    if daily_energy is not None and protein_target is not None:
        total_energy, total_protein, _, _ = _totals()
        protein_cap = float(protein_target) * (1.0 + VALIDATION_TOLERANCE)
        iterations = 0
        while total_protein >= float(protein_target) and total_energy < float(daily_energy) and total_protein <= protein_cap + 1e-6 and iterations < 100:
            best: tuple[float, float, float, str, str, float, float] | None = None
            current_gap = abs(float(daily_energy) - total_energy)
            for slot, meal in day_meals.items():
                for component in meal.get("components") or []:
                    if component.get("category") not in {"staple", "snack"}:
                        continue
                    current_scale = _number_or_none(component.get("portion_scale")) or 1.0
                    options = [value for value in _portion_options_for(component) if value > current_scale + 1e-6]
                    if not options:
                        continue
                    next_scale = min(options)
                    ratio = next_scale / current_scale
                    energy_delta = (_number_or_none(component.get("estimated_energy")) or 0.0) * (ratio - 1.0)
                    protein_delta = (_number_or_none(component.get("estimated_protein")) or 0.0) * (ratio - 1.0)
                    if energy_delta <= 0 or total_protein + protein_delta > protein_cap + 1e-6:
                        continue
                    new_gap = abs(float(daily_energy) - (total_energy + energy_delta))
                    improvement = current_gap - new_gap
                    if improvement <= 1e-9:
                        continue
                    # Prefer the step that closes the energy gap most; for ties
                    # prefer less protein added, then a stable component id.
                    candidate = (improvement, -protein_delta, str(component.get("component_id")), slot, component, current_scale, next_scale)
                    if best is None or (candidate[0], candidate[1], candidate[2]) > (best[0], best[1], best[2]):
                        best = candidate
            if best is None:
                break
            _, _, component_id, slot, component, from_scale, to_scale = best
            before_amount = deepcopy(component.get("ingredient_amount"))
            _apply_component_scale(component, to_scale / from_scale)
            # ``_apply_component_scale`` receives a relative factor during
            # the whole-day pass; keep the absolute canonical multiplier for
            # subsequent steps and trace validation.
            component["portion_scale"] = to_scale
            energy_phase_applied = True
            energy_adjustments.append({
                "day": day,
                "meal_type": slot,
                "component_id": component_id,
                "from_scale": from_scale,
                "to_scale": to_scale,
                "from_amount": before_amount,
                "to_amount": component.get("ingredient_amount"),
                "reason": "increase_staple_for_energy" if component.get("category") == "staple" else "increase_snack_for_energy",
                "closure_phase": "energy_closure",
            })
            _refresh_composite_meal(day_meals[slot])
            total_energy, total_protein, _, _ = _totals()
            iterations += 1

    # Refresh per-meal actuals after the whole-day energy pass.
    for slot, meal in day_meals.items():
        meal_actual[slot] = _number_or_none(meal.get("estimated_energy")) if meal.get("components") else None
        if meal.get("components"):
            meal["meal_energy_actual"] = meal_actual[slot]

    total_energy = sum(value or 0 for value in meal_actual.values()) if meal_actual else 0.0
    total_protein = sum((_number_or_none(meal.get("estimated_protein")) or 0.0) for meal in day_meals.values() if meal.get("components"))
    total_carb = sum((_number_or_none(meal.get("estimated_carbohydrate")) or 0.0) for meal in day_meals.values() if meal.get("components"))
    total_fat = sum((_number_or_none(meal.get("estimated_fat")) or 0.0) for meal in day_meals.values() if meal.get("components"))
    carb_target = round(float(daily_energy) * ((float(carb_range[0]) + float(carb_range[1])) / 2) / 100 / 4, 3) if daily_energy and carb_range and len(carb_range) == 2 else None
    fat_target = round(float(daily_energy) * ((float(fat_range[0]) + float(fat_range[1])) / 2) / 100 / 9, 3) if daily_energy and fat_range and len(fat_range) == 2 else None
    def delta(actual: float | None, target_value: float | None) -> float | None:
        return round((actual - target_value) / target_value * 100, 2) if actual is not None and target_value not in (None, 0) else None
    energy_delta = delta(total_energy, daily_energy)
    protein_delta = delta(total_protein, protein_target)
    if daily_energy is None or protein_target is None or not targets:
        closure_status = "INCOMPLETE"
        reasons = ["缺少每日/餐次目标或餐次分配配置"]
    elif (
        energy_delta is not None
        and protein_delta is not None
        and abs(energy_delta) <= VALIDATION_TOLERANCE * 100
        and abs(protein_delta) <= VALIDATION_TOLERANCE * 100
    ):
        closure_status = "PASS"
        reasons = []
    else:
        closure_status = "WARN"
        reasons = ["目录份量选项下能量或蛋白目标仍有偏差"]
    closure_constraint_status = (
        "BEST_EFFORT_WITHIN_ALLOWED_SCALES"
        if closure_status == "WARN" and limited_reasons
        else None
    )
    reasons.extend(limited_reasons)
    adjustments.extend(energy_adjustments)
    closure = {"day": day, "energy_target": daily_energy, "energy_actual": round(total_energy, 3) if meal_actual else None, "energy_delta_pct": energy_delta, "protein_target": protein_target, "protein_actual": round(total_protein, 3), "protein_delta_pct": protein_delta, "carbohydrate_target": carb_target, "carbohydrate_actual": round(total_carb, 3), "fat_target": fat_target, "fat_actual": round(total_fat, 3), "closure_status": closure_status, "closure_constraint_status": closure_constraint_status, "closure_phase": "energy_closure" if energy_phase_applied else "protein_closure", "reasons": reasons, "portion_adjustment_limited": bool(limited_reasons)}
    details = {"meal_energy_target": {"day": day, **meal_target}, "meal_energy_actual": {"day": day, **meal_actual}, "protein_distribution": {"day": day, **protein_distribution}, "portion_adjustments": adjustments, "closure_phase": "energy_closure" if energy_phase_applied else "protein_closure"}
    return closure, details


def _replacement_score(item: dict[str, Any], payload: dict[str, Any], *, phenotype: str | None, goal: dict[str, Any] | None, energy_target: float | None, protein_target: float | None, carb_range: list[float] | None, fat_range: list[float] | None, meal_distribution: dict[str, Any] | None, slot: str) -> float:
    """Return the existing candidate score plus the established protein boost.

    Replacement is deliberately a small post-selection search.  This helper
    mirrors the protein boost used by the initial selector so the replacement
    pool remains explainable and deterministic; it does not create a second
    food scoring rule.
    """
    score, _ = food_candidate_score(
        item,
        payload,
        phenotype=phenotype,
        goal=goal,
        energy_target=energy_target,
        protein_target=protein_target,
        carb_range=carb_range,
        fat_range=fat_range,
        meal_distribution=meal_distribution,
        slot=slot,
    )
    if item.get("category") == "protein":
        try:
            protein_boost = min(0.5, (float(item.get("protein_g") or 0) / max(float(item.get("energy_kcal") or 1), 1)) * 10)
        except (TypeError, ValueError):
            protein_boost = 0.0
        score += protein_boost
    return round(float(score), 6)


def _replacement_candidates(
    catalog_foods: list[dict[str, Any]],
    payload: dict[str, Any],
    *,
    phenotype: str | None,
    goal: dict[str, Any] | None,
    energy_target: float | None,
    protein_target: float | None,
    carb_range: list[float] | None,
    fat_range: list[float] | None,
    meal_distribution: dict[str, Any] | None,
    slot: str,
    category: str,
    current_id: str,
    same_day_ids: set[str],
    adjacent_ids: set[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Build a bounded, deterministic replacement pool.

    The normal score top-N is supplemented with energy-dense and lower-protein
    candidates.  That is the minimal capability missing from the old path:
    high-energy/less-protein foods must be considered even when protein
    density gives them a lower initial score.  All candidates still pass the
    existing allergy/intolerance and rotation checks.
    """
    allowed: list[dict[str, Any]] = []
    for item in catalog_foods:
        component_id = str(item.get("component_id") or "")
        if not component_id or item.get("category") != category or component_id == current_id:
            continue
        if component_id in same_day_ids or component_id in adjacent_ids or not _food_allowed(item, payload):
            continue
        score = _replacement_score(
            item,
            payload,
            phenotype=phenotype,
            goal=goal,
            energy_target=energy_target,
            protein_target=protein_target,
            carb_range=carb_range,
            fat_range=fat_range,
            meal_distribution=meal_distribution,
            slot=slot,
        )
        try:
            energy = float(item.get("energy_kcal") or 0)
            protein = float(item.get("protein_g") or 0)
        except (TypeError, ValueError):
            energy, protein = 0.0, 0.0
        allowed.append({"item": item, "score": score, "energy": energy, "protein": protein})
    if not allowed:
        return []
    # Keep score leaders, high-energy candidates, and low-protein-density
    # candidates.  The union is capped to keep the post-selection search
    # bounded while still exposing the trade-off needed for D1.
    selected: dict[str, dict[str, Any]] = {}
    for ordered in (
        sorted(allowed, key=lambda x: (-x["score"], str(x["item"].get("component_id"))))[:limit],
        sorted(allowed, key=lambda x: (-x["energy"], x["protein"], str(x["item"].get("component_id"))))[:limit],
        sorted(allowed, key=lambda x: (x["protein"] / max(x["energy"], 1.0), -x["energy"], str(x["item"].get("component_id"))))[:limit],
    ):
        for entry in ordered:
            selected.setdefault(str(entry["item"].get("component_id")), entry)
    return [entry["item"] for entry in sorted(selected.values(), key=lambda x: (-x["score"], str(x["item"].get("component_id"))))]


def _replace_day_component(day_meals: dict[str, dict[str, Any]], *, slot: str, category: str, replacement: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a fresh day meal map with one component replaced."""
    trial = deepcopy(day_meals)
    meal = trial.get(slot)
    if not isinstance(meal, dict):
        return trial
    components = list(meal.get("components") or [])
    for index, component in enumerate(components):
        if component.get("category") != category:
            continue
        components[index] = _meal(slot, replacement, mdt_confirmed=bool(component.get("mdt_confirmed")))
        meal["components"] = components
        _refresh_composite_meal(meal)
        return trial
    return trial


def _replacement_objective(closure: dict[str, Any]) -> float:
    """Score a closed day for replacement comparison only."""
    energy_delta = _number_or_none(closure.get("energy_delta_pct"))
    protein_delta = _number_or_none(closure.get("protein_delta_pct"))
    tolerance_pct = VALIDATION_TOLERANCE * 100
    # Resolve the number of WARN metrics first.  The existing validation
    # tolerance remains the engineering boundary; this is not a new medical
    # threshold.
    warning_count = sum(
        1
        for value in (energy_delta, protein_delta)
        if value is None or abs(value) > tolerance_pct
    )
    if energy_delta is None or protein_delta is None:
        return 1_000_000.0 + warning_count * 1_000.0
    # When WARN counts are equal, energy gap is primary and protein deviation
    # is secondary. Penalize protein overshoot beyond the existing tolerance.
    protein_overshoot = max(0.0, protein_delta - tolerance_pct)
    return warning_count * 1_000.0 + abs(energy_delta) + 0.35 * abs(protein_delta) + 2.0 * protein_overshoot


def _replacement_warning_metrics(closure: dict[str, Any]) -> set[str]:
    """Return the existing engineering WARN metrics for a closed day."""
    tolerance_pct = VALIDATION_TOLERANCE * 100
    warnings: set[str] = set()
    for key, metric in (("energy", "energy_delta_pct"), ("protein", "protein_delta_pct")):
        value = _number_or_none(closure.get(metric))
        if value is None or abs(value) > tolerance_pct:
            warnings.add(key)
    return warnings


def _replacement_is_acceptable(before: dict[str, Any], after: dict[str, Any]) -> bool:
    """Accept a replacement without introducing a new WARN metric."""
    before_warnings = _replacement_warning_metrics(before)
    after_warnings = _replacement_warning_metrics(after)
    # A replacement may not turn an already-closed metric into a new WARN.
    if after_warnings - before_warnings:
        return False
    if len(after_warnings) < len(before_warnings):
        return True
    if len(after_warnings) > len(before_warnings):
        return False
    before_gap = sum(abs(_number_or_none(before.get(metric)) or 0.0) for metric in ("energy_delta_pct", "protein_delta_pct"))
    after_gap = sum(abs(_number_or_none(after.get(metric)) or 0.0) for metric in ("energy_delta_pct", "protein_delta_pct"))
    # Ignore negligible numerical improvements.
    return before_gap - after_gap > 0.05


def _component_change_count(before: dict[str, Any], after: dict[str, Any]) -> int:
    """Count distinct meal/category components changed by replacement."""
    def signature(day: dict[str, Any]) -> dict[tuple[str, str], str]:
        result: dict[tuple[str, str], str] = {}
        for slot, meal in day.items():
            if not isinstance(meal, dict):
                continue
            for component in meal.get("components") or []:
                category = str(component.get("category") or "")
                if category in {"staple", "protein", "snack"}:
                    result[(str(slot), category)] = str(component.get("component_id") or "")
        return result

    before_signature = signature(before)
    after_signature = signature(after)
    return sum(1 for key in set(before_signature) | set(after_signature) if before_signature.get(key) != after_signature.get(key))


def _execution_complexity(change_count: int) -> str:
    """Engineering-only audit label; not a clinical threshold."""
    if change_count <= 1:
        return "LOW"
    if change_count <= 3:
        return "MODERATE"
    return "HIGH"


def _optimize_day_replacements(
    day_index: int,
    rotating_meals: list[dict[str, dict[str, Any]]],
    catalog_foods: list[dict[str, Any]],
    payload: dict[str, Any],
    *,
    phenotype: str | None,
    goal: dict[str, Any] | None,
    energy_target: float | None,
    protein_target: float | None,
    carb_range: list[float] | None,
    fat_range: list[float] | None,
    meal_distribution: dict[str, Any] | None,
    base_day_meals: dict[str, dict[str, Any]],
    baseline_closure: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Try a bounded whole-day replacement search after portion closure.

    Replacement is evaluated for any material energy or protein deficit, not
    only the former protein-overshoot/energy-deficit combination. Good closed
    days therefore remain unchanged, while D/E-like days can consider legal
    staple, snack, and protein alternatives. At most six accepted replacements
    are made; this remains a bounded search rather than an exhaustive catalog
    enumeration.
    """
    energy_delta = _number_or_none(baseline_closure.get("energy_delta_pct"))
    protein_delta = _number_or_none(baseline_closure.get("protein_delta_pct"))
    tolerance_pct = VALIDATION_TOLERANCE * 100
    energy_low = energy_delta is not None and energy_delta < -tolerance_pct
    protein_low = protein_delta is not None and protein_delta < -tolerance_pct
    protein_high = protein_delta is not None and protein_delta > tolerance_pct
    triggered = bool(energy_low or protein_low or protein_high)
    if not triggered:
        trigger_reason = "未达到全日replacement触发条件"
    elif energy_low and protein_high:
        trigger_reason = "能量不足且蛋白超过工程容差"
    elif energy_low and protein_low:
        trigger_reason = "能量与蛋白均不足"
    elif energy_low:
        trigger_reason = "能量不足，进入能量优先replacement评估"
    elif protein_high:
        trigger_reason = "蛋白超过工程容差，进入蛋白过量replacement评估"
    else:
        trigger_reason = "蛋白不足，进入蛋白replacement评估"
    trace: dict[str, Any] = {
        "day": day_index + 1,
        "triggered": triggered,
        "reason": trigger_reason,
        "before_energy": baseline_closure.get("energy_actual"),
        "before_protein": baseline_closure.get("protein_actual"),
        "replacements": [],
        "after_energy": baseline_closure.get("energy_actual"),
        "after_protein": baseline_closure.get("protein_actual"),
        "accepted": False,
        "candidate_attempts": 0,
        "scale_rejections": 0,
        "replacement_change_count": 0,
        "EXECUTION_COMPLEXITY": "LOW",
    }
    # ``_close_day_meals`` mutates estimated values and ingredient amounts by
    # the selected multiplier.  Trials must always start from an unscaled
    # snapshot; otherwise a second trial would scale an already-scaled meal
    # and produce inflated kcal/protein values.
    current_unclosed_day = deepcopy(base_day_meals)
    current_day = deepcopy(rotating_meals[day_index])
    current_closure = deepcopy(baseline_closure)
    if not triggered or not catalog_foods or energy_target is None or protein_target is None:
        return current_day, current_closure, {}, trace

    slots = ("breakfast", "lunch", "snack", "dinner")
    categories = ("staple", "protein", "snack")
    for _iteration in range(6):
        current_objective = _replacement_objective(current_closure)
        best: tuple[float, str, str, str, dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]] | None = None
        for slot in slots:
            meal = current_unclosed_day.get(slot) or {}
            parts = meal.get("components") or []
            for category in categories:
                current_component = next((component for component in parts if component.get("category") == category), None)
                if not current_component:
                    continue
                current_id = str(current_component.get("component_id") or "")
                same_day_ids = {
                    str(component.get("component_id"))
                    for other_meal in current_unclosed_day.values()
                    for component in (other_meal.get("components") or [])
                    if component.get("category") == category and component.get("component_id") and str(component.get("component_id")) != current_id
                }
                adjacent_ids: set[str] = set()
                for adjacent_index in (day_index - 1, day_index + 1):
                    if 0 <= adjacent_index < len(rotating_meals):
                        adjacent_ids.update(
                            str(component.get("component_id"))
                            for other_meal in rotating_meals[adjacent_index].values()
                            for component in (other_meal.get("components") or [])
                            if component.get("category") == category and component.get("component_id")
                        )
                candidates = _replacement_candidates(
                    catalog_foods,
                    payload,
                    phenotype=phenotype,
                    goal=goal,
                    energy_target=energy_target,
                    protein_target=protein_target,
                    carb_range=carb_range,
                    fat_range=fat_range,
                    meal_distribution=meal_distribution,
                    slot=slot,
                    category=category,
                    current_id=current_id,
                    same_day_ids=same_day_ids,
                    adjacent_ids=adjacent_ids,
                )
                for candidate in candidates:
                    trace["candidate_attempts"] += 1
                    from .v4_food_data import V4FoodDataError, get_allowed_component_scales
                    candidate_id = str(candidate.get("component_id") or "").strip()
                    try:
                        allowed_scales = get_allowed_component_scales(candidate_id)
                    except V4FoodDataError as exc:
                        if not str(exc).startswith("unknown component_id:"):
                            trace["scale_rejections"] += 1
                            continue
                        allowed_scales = ()
                    if not allowed_scales:
                        trace["scale_rejections"] += 1
                        continue
                    trial_unclosed_day = _replace_day_component(current_unclosed_day, slot=slot, category=category, replacement=candidate)
                    trial_day = deepcopy(trial_unclosed_day)
                    trial_closure, trial_details = _close_day_meals(
                        day_index + 1,
                        trial_day,
                        daily_energy=energy_target,
                        protein_target=protein_target,
                        carb_range=carb_range,
                        fat_range=fat_range,
                        meal_distribution=meal_distribution,
                    )
                    if not _replacement_is_acceptable(current_closure, trial_closure):
                        continue
                    objective = _replacement_objective(trial_closure)
                    if objective >= current_objective - 0.05:
                        continue
                    candidate_key = str(candidate.get("component_id") or "")
                    # When nutritional improvement is effectively tied, prefer
                    # the option with fewer distinct component changes.
                    change_count = _component_change_count(base_day_meals, trial_unclosed_day)
                    selection_objective = objective + change_count * 0.001
                    entry = (selection_objective, slot, category, candidate_key, trial_unclosed_day, trial_day, trial_closure, trial_details)
                    if best is None or entry[:4] < best[:4]:
                        best = entry
        if best is None:
            break
        _, slot, category, new_id, current_unclosed_day, current_day, current_closure, best_details = best
        old_component_id = next(
            (component.get("component_id") for component in (rotating_meals[day_index].get(slot, {}).get("components") or []) if component.get("category") == category),
            None,
        )
        trace["replacements"].append({
            "day": day_index + 1,
            "meal": slot,
            "category": category,
            "old_component_id": old_component_id,
            "new_component_id": new_id,
            "reason": "replace_protein_to_reduce_protein_density" if category == "protein" else "replace_staple_for_energy_closure" if category == "staple" else "replace_snack_for_energy_support",
        })
    trace["after_energy"] = current_closure.get("energy_actual")
    trace["after_protein"] = current_closure.get("protein_actual")
    trace["accepted"] = bool(trace["replacements"])
    trace["replacement_change_count"] = _component_change_count(base_day_meals, current_unclosed_day) if trace["accepted"] else 0
    trace["EXECUTION_COMPLEXITY"] = _execution_complexity(trace["replacement_change_count"])
    return current_day, current_closure, best_details if trace["accepted"] else {}, trace


def _pulmonary_mode_item(item: dict[str, Any], mode: str) -> dict[str, Any]:
    """Return a pulmonary catalogue item with an explicit V1.0 mode.

    The base pulmonary_id remains stable for catalogue/validator compatibility;
    ``mode_id`` is the clinician-facing distinction for P05 education versus
    therapeutic airway clearance.
    """
    result = deepcopy(item)
    result["pulmonary_mode"] = mode
    result["mode_id"] = f"{result.get('pulmonary_id')}_{mode}"
    return result


def _apply_pulmonary_dose(item: dict[str, Any], dose_level: str) -> dict[str, Any]:
    """Apply only the V1.0 two-level dose mapping; no new thresholds."""
    result = deepcopy(item)
    pid = result.get("pulmonary_id")
    result["dose_level"] = dose_level
    result["dose_reason"] = "Safety yellow conservative" if dose_level == "CONSERVATIVE" else "non-RED standard"
    if pid == "P01":
        result["candidate_dose"] = "3分钟/次" if dose_level == "CONSERVATIVE" else "3–5分钟/次"
        result["dose_range"] = result["candidate_dose"]
        result["frequency_range"] = "2次/日"
    elif pid == "P02":
        result["candidate_dose"] = "5分钟/次" if dose_level == "CONSERVATIVE" else "5–10分钟/次"
        result["dose_range"] = result["candidate_dose"]
        result["frequency_range"] = "1–2次/日" if dose_level == "CONSERVATIVE" else "2次/日"
    elif pid == "P03":
        result["candidate_dose"] = "5次/组" if dose_level == "CONSERVATIVE" else "5–10次/组"
        result["dose_range"] = result["candidate_dose"]
        result["frequency_range"] = "1组/日" if dose_level == "CONSERVATIVE" else "1–2组/日"
    return result


def _select_pulmonary_plan(
    payload: dict[str, Any],
    *,
    safety_level: str,
    pulmonary_cfg: dict[str, Any] | None,
    clinician_inputs: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """Select the V1.0 pulmonary plan without inferring clinician-only inputs.

    P01/P02 are the non-RED base skills. P03/P04 require explicit structured
    clinician indications. P05 has education and therapeutic clearance modes;
    P06 requires both clinician gates. RED always wins.
    """
    if safety_level == "red":
        return [], "BLOCKED_RED", {"p03_indicated": False, "p04_indicated": False, "p05_education": False, "p05_airway_clearance": False, "p06": False}

    clinician_inputs = clinician_inputs or {}
    dose_level = "CONSERVATIVE" if safety_level == "yellow" else "STANDARD"
    catalog = {}
    if isinstance(pulmonary_cfg, dict) and pulmonary_cfg.get("items"):
        catalog = {x.get("pulmonary_id"): x for x in pulmonary_cfg["items"] if x.get("pulmonary_id")}
    else:
        ids = pulmonary_cfg.get("ids") if isinstance(pulmonary_cfg, dict) else None
        source = ids or list(PULMONARY)
        catalog = {pid: PULMONARY[pid] for pid in source if pid in PULMONARY}

    selected: list[dict[str, Any]] = []
    # P01/P02 are the V1.0 base skills for every non-RED pre-operative patient.
    for pid in ("P01", "P02"):
        if pid in catalog:
            selected.append(_apply_pulmonary_dose(catalog[pid], dose_level))

    p03_indicated = clinician_inputs.get("p03_indicated") is True
    p04_indicated = clinician_inputs.get("p04_indicated") is True
    if p03_indicated and "P03" in catalog:
        selected.append(_apply_pulmonary_dose(catalog["P03"], dose_level))
    if p04_indicated and "P04" in catalog:
        selected.append(deepcopy(catalog["P04"]))

    symptoms = set(normalize_selection(_value(payload, "q12_respiratorySymptoms", "respiratory_symptoms"))["positive_items"])
    airway_signals = {"咳痰", "痰液增多", "排痰困难", "分泌物管理需求"}
    p05_airway = bool(symptoms & airway_signals)
    if "P05" in catalog:
        education = _pulmonary_mode_item(catalog["P05"], "EDUCATION")
        education["candidate_dose"] = "本周至少1次术前有效咳嗽技能学习/练习"
        education["dose_range"] = education["candidate_dose"]
        education["frequency_range"] = "本周1次，之后按需复习"
        education["requires_daily_task"] = False
        selected.append(education)
        if p05_airway:
            airway = _pulmonary_mode_item(catalog["P05"], "AIRWAY_CLEARANCE")
            airway["candidate_dose"] = "2次咳嗽/循环×2–5循环"
            airway["dose_range"] = airway["candidate_dose"]
            airway["frequency_range"] = "按需"
            airway["requires_daily_task"] = True
            selected.append(airway)

    p06_device = clinician_inputs.get("p06_device_available") is True
    p06_ordered = clinician_inputs.get("p06_clinician_ordered") is True
    p06_selected = p06_device and p06_ordered and "P06" in catalog
    if p06_selected:
        p06 = deepcopy(catalog["P06"])
        p06["device_available"] = True
        p06["clinician_ordered"] = True
        p06["dose_level"] = "STANDARD"
        selected.append(p06)

    trace = {
        "dose_level": dose_level,
        "p03_indicated": p03_indicated,
        "p04_indicated": p04_indicated,
        "p05_education": "P05" in catalog,
        "p05_airway_clearance": p05_airway,
        "p06": p06_selected,
        "p06_gate": {"device_available": p06_device, "clinician_ordered": p06_ordered},
    }
    return selected, dose_level, trace


def build_v2_plan(
    payload: dict[str, Any],
    evaluation: dict[str, Any],
    *,
    active_configs: dict[str, Any] | None = None,
    pulmonary_clinician_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # V4 keeps the legacy display phenotype for compatibility, while all
    # nutrition/energy decisions use the underlying A-E phenotype.  The
    # imports remain local so the legacy rules module can continue importing
    # this engine without a module cycle.
    from .v4_contract import derive_v4_phenotype
    from .v4_energy_state import derive_energy_state
    from .v4_safety_contract import apply_v4_safety_contract_floor

    legacy_phenotype = str(evaluation.get("phenotype_code") or evaluation.get("phenotype") or "A").split("｜", 1)[0].strip()
    v4_phenotype_contract = evaluation.get("v4_phenotype_contract") or derive_v4_phenotype(payload)
    nutrition_phenotype = v4_phenotype_contract.get("primary_nutrition_phenotype") or legacy_phenotype
    display_phenotype = v4_phenotype_contract.get("display_phenotype") or legacy_phenotype
    # ``phenotype`` remains the display/legacy field.  New machine consumers
    # must use ``primary_nutrition_phenotype`` and ``complexity_overlay``.
    phenotype = display_phenotype
    q56 = parse_q56(payload.get("q56_goal", payload.get("Q56")))
    liver = evaluation.get("liver", {})
    safety_contract = apply_v4_safety_contract_floor(
        existing_safety_level=evaluation.get("safety", "green"),
        existing_reason_codes=evaluation.get("safety_reason_codes", []),
        primary_nutrition_phenotype=nutrition_phenotype,
        complexity_overlay=v4_phenotype_contract.get("complexity_overlay"),
    )
    safety_level = safety_contract["safety_level"]
    trace = energy_trace(payload, nutrition_phenotype, q56, safety_level, active_configs=active_configs)
    v4_energy_state = derive_energy_state(
        phenotype_contract=v4_phenotype_contract,
        energy_trace=trace,
        payload=payload,
        active_configs=active_configs,
        safety_level=safety_level,
    )
    # A structure-only state must not expose a fabricated exact target to the
    # nutrition closure.  The legacy trace remains available for diagnostics,
    # but generation receives null targets in this mode.
    generation_energy_target = (
        v4_energy_state["energy_target"].get("prescribed_energy_target_kcal")
        or v4_energy_state["energy_target"].get("provisional_energy_target_kcal")
    )
    if v4_energy_state["diet_generation_mode"] == "STRUCTURE_ONLY":
        generation_energy_target = None
    trace["legacy_candidate_energy_target_kcal"] = trace.get("daily_energy_target_kcal")
    trace["daily_energy_target_kcal"] = generation_energy_target
    trace["energy_target_status"] = v4_energy_state["energy_target"]["status"]
    trace["diet_generation_mode"] = v4_energy_state["diet_generation_mode"]
    enhanced_ok, enhanced_reasons = enhanced_eligibility(payload, nutrition_phenotype, safety_level, q56, liver)
    goal_conflict = q56.get("primary_goal") == "ENHANCED_FAT_LOSS" and not enhanced_ok
    candidate_mode = bool(isinstance(active_configs, dict) and (active_configs.get("environment") == "TEST_ONLY" or any(isinstance(v, dict) and (v.get("environment") == "TEST_ONLY" or v.get("status") == "CANDIDATE") for v in active_configs.values())))
    # Provisional and structure-only energy chains are reviewable drafts, but
    # cannot be published as if their energy source were ACTIVE.  This is a
    # candidate-content governance flag only; the publication workflow remains
    # unchanged and still owns the final gate.
    energy_requires_review = (
        v4_energy_state["energy_target"]["status"] != "ACTIVE"
        or v4_energy_state["diet_generation_mode"] != "EXACT_ACTIVE"
    )
    publication_blocked = (
        safety_level == "red"
        or goal_conflict
        or trace.get("energy_estimation_conflict", False)
        or energy_requires_review
    )
    draft_source = "ACTIVE_MDT" if not candidate_mode and active_configs and all(not isinstance(v, dict) or v.get("status", "ACTIVE") == "ACTIVE" for v in active_configs.values()) else "CANDIDATE_MDT" if candidate_mode else "RULE_BASED_PENDING"
    goal_source = "Q56_CLINICIAN" if q56.get("has_clinician_goal") else "SYSTEM_DEFAULT_AF"
    exercise_cfg = (active_configs or {}).get("V2-EXERCISE-ACTIONS") or (active_configs or {}).get("EXERCISE_IDS") or {}
    exercise_ids = exercise_cfg.get("ids") if isinstance(exercise_cfg, dict) else None
    if isinstance(exercise_cfg, dict) and exercise_cfg.get("items"):
        exercise_catalog = {x.get("exercise_id"): x for x in exercise_cfg["items"]}
    else:
        exercise_catalog = ({eid: EXERCISES[eid] for eid in exercise_ids if eid in EXERCISES} if exercise_ids else EXERCISES)
    catalog_items_supplied = bool(isinstance(exercise_cfg, dict) and exercise_cfg.get("items"))
    # q37_activityLimits is the canonical Q1-Q56-v1.2 answer key. Prefer it,
    # then the normalized internal alias, and finally the legacy pre-v1.2
    # spelling for historical assessments. This keeps a legacy alias from
    # masking a newer canonical answer when both are present.
    # Preserve an explicitly submitted empty canonical list as authoritative
    # too; `_value()` intentionally skips [] for ordinary aliases.
    q37_value = (
        payload.get("q37_activityLimits")
        if "q37_activityLimits" in payload and payload.get("q37_activityLimits") is not None
        else _value(payload, "activity_limitations", "q37_activityLimitations")
    )
    restrictions = set(normalize_selection(q37_value)["positive_items"])
    pulmonary_cfg = (active_configs or {}).get("V2-PULMONARY-ACTIONS") or {}
    selected_pulmonary, pulmonary_dose_level, pulmonary_trace = _select_pulmonary_plan(
        payload,
        safety_level=safety_level,
        pulmonary_cfg=pulmonary_cfg,
        clinician_inputs=pulmonary_clinician_inputs,
    )
    v3_flat_exercise, v3_weekly_schedule, v3_combo = build_v3_weekly_exercise(
        exercise_catalog, phenotype, restrictions=restrictions, safety_level=safety_level,
        pulmonary=selected_pulmonary,
    )
    e_formal_aerobic_eligibility = None
    if nutrition_phenotype == "E":
        from .v4_e_exercise_eligibility import (
            apply_e_eligibility_to_schedule,
            derive_e_formal_aerobic_eligibility,
        )
        e_formal_aerobic_eligibility = derive_e_formal_aerobic_eligibility(
            payload,
            safety_level=safety_level,
            primary_nutrition_phenotype=nutrition_phenotype,
            existing_reason_codes=evaluation.get("safety_reason_codes", []),
        )
        v3_weekly_schedule, e_schedule_adjustment = apply_e_eligibility_to_schedule(
            v3_weekly_schedule,
            e_formal_aerobic_eligibility,
        )
        if e_schedule_adjustment.get("formal_aerobic_days_target") is not None:
            # Preserve the legacy candidate range for audit while making the
            # canonical trace's declared target reflect the resolved E gate.
            v3_combo = deepcopy(v3_combo)
            v3_combo["legacy_aerobic_days_target"] = v3_combo.get("aerobic_days_target")
            v3_combo["aerobic_days_target"] = e_schedule_adjustment["formal_aerobic_days_target"]
            v3_combo["functional_activity_days_target"] = e_schedule_adjustment.get("functional_activity_days_target")
    # Phase 3B-1: adapt the final legacy V3 candidate into one canonical,
    # auditable exercise week.  Selection, dose intent and clinical rules
    # remain owned by build_v3_weekly_exercise; this adapter only normalizes
    # identity/roles and derives counts after the candidate is complete.
    from .v4_exercise_trace import build_canonical_exercise_week
    canonical_exercise_week, v4_weekly_schedule, v4_flat_exercise = build_canonical_exercise_week(
        v3_weekly_schedule,
        combo=v3_combo,
        v4_phenotype_contract=v4_phenotype_contract,
        q56_goal=q56,
        surgery_window=_value(payload, "q6_surgeryWindow"),
        safety_level=safety_level,
        allowed_action_ids=set(v3_combo.get("allowed_action_ids") or []),
        e_formal_aerobic_eligibility=e_formal_aerobic_eligibility,
    )
    v3_weekly_schedule = v4_weekly_schedule
    v3_flat_exercise = v4_flat_exercise
    if safety_level == "red":
        selected_exercise = []
    else:
        # The canonical adapter is now the source for the patient-facing flat
        # list as well as the seven-day schedule.  Action IDs remain stable,
        # so older consumers retain their existing lookup behaviour.
        selected_exercise = v3_flat_exercise
    if safety_level == "red":
        goal_text = "当前存在红色安全信号，暂停自动进阶并转医护处理。"
    else:
        goal_text = Q56_PRIMARY.get(q56.get("primary_goal"), AF_DEFAULTS.get(nutrition_phenotype, AF_DEFAULTS["A"])["mode"])
    # Resolve existing nutrition targets before candidate selection so they can
    # participate in ranking (the values themselves still come from the
    # established energy/protein configurations).
    protein_cfg = (active_configs or {}).get("V2-PROTEIN-MACROS") or {}
    protein_target = None
    weight_for_protein = _value(payload, "q15_weight", "weight_kg")
    if isinstance(protein_cfg, dict) and protein_cfg.get("status") in {"ACTIVE", "CANDIDATE"} and weight_for_protein is not None:
        try: protein_target = round(float(weight_for_protein) * AF_DEFAULTS.get(nutrition_phenotype, AF_DEFAULTS["A"])["protein_g_per_kg"], 1)
        except (TypeError, ValueError): protein_target = None
    if v4_energy_state["diet_generation_mode"] == "STRUCTURE_ONLY":
        protein_target = None
    macro_cfg = (active_configs or {}).get("V2-MACRO-CANDIDATES") or {}
    meal_cfg = (active_configs or {}).get("V2-MEAL-DISTRIBUTION") or {}
    carb_range = macro_cfg.get("carbohydrate_pct_range") if isinstance(macro_cfg, dict) else None
    fat_range = macro_cfg.get("fat_pct_range") if isinstance(macro_cfg, dict) else None
    meal_distribution = meal_cfg.get("distribution_pct_range") if isinstance(meal_cfg, dict) else None
    nutrition_trace = {
        "phenotype": nutrition_phenotype,
        "energy_target": generation_energy_target,
        "energy_target_status": v4_energy_state["energy_target"]["status"],
        "diet_generation_mode": v4_energy_state["diet_generation_mode"],
        "protein_target": protein_target,
        "carbohydrate_target": carb_range,
        "fat_target": fat_range,
        "selected_food_reason": [],
        "rejected_food_reason": [],
    }
    food_cfg = (active_configs or {}).get("V2-FOOD-COMPONENTS") or {}
    food_confirmed = bool(isinstance(food_cfg, dict) and food_cfg.get("status") in {"ACTIVE", "CANDIDATE"})
    catalog_foods = list(food_cfg.get("items") or []) if isinstance(food_cfg, dict) and food_cfg.get("items") else []
    nutrition_generation_status = "complete"
    nutrition_generation_missing_reasons: list[str] = []
    if catalog_foods:
        # Do not silently fall back to the legacy first-item/default menu when
        # the catalog cannot support a safe weekly rotation.
        category_counts = {
            category: sum(1 for item in catalog_foods if item.get("category") == category and _food_allowed(item, payload) and item.get("component_id"))
            for category in ("staple", "protein", "vegetable", "snack")
        }
        insufficient = [category for category, count in category_counts.items() if count < 2]
        if insufficient:
            nutrition_generation_status = "incomplete"
            nutrition_generation_missing_reasons.append("可安全轮换的食物候选不足：" + "、".join(insufficient))
        # Select each day's staple/protein/vegetable independently. This
        # replaces the old eligible_items[0] selection and preserves a used
        # history for every food category.
        if nutrition_generation_status == "complete":
            rotating_meals, rotation_limited = _build_rotating_weekly_meals(
                catalog_foods, payload, phenotype=nutrition_phenotype, goal=q56,
                energy_target=generation_energy_target,
                protein_target=protein_target, carb_range=carb_range,
                fat_range=fat_range, meal_distribution=meal_distribution,
                nutrition_trace=nutrition_trace,
            )
            meals = rotating_meals[0]
        else:
            rotating_meals = [{} for _ in range(7)]
            meals = {}
            rotation_limited = True
        for day_meals in rotating_meals:
            for meal in day_meals.values():
                meal["mdt_confirmed"] = food_confirmed
                for component in meal.get("components") or []:
                    component["mdt_confirmed"] = food_confirmed
                    component["status"] = "ACTIVE" if food_confirmed else "候选组件，待医护确认"
    else:
        # No catalog means no generated diet. Keep independent day containers
        # so callers never observe the same meal object reused across the week.
        nutrition_generation_status = "incomplete"
        nutrition_generation_missing_reasons.append("未提供可调用的FOOD catalog")
        meals = {}
        rotating_meals = [{} for _ in range(7)]
        rotation_limited = True
    if rotation_limited and not nutrition_generation_missing_reasons:
        nutrition_generation_missing_reasons.append("安全候选不足，无法满足7天轮换要求")
    meals_complete = all(all(meal.get(key) not in (None, "") for key in ("ingredient_name", "ingredient_amount", "unit", "raw_or_cooked_basis")) for meal in meals.values())
    all_active = bool(trace.get("mdt_confirmed") and food_confirmed and meals_complete and isinstance(exercise_cfg, dict) and exercise_cfg.get("status") == "ACTIVE" and isinstance(pulmonary_cfg, dict) and pulmonary_cfg.get("status") == "ACTIVE")
    # P2: independently size every day from the selected components.  The
    # previous implementation scaled only the first day's aggregate meal;
    # this path keeps seven independent portion/closure results.
    daily_closures: list[dict[str, Any]] = []
    portion_adjustment_limited = False
    portion_adjustment_reasons: list[str] = []
    replacement_optimization: list[dict[str, Any]] = []
    if nutrition_generation_status == "complete":
        for day_number, day_meals in enumerate(rotating_meals, start=1):
            base_day_meals = deepcopy(day_meals)
            closure, details = _close_day_meals(
                day_number,
                day_meals,
                daily_energy=generation_energy_target,
                protein_target=protein_target,
                carb_range=carb_range,
                fat_range=fat_range,
                meal_distribution=meal_distribution,
            )
            daily_closures.append(closure)
            nutrition_trace["meal_energy_target"] = nutrition_trace.get("meal_energy_target", [])
            nutrition_trace["meal_energy_actual"] = nutrition_trace.get("meal_energy_actual", [])
            nutrition_trace["protein_distribution"] = nutrition_trace.get("protein_distribution", [])
            nutrition_trace["portion_adjustments"] = nutrition_trace.get("portion_adjustments", [])
            nutrition_trace["meal_energy_target"].append(details["meal_energy_target"])
            nutrition_trace["meal_energy_actual"].append(details["meal_energy_actual"])
            nutrition_trace["protein_distribution"].append(details["protein_distribution"])
            nutrition_trace["portion_adjustments"].extend(details["portion_adjustments"])
            if closure.get("portion_adjustment_limited"):
                portion_adjustment_limited = True
                portion_adjustment_reasons.extend(closure.get("reasons") or [])
            # Post-selection whole-day review. This is intentionally bounded
            # and only runs when an energy/protein core metric is outside the
            # existing engineering tolerance; normally closed days are left
            # untouched.
            optimized_day, optimized_closure, optimized_details, replacement_trace = _optimize_day_replacements(
                day_number - 1,
                rotating_meals,
                catalog_foods,
                payload,
                phenotype=nutrition_phenotype,
                goal=q56,
                energy_target=generation_energy_target,
                protein_target=protein_target,
                carb_range=carb_range,
                fat_range=fat_range,
                meal_distribution=meal_distribution,
                base_day_meals=base_day_meals,
                baseline_closure=closure,
            )
            replacement_optimization.append(replacement_trace)
            if replacement_trace.get("accepted"):
                rotating_meals[day_number - 1] = optimized_day
                daily_closures[-1] = optimized_closure
                # Replace this day's closure trace so it describes the final
                # accepted component set rather than the pre-replacement trial.
                nutrition_trace["portion_adjustments"] = [
                    item for item in nutrition_trace["portion_adjustments"] if item.get("day") != day_number
                ]
                nutrition_trace["portion_adjustments"].extend(optimized_details.get("portion_adjustments") or [])
                nutrition_trace["meal_energy_actual"][day_number - 1] = optimized_details.get("meal_energy_actual", {})
    else:
        daily_closures = [{"day": day, "energy_target": generation_energy_target, "energy_actual": None, "energy_delta_pct": None, "protein_target": protein_target, "protein_actual": None, "protein_delta_pct": None, "carbohydrate_target": None, "carbohydrate_actual": None, "fat_target": None, "fat_actual": None, "closure_status": "INCOMPLETE", "reasons": nutrition_generation_missing_reasons or ["未生成饮食组件"], "portion_adjustment_limited": True} for day in range(1, 8)]
        nutrition_trace.setdefault("meal_energy_target", [])
        nutrition_trace.setdefault("meal_energy_actual", [])
        nutrition_trace.setdefault("protein_distribution", [])
        nutrition_trace.setdefault("portion_adjustments", [])
    nutrition_trace["closure_result"] = daily_closures
    nutrition_trace["replacement_optimization"] = replacement_optimization
    changed_counts = [int(item.get("replacement_change_count") or 0) for item in replacement_optimization]
    nutrition_trace["replacement_execution_complexity"] = {
        "total_changed_components": sum(changed_counts),
        "max_changed_components_per_day": max(changed_counts, default=0),
        "max_level": max(
            (item.get("EXECUTION_COMPLEXITY", "LOW") for item in replacement_optimization),
            key={"LOW": 0, "MODERATE": 1, "HIGH": 2}.get,
            default="LOW",
        ),
        "engineering_audit_only": True,
    }
    nutrition_trace["portion_adjustment_limited"] = portion_adjustment_limited
    nutrition_trace["portion_adjustment_reason"] = list(dict.fromkeys(portion_adjustment_reasons))
    nutrition_trace["v4_scale_coordination"] = _v4_scale_coordination_diagnostic(
        rotating_meals,
        daily_closures,
        replacement_optimization,
    )
    # Phase 2B: materialize only after the final replacement/closure decision.
    # The returned compatibility meals are projections of the same canonical
    # object; no later nutrition or portion optimizer runs after this point.
    legacy_rotating_meals = rotating_meals
    try:
        from .v4_diet_materialization import materialize_canonical_week_diet
        from .v4_food_data import load_v4_food_data
        active_food_version = load_v4_food_data().asset_provenance.food_execution.version
        canonical_week_diet, projected_rotating_meals = materialize_canonical_week_diet(
            legacy_rotating_meals,
            energy_state=v4_energy_state,
            context_snapshot={
                "patient_id": payload.get("patient_id"),
                "primary_nutrition_phenotype": nutrition_phenotype,
                "complexity_overlay": v4_phenotype_contract.get("complexity_overlay"),
                "energy_state": deepcopy(v4_energy_state),
                "food_source": f"ZXY_WEEK1_V4_FREEZE/{active_food_version}",
            },
        )
        rotating_meals = projected_rotating_meals
    except Exception as exc:  # explicit trace failure; never hide legacy state
        canonical_week_diet = {
            "trace_schema_version": "FOOD_TRACE_V4_2",
            "trace_materialization_status": "MISSING",
            "generation_context": {"error": str(exc)},
            "days": [],
            "trace_validation": {"status": "FAIL", "error": str(exc)},
        }
        # Do not expose legacy base×scale amounts when the V4 materializer
        # itself is unavailable.  The explicit MISSING trace is the only
        # result; callers must route it to review rather than use stale grams.
        rotating_meals = [{} for _ in range(7)]
    meals = rotating_meals[0] if rotating_meals else {}
    legacy_meals_for_totals = legacy_rotating_meals[0] if legacy_rotating_meals else {}
    meal_totals = {"energy_kcal": sum((m.get("estimated_energy") or 0) for m in legacy_meals_for_totals.values()), "protein_g": sum((m.get("estimated_protein") or 0) for m in legacy_meals_for_totals.values()), "carbohydrate_g": sum((m.get("estimated_carbohydrate") or 0) for m in legacy_meals_for_totals.values()), "fat_g": sum((m.get("estimated_fat") or 0) for m in legacy_meals_for_totals.values())}
    warn_days = [item["day"] for item in daily_closures if item.get("closure_status") == "WARN"]
    incomplete_days = [item["day"] for item in daily_closures if item.get("closure_status") == "INCOMPLETE"]
    nutrition_review_required = bool(warn_days or incomplete_days)
    nutrition_review = {
        "required": nutrition_review_required,
        "warn_days": warn_days,
        "incomplete_days": incomplete_days,
        "issues": [
            {
                "day": item["day"],
                "energy_delta_pct": item.get("energy_delta_pct"),
                "protein_delta_pct": item.get("protein_delta_pct"),
                "reasons": item.get("reasons", []),
                "portion_adjustment_limited": item.get("portion_adjustment_limited", False),
                "portion_adjustment_reason": [
                    reason for reason in item.get("reasons", [])
                    if "份量" in str(reason) or "portion" in str(reason).lower()
                ],
            }
            for item in daily_closures if item.get("closure_status") in {"WARN", "INCOMPLETE"}
        ],
    }
    valid_closures = [item for item in daily_closures if item.get("closure_status") != "INCOMPLETE" and item.get("energy_actual") is not None]
    def _average(key: str) -> float | None:
        values = [_number_or_none(item.get(key)) for item in valid_closures]
        values = [value for value in values if value is not None]
        return round(sum(values) / len(values), 3) if values else None
    weekly_nutrition_summary = {
        "average_energy_actual": _average("energy_actual"),
        "average_energy_delta_pct": _average("energy_delta_pct"),
        "average_protein_actual": _average("protein_actual"),
        "average_protein_delta_pct": _average("protein_delta_pct"),
        "days_pass": sum(item.get("closure_status") == "PASS" for item in daily_closures),
        "days_warn": len(warn_days),
        "days_incomplete": len(incomplete_days),
    }
    nutrition_trace["closure_result"] = daily_closures
    nutrition_trace["nutrition_review_required"] = nutrition_review_required
    nutrition_trace["weekly_nutrition_summary"] = weekly_nutrition_summary
    nutrition_complete = nutrition_generation_status == "complete" and all(all(meal.get(key) not in (None, "") for key in ("ingredient_name", "ingredient_amount", "unit", "raw_or_cooked_basis", "cooking_method")) for meal in meals.values()) and all(v is not None for m in meals.values() for v in (m.get("estimated_energy"), m.get("estimated_protein"), m.get("estimated_carbohydrate"), m.get("estimated_fat")))
    target_energy = generation_energy_target
    closure_ok = nutrition_generation_status == "complete" and bool(daily_closures) and all(item.get("closure_status") == "PASS" for item in daily_closures) if target_energy is not None else nutrition_generation_status == "complete"
    # Separate content integrity from governance/publish eligibility. Candidate
    # values can produce a complete clinician draft while remaining blocked
    # until MDT promotion; publication status must not masquerade as a content
    # validation failure.
    content_validation = "PASS" if nutrition_complete and closure_ok else "FAIL"
    publish_validation = "BLOCKED" if publication_blocked else "PASS"
    content_errors = [] if content_validation == "PASS" else ["营养餐次字段或营养闭合未通过"]
    review_validation = "PASS" if content_validation == "PASS" else "BLOCKED"
    publish_block_reasons = (["安全状态/目标冲突"] if safety_level == "red" or goal_conflict else [])
    if trace.get("energy_estimation_conflict", False):
        publish_block_reasons.append("能量估算冲突需复核")
    if energy_requires_review:
        publish_block_reasons.append("能量状态为PROVISIONAL/UNAVAILABLE，需医护审核")
    validation = {"nutrition_plan_validation": content_validation, "content_validation": content_validation,
                  "exercise_validation": "PASS" if selected_exercise or safety_level == "red" else "BLOCKED",
                  "pulmonary_validation": "PASS" if selected_pulmonary or safety_level == "red" else "BLOCKED",
                  "safety_validation": "BLOCKED" if safety_level == "red" or goal_conflict else "PASS",
                  "review_validation": review_validation, "publish_validation": publish_validation,
                  "publish_block_reasons": publish_block_reasons,
                  "nutrition_closure": {**meal_totals, "target_energy_kcal": target_energy, "within_20pct": closure_ok, "tolerance": VALIDATION_TOLERANCE, "tolerance_type": "VALIDATION_TOLERANCE", "daily": daily_closures}, "nutrition_review_required": nutrition_review_required, "nutrition_review": nutrition_review, "weekly_nutrition_summary": weekly_nutrition_summary, "errors": content_errors}
    review_eligible = review_validation == "PASS"
    weekly_schedule = []
    for index, day in enumerate(v3_weekly_schedule):
        day_view = {**deepcopy(day), "diet": list(deepcopy(rotating_meals[index] if index < len(rotating_meals) else {}).values())}
        if index < len(daily_closures):
            closure = deepcopy(daily_closures[index])
            day_view["nutrition_closure"] = closure
            day_view["actual_energy"] = closure.get("energy_actual")
            day_view["actual_protein"] = closure.get("protein_actual")
            day_view["actual_carbohydrate"] = closure.get("carbohydrate_actual")
            day_view["actual_fat"] = closure.get("fat_actual")
        weekly_schedule.append(day_view)
    plan = {
        "contract_version": "2.1",
        "management_period": {"stage": "术前第一周", "surgery_window": _value(payload, "q6_surgeryWindow"), "cycle_days": 7},
        "goal_source": goal_source,
        "draft_source": draft_source,
        "candidate_draft": candidate_mode,
        "rule_authority": "PROJECT_BASELINE_V2_V3",
        "review_eligible": review_eligible,
        "publish_eligible": bool(review_eligible and not publication_blocked),
        "clinician_goal_q56": q56,
        "phenotype": phenotype,
        "primary_nutrition_phenotype": nutrition_phenotype,
        "complexity_overlay": v4_phenotype_contract["complexity_overlay"],
        "display_phenotype": display_phenotype,
        "v4_phenotype_contract": v4_phenotype_contract,
        "energy_state": v4_energy_state,
        "surgery_window": _value(payload, "q6_surgeryWindow"),
        "safety_level": safety_level,
        "safety_reason_codes": safety_contract["safety_reason_codes"],
        "safety_floor_applied": safety_contract["safety_floor_applied"],
        "safety_floor_sources": safety_contract["safety_floor_sources"],
        "pulmonary_rule_version": "V1.0",
        "pulmonary_dose_level": pulmonary_dose_level,
        "pulmonary_selection_trace": pulmonary_trace,
        "formal_aerobic_eligibility": deepcopy(e_formal_aerobic_eligibility),
        "e_formal_aerobic_validation": deepcopy(
            canonical_exercise_week.get("context_snapshot", {}).get("e_formal_aerobic_validation")
        ),
        "enhanced_eligible": enhanced_ok,
        "enhanced_ineligible_reasons": enhanced_reasons,
        "goal_conflict": goal_conflict,
        "publication_blocked": publication_blocked,
        "manual_review_required": publication_blocked or bool(evaluation.get("need_clinician_review")),
        "stage_goals": {"overall_goal": goal_text, "weight_goal": q56.get("target_weight_kg"), "body_fat_goal": None, "waist_goal": None, "muscle_goal": "优先保护肌肉，具体目标待医护确认", "functional_goal": None, "metabolic_goals": None, "surgery_preparation_goal": "完成术前安全准备和预康复技能练习"},
        "energy_calculation": trace,
        "nutrition_trace": nutrition_trace,
        # Phase 2B canonical root. Compatibility projections below are
        # produced from this same materialized week, never recalculated.
        "canonical_week_diet": canonical_week_diet,
        "diet_plan_trace": canonical_week_diet,
        "canonical_exercise_week": canonical_exercise_week,
        "exercise_plan_trace": canonical_exercise_week,
        "replacement_optimization": replacement_optimization,
        "nutrition_generation_status": nutrition_generation_status,
        "nutrition_generation_missing_reasons": nutrition_generation_missing_reasons,
        "body_composition_targets": {"weight": q56.get("target_weight_kg"), "body_fat": None, "waist": None, "muscle": "保护"},
        "diet_plan": {"daily_energy_target": trace["daily_energy_target_kcal"], "protein_target": protein_target,
                      "carbohydrate_target": ({"min_pct": carb_range[0], "max_pct": carb_range[1], "basis": "energy_percent", "status": "CANDIDATE"} if isinstance(carb_range, list) and len(carb_range) == 2 else None),
                      "fat_target": ({"min_pct": fat_range[0], "max_pct": fat_range[1], "basis": "energy_percent", "status": "CANDIDATE"} if isinstance(fat_range, list) and len(fat_range) == 2 else None),
                      "meal_distribution": meal_distribution, "meal_frequency": "3+1", **meals, "components": [*meals.values()], "daily_energy_total": meal_totals["energy_kcal"], "daily_protein_total": meal_totals["protein_g"], "daily_carbohydrate_total": meal_totals["carbohydrate_g"], "daily_fat_total": meal_totals["fat_g"], "nutrition_closure": daily_closures, "nutrition_review_required": nutrition_review_required, "nutrition_review": nutrition_review, "weekly_nutrition_summary": weekly_nutrition_summary, "nutrition_plan_validation": validation["nutrition_plan_validation"], "nutrition_generation_status": nutrition_generation_status, "nutrition_generation_missing_reasons": nutrition_generation_missing_reasons, "rotation_limited": rotation_limited, "portion_adjustment_limited": portion_adjustment_limited, "portion_adjustment_reason": list(dict.fromkeys(portion_adjustment_reasons)), "mdt_confirmed": food_confirmed},
        "exercise_plan": selected_exercise,
        "pulmonary_prehab_plan": selected_pulmonary,
        "monitoring_plan": {"items": ["体重", "体脂率", "腰围", "饮食执行", "运动执行", "肺预康复执行", "疲劳/气促/疼痛"], "frequency": "每日记录，周末复评", "thresholds": None, "instructions": "按已发布任务记录实际完成情况；异常及时联系医护。"},
        "daily_record_requirements": {"body_weight": "R", "body_fat": "O", "waist": "CR", "meal_completion": "R", "protein_completion": "CR", "exercise_actual": "CR", "pulmonary_actual": "CR", "symptoms": "R"},
        # Each day receives its own deep-copied diet container.  Never reuse a
        # fallback meal object for missing days.
        "weekly_schedule": weekly_schedule,
        "exercise_weekly_prescription": v3_combo,
        "weekly_review": {"confidence": "LOW", "decision": "DATA_INSUFFICIENT", "reason": "尚未积累7天执行记录"},
        "next_week_adjustment": {"status": "待周复评", "changes": [], "safety_review_required": True},
        "safety_rules": {"safety_level": safety_level, "reason_codes": safety_contract["safety_reason_codes"], "safety_floor_applied": safety_contract["safety_floor_applied"], "safety_floor_sources": safety_contract["safety_floor_sources"], "precautions": "不自动改药、不跳餐、不以目标体重倒算热量。", "stop_conditions": "胸痛/胸闷、明显气促、头晕、咯血、意识异常等立即停止并转医护。", "blocked_modules": ["exercise", "pulmonary_prehab", "enhanced_fat_loss"] if safety_level == "red" or goal_conflict else [], "goal_conflict": goal_conflict, "publication_blocked": publication_blocked},
        "clinician_notes": {"review_required": True, "note": "规则生成候选方案，须医护审核后发布。"},
        "missing_data": evaluation.get("missing_data", []),
        # Candidate values are usable for the clinician-only draft. Keep the
        # pending list for fields that are genuinely unresolved; governance
        # blocking remains explicit in publish_validation/publish_block_reasons.
        "mdt_pending_items": (["脂肪目标比例（V2文档未提供候选值）"] if fat_range is None else [])
            + (["蛋白目标（缺少体重或候选配置）"] if protein_target is None else [])
            + (["运动剂量（所选动作没有文档候选值）"] if any(not (i.get("candidate_dose") or i.get("duration_range") or i.get("dose_range")) for i in selected_exercise) else [])
            + (["肺预康复剂量（所选动作没有文档候选值）"] if any(not (i.get("candidate_dose") or i.get("dose_range")) for i in selected_pulmonary) else []),
        "generator_type": "RULE_BASED", "rule_version": V3_RULE_VERSION, "knowledge_versions": {"food": "V2.0", "exercise": V3_RULE_VERSION, "pulmonary": "V2.0", "template": "V2.1"}, "config_versions": {"status": "PENDING"},
        "validation_result": validation,
        "nutrition_closure": daily_closures,
        "nutrition_review_required": nutrition_review_required,
        "nutrition_review": nutrition_review,
        "weekly_nutrition_summary": weekly_nutrition_summary,
    }
    # Run the shared validator as the final contract gate.  It is intentionally
    # imported lazily to keep this engine independent of DB/runtime modules.
    try:
        from .plan_validator import validate_plan
        candidate_env = isinstance(active_configs, dict) and (active_configs.get("environment") == "TEST_ONLY" or any(isinstance(v, dict) and v.get("environment") == "CANDIDATE_MDT" for v in active_configs.values()))
        mode = "TEST_ONLY" if candidate_env else "production"
        allowed_ex = set((exercise_cfg or {}).get("ids", [])) if isinstance(exercise_cfg, dict) else None
        allowed_pr = set((pulmonary_cfg or {}).get("ids", [])) if isinstance(pulmonary_cfg, dict) else None
        plan["validation_result"] = {**plan["validation_result"], "contract_validator": validate_plan(plan, mode=mode, allowed_exercise_ids=allowed_ex, allowed_pulmonary_ids=allowed_pr)}
    except Exception:
        pass
    return plan


def weekly_review(records: list[dict[str, Any]], *, phenotype: str | None = None, safety_level: str = "green", q56_goal: dict[str, Any] | None = None, surgery_window: str | None = None) -> dict[str, Any]:
    """Seven-day review using persisted records only (pending local records excluded by caller)."""
    valid = sorted((r for r in records if not r.get("pending_sync")), key=lambda r: str(r.get("record_date") or ""))
    def meta(r: dict[str, Any]) -> dict[str, Any]:
        value = r.get("metadata_json", r.get("metadata", {}))
        return value if isinstance(value, dict) else {}
    def nums(key: str) -> list[float]:
        out = []
        for r in valid:
            value = r.get(key, meta(r).get(key))
            try:
                if value is not None: out.append(float(value))
            except (TypeError, ValueError): pass
        return out
    weights, fats, muscles, waters, waists = (nums(k) for k in ("weight_kg", "body_fat_pct", "skeletal_muscle_mass", "water_pct", "waist_cm"))
    def rate(keys: tuple[str, ...], types: set[str] | None = None) -> float | None:
        values = []
        for r in valid:
            if types and r.get("record_type") not in types:
                continue
            m = meta(r)
            v = next((m.get(k, r.get(k)) for k in keys if m.get(k, r.get(k)) is not None), None)
            if isinstance(v, str): values.append(1.0 if v.lower() in {"completed", "complete", "全部", "all", "100%"} else 0.5 if v.lower() in {"partial", "部分", "75%", "75-89%"} else 0.0)
            elif isinstance(v, (int, float)): values.append(float(v) / 100 if float(v) > 1 else float(v))
        return sum(values) / len(values) if values else None
    diet_rate = rate(("diet_completion", "daily_plan_completion"), {"DIET"}); protein_rate = rate(("protein_completion", "protein_component_completion"), {"DIET"})
    exercise_rate = rate(("exercise_completion", "status"), {"EXERCISE"}); pulmonary_rate = rate(("pulmonary_completion", "status"), {"PULMONARY", "PULMONARY_PREHAB"})
    fatigue, dyspnea, pain = nums("fatigue"), nums("dyspnea"), nums("pain")
    safety_events = [r for r in valid if meta(r).get("safety_level") in {"red", "yellow"} or meta(r).get("new_symptoms") in {"有", "yes", True}]
    core_days = len({str(r.get("record_date")) for r in valid if r.get("record_date")})
    confidence = "HIGH" if core_days >= 7 and weights else "MODERATE" if core_days >= 4 else "LOW"
    evidence = {"valid_record_count": len(valid), "valid_days": core_days, "weight_avg": round(sum(weights)/len(weights), 2) if weights else None,
                "weight_delta": round(weights[-1]-weights[0], 2) if len(weights) >= 2 else None, "body_fat_trend": fats[-1]-fats[0] if len(fats)>=2 else None,
                "muscle_trend": muscles[-1]-muscles[0] if len(muscles)>=2 else None, "water_trend": waters[-1]-waters[0] if len(waters)>=2 else None,
                "waist_latest": waists[-1] if waists else None, "diet_completion_rate": diet_rate, "protein_completion_rate": protein_rate,
                "exercise_completion_rate": exercise_rate, "pulmonary_completion_rate": pulmonary_rate, "fatigue_avg": sum(fatigue)/len(fatigue) if fatigue else None,
                "dyspnea_avg": sum(dyspnea)/len(dyspnea) if dyspnea else None, "pain_avg": sum(pain)/len(pain) if pain else None}
    triggered, frozen, allowed, recommended = [], [], [], []
    if safety_level == "red" or safety_events: decision = "SAFETY_REVIEW"; triggered.append("安全事件/红色状态"); frozen = ["energy_progression", "exercise_progression", "enhanced_fat_loss"]
    elif confidence == "LOW": decision = "DATA_INSUFFICIENT"; triggered.append("7日核心数据不足")
    elif (diet_rate is not None and diet_rate < .5) or (exercise_rate is not None and exercise_rate < .5): decision = "BARRIER_FIRST"; triggered.append("执行完成率偏低")
    elif phenotype == "E" and ((evidence["weight_delta"] is not None and evidence["weight_delta"] < 0) or (diet_rate is not None and diet_rate < .75)): decision = "NUTRITION_RECOVERY"; triggered.append("营养风险持续")
    elif (evidence["muscle_trend"] is not None and evidence["muscle_trend"] < 0) or (evidence["water_trend"] is not None and evidence["water_trend"] < 0 and diet_rate is not None and diet_rate < .75): decision = "PRESERVE_MUSCLE"; triggered.append("肌肉/水分下降")
    elif phenotype in {"A", "B"} and q56_goal and q56_goal.get("primary_goal") == "ENHANCED_FAT_LOSS" and evidence["weight_delta"] is not None and evidence["weight_delta"] >= 0 and (evidence["muscle_trend"] is None or evidence["muscle_trend"] >= 0): decision = "INTENSIFY_CANDIDATE"; triggered.append("安全且执行稳定但目标轨迹不足")
    else: decision = "MAINTAIN"
    return {"confidence": confidence, "decision": decision, "evidence": evidence, "trend_summary": evidence, "triggered_rules": triggered, "frozen_modules": frozen, "allowed_changes": allowed, "recommended_changes": recommended, "manual_review_required": decision in {"SAFETY_REVIEW", "INTENSIFY_CANDIDATE"}, "reason": "按安全→数据→执行→生理反应→A-F/Q56→手术窗口顺序", "next_week_action": "仅生成新的待审核草稿，不覆盖当前PUBLISHED版本。", "algorithm_version": "V2.0"}
