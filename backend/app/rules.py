from __future__ import annotations

from typing import Any

from .missing_data_policy import structured_missing_context
from .plan_contract import PLAN_CONTENT_CONTRACT_VERSION
from .v2_engine import build_v2_plan, calculate_phenotype, parse_q56, normalize_selection
from .v4_contract import derive_v4_phenotype
from .v4_safety_contract import apply_v4_safety_contract_floor


def _filled(value: Any) -> bool:
    return value is not None and str(value).strip() not in {"", "unknown", "未知"}


def _normalise_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Map V1.1 UI keys to the stable rule input names without changing the
    stored Q1-Q55 answer snapshot."""
    value = dict(payload or {})
    aliases = {
        "height_cm": "q14_height", "weight_kg": "q15_weight", "food_allergy": "q32_foodAllergy",
        "six_minute_walk_m": "q27_walkTest", "surgery_window_days": "q6_surgeryWindow",
        "recent_weight_intake": "q28_weightChange", "respiratory_symptoms": "q12_respiratorySymptoms",
        # Q37's v1.2 canonical answer key. Keep the normalized internal name
        # stable for downstream exercise rules while accepting the legacy
        # spelling as a fallback in the generator.
        "activity_limitations": "q37_activityLimits",
    }
    for target, source in aliases.items():
        if _filled(value.get(target)) or not _filled(value.get(source)):
            continue
        source_value = value[source]
        if target == "six_minute_walk_m" and isinstance(source_value, dict): source_value = source_value.get("distance")
        value[target] = source_value
    # When both a canonical answer and a legacy/internal alias are supplied,
    # the canonical Q1-Q56 field is authoritative. This also makes the
    # normalized payload deterministic for every downstream consumer.
    if _filled(value.get("q37_activityLimits")):
        value["activity_limitations"] = value["q37_activityLimits"]
    elif not _filled(value.get("activity_limitations")) and _filled(value.get("q37_activityLimitations")):
        value["activity_limitations"] = value["q37_activityLimitations"]
    if not _filled(value.get("sex")) and _filled(value.get("profile_sex")): value["sex"] = value["profile_sex"]
    swallowing = value.get("swallowing")
    if not _filled(swallowing):
        raw_difficulties = value.get("q31_eatingDifficulties")
        if raw_difficulties is None:
            difficulties = []
        elif isinstance(raw_difficulties, (list, tuple, set)):
            difficulties = list(raw_difficulties)
        else:
            difficulties = [raw_difficulties]
        # Q31 is a completed multi-select symptom checklist.  A non-empty
        # selection that does not include "吞咽困难" therefore answers the
        # derived swallowing question negatively, while null/[] remains
        # unknown.  Keep the original Q31 array untouched so only the
        # derived field becomes negative; selecting "无" still retains its
        # explicit_none state in the normalization metadata below.
        if not difficulties:
            value["swallowing"] = None
        elif "吞咽困难" in difficulties:
            value["swallowing"] = "吞咽困难"
        else:
            value["swallowing"] = "无"
    if not _filled(value.get("spo2_percent")):
        walk = value.get("q27_walkTest") or {}
        vitals = value.get("q44_vitals") or {}
        value["spo2_percent"] = (walk.get("spo2") if isinstance(walk, dict) else None) or (vitals.get("spo2") if isinstance(vitals, dict) else None)
    return value


def _liver_context(payload: dict[str, Any]) -> dict[str, Any]:
    liver = payload.get("q50_liverElastography") or {}
    if liver.get("performed") == "否":
        return {"known": [], "missing": ["肝弹性成像未做"], "explicit_none": ["肝弹性成像"], "uncertain": [], "review": False, "modifier": "未评估"}
    if liver.get("performed") != "是":
        return {"known": [], "missing": ["肝弹性成像"], "explicit_none": [], "uncertain": ["肝脏代谢/纤维化风险"], "review": False, "modifier": "未评估"}
    conclusion = liver.get("conclusion")
    method = liver.get("method") or liver.get("check_method")
    lsm = liver.get("lsm") or liver.get("lsm_kpa")
    review = conclusion in {"显著/进展期纤维化", "提示肝硬化"}
    uncertain = [] if conclusion else ["肝脏代谢/纤维化风险"]
    if lsm is not None and not method and not conclusion:
        uncertain.append("LSM缺少检查方法/报告结论")
    modifier = conclusion or ("已检查但报告结论缺失" if not conclusion else conclusion)
    return {"known": ["肝弹性成像已做"], "missing": ([] if conclusion else ["肝弹性报告结论"]), "explicit_none": [], "uncertain": uncertain, "review": review, "modifier": modifier, "method": method, "lsm": lsm}


def assess_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Deterministic V1 gate; model calls must never bypass this gate."""
    payload = _normalise_payload(payload)
    liver = _liver_context(payload)
    normalized = {key: normalize_selection(value) for key, value in payload.items() if isinstance(value, (list, tuple, str))}
    explicit_none = [key for key, meta in normalized.items() if meta["state"] == "explicit_none"]
    required = {
        "sex": "性别",
        "height_cm": "身高",
        "weight_kg": "体重",
        "food_allergy": "食物过敏/禁忌",
        "swallowing": "吞咽困难",
    }
    missing = [label for key, label in required.items() if not _filled(payload.get(key))]
    contextual = {
        "recent_weight_intake": "近期体重与摄入变化",
        "surgery_window_days": "预计手术时间",
        "six_minute_walk_m": "6分钟步行距离",
        "spo2_percent": "血氧",
    }
    missing_context = [label for key, label in contextual.items() if not _filled(payload.get(key))]
    measured = sum(_filled(payload.get(k)) for k in {**required, **contextual})
    score = round(measured / (len(required) + len(contextual)) * 100)
    if len(missing) >= 2:
        tier, tier_label = 1, "一级｜关键资料不足"
    elif score < 70:
        tier, tier_label = 2, "二级｜可生成保守草稿"
    else:
        tier, tier_label = 3, "三级｜可生成个体化草稿"

    # "无" is an explicit none selection, not an active symptom.  Keep it
    # distinct from missing/null and do not downgrade safety merely because it
    # is present in a multi-select answer.
    symptoms = {item for item in (payload.get("respiratory_symptoms") or []) if item not in {"无", ""}}
    walk_text = str(payload.get("q27_walkTest") or payload.get("six_minute_walk_m") or "")
    _sp = __import__("re").findall(r"SpO₂\s*[=:：]?\s*([0-9.]+(?:\s*[–-]\s*[0-9.]+)?)", walk_text)
    spo2_values = [float(part) for raw in _sp for part in __import__("re").split(r"\s*[–-]\s*", raw)]
    low_spo2 = any(x < 92 for x in spo2_values)
    if symptoms.intersection({"咯血", "明显呼吸困难", "晕厥", "意识异常", "明显胸痛", "胸痛"}) or low_spo2:
        safety, safety_text = "red", "红色｜暂停相关计划并立即转医护"
    elif symptoms or payload.get("swallowing") == "不确定，需要医护评估" or liver["review"]:
        safety, safety_text = "yellow", "黄色｜异常关注，及时转医护"
    else:
        safety, safety_text = "green", "绿色｜正常居家管理"

    height = float(payload["height_cm"]) if _filled(payload.get("height_cm")) else None
    weight = float(payload["weight_kg"]) if _filled(payload.get("weight_kg")) else None
    bmi = round(weight / ((height / 100) ** 2), 1) if height and weight else None
    if bmi is not None and bmi < 18.5:
        phenotype = "D｜消瘦/营养风险型"
    elif bmi is not None and bmi >= 28:
        phenotype = "B｜肥胖/代谢风险型"
    else:
        phenotype = "A｜超重/高体脂型"
    # V2 phenotype/safety enrichment is additive and keeps the legacy fields
    # readable for existing API clients.
    q56 = parse_q56(payload.get("q56_goal", payload.get("Q56")))
    # All callers (persistence, API and plan generation) use this one
    # calculation entry point; no endpoint computes A-F independently.
    phenotype_code, phenotype_modifiers = calculate_phenotype(payload)
    v4_phenotype_contract = derive_v4_phenotype(payload)
    safety_contract = apply_v4_safety_contract_floor(
        existing_safety_level=safety,
        existing_reason_codes=[],
        primary_nutrition_phenotype=v4_phenotype_contract["primary_nutrition_phenotype"],
        complexity_overlay=v4_phenotype_contract["complexity_overlay"],
    )
    safety = safety_contract["safety_level"]
    safety_text = {
        "red": "红色｜暂停相关计划并立即转医护",
        "yellow": "黄色｜异常关注，及时转医护",
        "green": "绿色｜正常居家管理",
    }[safety]
    return {
        "tier": tier,
        "tier_label": tier_label,
        "score": score,
        "missing": missing + missing_context,
        "safety": safety,
        "safety_label": safety_text,
        "safety_reason_codes": safety_contract["safety_reason_codes"],
        "safety_floor_applied": safety_contract["safety_floor_applied"],
        "safety_floor_sources": safety_contract["safety_floor_sources"],
        "phenotype": {"A": "A｜超重/高体脂型", "B": "B｜肥胖/代谢风险型", "C": "C｜高体脂伴肌少风险型", "D": "D｜消瘦/营养风险型", "E": "E｜非意愿下降/摄入不足型", "F": "F｜复杂共病/执行障碍型"}.get(phenotype_code, phenotype),
        "phenotype_code": phenotype_code,
        "phenotype_modifiers": phenotype_modifiers,
        "v4_phenotype_contract": v4_phenotype_contract,
        "primary_nutrition_phenotype": v4_phenotype_contract["primary_nutrition_phenotype"],
        "complexity_overlay": v4_phenotype_contract["complexity_overlay"],
        "display_phenotype": v4_phenotype_contract["display_phenotype"],
        "liver": liver,
        "q56_goal": q56,
        "q56_optional_not_set": not q56.get("has_clinician_goal", False),
        "bmi": bmi,
        "liver_modifier": liver["modifier"],
        "liver_missing": liver["missing"],
        "liver_uncertain": liver["uncertain"],
        "choice_normalization": normalized,
        **structured_missing_context(
            known_data=[key for key in ("sex", "height_cm", "weight_kg", "food_allergy", "swallowing") if _filled(payload.get(key))],
            missing_data=missing + missing_context + liver["missing"],
            explicit_none=explicit_none + liver["explicit_none"],
            uncertain_items=liver["uncertain"] + [key for key, meta in normalized.items() if meta["state"] == "uncertain"],
            need_clinician_review=liver["review"],
        ),
    }


def _meal_placeholder(label: str) -> dict[str, Any]:
    """A deliberate empty meal slot: never invent a recipe or dose."""
    return {
        "meal_type": label, "dish_name": None, "ingredients": None,
        "amount": None, "cooking_method": None, "brief_instructions": None,
        "estimated_energy": None, "estimated_protein": None,
        "estimated_carbohydrate": None, "estimated_fat": None,
        "replacement_options": None, "precautions": None,
        "mdt_confirmed": False, "status": "待医护补充餐次/份量",
    }


def _structured_contract(assessment: dict[str, Any], payload: dict[str, Any], *, kind: str, title: str, goal: str,
                         diet_text: str, exercise_text: str, monitor_text: str) -> dict[str, Any]:
    liver_review = bool(assessment.get("need_clinician_review"))
    window = payload.get("q6_surgeryWindow")
    diet_pattern = payload.get("q34_dietPattern") or []
    meal_frequency = "三餐" if "三餐规律" in diet_pattern else None
    # These are structured placeholders, not clinical prescriptions.  They
    # intentionally carry null doses until a clinician publishes confirmed data.
    pulmonary = []
    if assessment.get("safety") != "red":
        pulmonary = [
            {"action_id": "P01", "action_name": "缩唇呼吸", "purpose": None, "steps": None,
             "duration": None, "repetitions": None, "sets": None, "daily_frequency": None,
             "precautions": "按医护指导；出现不适停止", "stop_conditions": None,
             "alternative_action": None, "mdt_confirmed": False, "status": "待医护确认剂量"},
            {"action_id": "P02", "action_name": "腹式呼吸", "purpose": None, "steps": None,
             "duration": None, "repetitions": None, "sets": None, "daily_frequency": None,
             "precautions": "按医护指导；出现不适停止", "stop_conditions": None,
             "alternative_action": None, "mdt_confirmed": False, "status": "待医护确认剂量"},
        ]
    exercise = [{"exercise_id": None, "exercise_name": "运动计划（待医护从术前动作库选择）",
                 "category": "术前功能活动", "purpose": None, "preparation_position": None,
                 "steps": None, "duration": None, "repetitions": None, "sets": None,
                 "intensity": None, "rest": None, "frequency": None, "precautions": "出现不适立即停止并联系医护",
                 "stop_conditions": None, "alternative_exercise": None, "mdt_confirmed": False,
                 "status": "待医护确认"}] if assessment.get("safety") != "red" else []
    pending = ["饮食餐次、份量及营养目标待医护确认", "运动动作与剂量待医护确认"]
    if pulmonary:
        pending.append("肺预康复动作剂量待医护确认")
    if liver_review:
        pending.append("肝弹性报告需专科/MDT复核")
    contract = {
        "contract_version": PLAN_CONTENT_CONTRACT_VERSION,
        "management_period": {"stage": "术前", "surgery_window": window, "mdt_confirmed": False},
        "stage_goals": {
            "overall_goal": goal, "weight_goal": None, "body_fat_goal": None,
            "waist_goal": None, "muscle_goal": "优先保肌，具体目标待医护确认",
            "functional_goal": None, "metabolic_goals": None,
            "surgery_preparation_goal": "围术期安全准备，具体目标待医护确认",
        },
        "diet_plan": {
            "daily_energy_target": None, "protein_target": None,
            "carbohydrate_target": None, "fat_target": None,
            "meal_frequency": meal_frequency,
            "breakfast": _meal_placeholder("早餐"), "lunch": _meal_placeholder("午餐"),
            "snack": _meal_placeholder("加餐"), "dinner": _meal_placeholder("晚餐"),
            "mdt_confirmed": False, "status": "待医护补充结构化餐次",
        },
        "exercise_plan": exercise,
        "pulmonary_prehab_plan": pulmonary,
        "monitoring_plan": {"items": ["体重", "体脂率", "腰围", "每日执行记录"],
                             "frequency": None, "thresholds": None, "instructions": monitor_text,
                             "mdt_confirmed": False},
        "safety_rules": {"safety_level": assessment.get("safety"), "safety_label": assessment.get("safety_label"),
                          "precautions": "不自动改药、停药或调整治疗；任务剂量以医护发布内容为准",
                          "stop_conditions": None, "mdt_confirmed": False},
        "clinician_notes": {"review_required": True, "note": "规则草稿需医护审核后发布。",
                             "mdt_confirmed": False},
        "missing_data": assessment.get("missing_data", assessment.get("missing", [])),
        "mdt_pending_items": pending,
    }
    # Keep legacy aliases so existing screens and old versions remain readable.
    contract.update({"kind": kind, "title": title, "goal": goal, "diet": diet_text,
                     "exercise": exercise_text, "monitor": monitor_text,
                     "missing_data": assessment.get("missing_data", assessment.get("missing", [])),
                     "known_data": assessment.get("known_data", []),
                     "explicit_none": assessment.get("explicit_none", []),
                     "uncertain_items": assessment.get("uncertain_items", []),
                     "need_clinician_review": assessment.get("need_clinician_review", False)})
    if liver_review:
        contract["liver_safety_note"] = "肝弹性报告提示需专科/MDT复核；降低快速减重优先级，不自动低蛋白或强化运动。"
    return contract


def generate_plan_draft(
    patient: dict[str, Any],
    payload: dict[str, Any],
    assessment: dict[str, Any],
    *,
    active_configs: dict[str, Any] | None = None,
    pulmonary_clinician_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # V2.1 structured contract is the canonical output for both rule and AI
    # generators. Legacy text aliases are retained by build_v2_plan callers.
    draft = build_v2_plan(
        payload,
        assessment,
        active_configs=active_configs,
        pulmonary_clinician_inputs=pulmonary_clinician_inputs,
    )
    draft.update({
        "kind": "safety_notice" if assessment.get("safety") == "red" else ("limited" if assessment.get("tier") == 1 else "draft"),
        "title": "暂不生成完整方案" if assessment.get("safety") == "red" else "V2.1结构化方案草稿",
        "goal": draft.get("stage_goals", {}).get("overall_goal"),
        "diet": "已生成结构化饮食模块，待医护审核",
        "exercise": "已生成结构化运动模块，待医护审核",
        "monitor": draft.get("monitoring_plan", {}).get("instructions"),
        "generation_source": "RULE_BASED",
    })
    return draft
