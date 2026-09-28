"""Pre-publication validation for the V2.1 structured plan contract."""
from __future__ import annotations
from typing import Any

REQUIRED = ("management_period", "stage_goals", "diet_plan", "exercise_plan", "pulmonary_prehab_plan", "monitoring_plan", "safety_rules", "missing_data", "mdt_pending_items")

def validate_plan(plan: dict[str, Any], *, mode: str = "production", allowed_exercise_ids: set[str] | None = None, allowed_pulmonary_ids: set[str] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, str] = {}
    for key in REQUIRED:
        checks[f"contract.{key}"] = "PASS" if key in plan and plan[key] is not None else "FAIL"
        if checks[f"contract.{key}"] == "FAIL": errors.append(f"缺少方案字段:{key}")
    diet = plan.get("diet_plan") or {}
    meals = [diet.get(k) for k in ("breakfast", "lunch", "snack", "dinner")]
    main = [m for m in meals if m and m.get("meal_type") in {"breakfast", "lunch", "dinner"}]
    checks["nutrition.main_meal_completeness"] = "PASS" if all(all(m.get(k) not in (None, "") for k in ("ingredient_name", "ingredient_amount", "raw_or_cooked_basis", "cooking_method")) for m in main) else "FAIL"
    if checks["nutrition.main_meal_completeness"] == "FAIL": errors.append("正餐缺少食材/重量/生熟口径/做法")
    checks["nutrition.closure"] = "PASS" if diet.get("nutrition_plan_validation") == "PASS" or (diet.get("daily_energy_total") and diet.get("daily_protein_total")) else "FAIL"
    diet_trace = plan.get("diet_plan_trace") or {}
    replacement_validation = diet_trace.get("replacement_integrity_validation") or {}
    realism_validation = diet_trace.get("meal_realism_validation") or {}
    checks["nutrition.replacement_integrity"] = replacement_validation.get("status", "WARN")
    checks["nutrition.meal_realism"] = realism_validation.get("status", "WARN")
    if checks["nutrition.replacement_integrity"] == "FAIL":
        errors.append("饮食替换完整性未通过")
    if checks["nutrition.meal_realism"] == "FAIL":
        warnings.append("存在餐次执行真实性待复核项")
    exercises = plan.get("exercise_plan") or []
    if allowed_exercise_ids is not None and any(x.get("exercise_id") not in allowed_exercise_ids for x in exercises): errors.append("运动包含非允许动作ID")
    checks["exercise.allowed_ids"] = "PASS" if not errors or not any("运动包含" in e for e in errors) else "FAIL"
    pulmonary = plan.get("pulmonary_prehab_plan") or []
    if allowed_pulmonary_ids is not None and any(x.get("pulmonary_id") not in allowed_pulmonary_ids for x in pulmonary): errors.append("肺康复包含非允许动作ID")
    for item in pulmonary:
        if item.get("pulmonary_id") == "P06" and not (item.get("device_available") and item.get("clinician_ordered")):
            errors.append("P06缺少设备和医护指导/处方")
    checks["pulmonary.gates"] = "PASS" if not any("P06" in e for e in errors) else "FAIL"
    pulmonary_trace = plan.get("pulmonary_rehab_trace")
    if pulmonary_trace is not None:
        trace_validation = pulmonary_trace.get("trace_validation") or {}
        canonical_ids = {
            (action.get("pulmonary_id"), action.get("pulmonary_mode"))
            for day in pulmonary_trace.get("daily_schedule", [])
            for action in day.get("actions", [])
        }
        projected_ids = {(item.get("pulmonary_id"), item.get("pulmonary_mode")) for item in pulmonary}
        canonical_checks = {
            "schema": pulmonary_trace.get("schema_version") == "PULMONARY_TRACE_V4_2",
            "full_root": pulmonary_trace.get("trace_materialization_status") == "FULL" and pulmonary_trace.get("pulmonary_trace_full") is True,
            "trace_validation": trace_validation.get("status") == "PASS",
            "minimum_sufficient_set": bool(pulmonary_trace.get("minimum_sufficient_set")),
            "provenance": bool((pulmonary_trace.get("source_provenance") or {}).get("source_version")) and bool((pulmonary_trace.get("source_provenance") or {}).get("sha256")),
            "patient_projection": projected_ids.issubset(canonical_ids),
        }
        checks["pulmonary.canonical_trace"] = "PASS" if all(canonical_checks.values()) else "FAIL"
        if not all(canonical_checks.values()):
            errors.append("肺康复canonical trace或患者投影未通过")
    else:
        checks["pulmonary.canonical_trace"] = "WARN"
    # Rotation is independent from nutrition closure. Repetition is only
    # tolerated when the catalog explicitly reports that safe alternatives are
    # limited; otherwise it is a validation problem for a seven-day plan.
    weekly = plan.get("weekly_schedule") or []
    weekly_diets = [d.get("diet") or [] for d in weekly if isinstance(d, dict)]
    def _signature(meal: Any) -> str:
        if not isinstance(meal, dict):
            return ""
        components = meal.get("components") or []
        ids = [str(x.get("component_id") or x.get("knowledge_item_id") or x.get("name") or "") for x in components if isinstance(x, dict)]
        return "+".join(ids) or str(meal.get("dish_name") or meal.get("meal_name") or "")
    breakfast_signatures = {_signature(day[0]) for day in weekly_diets if day and isinstance(day[0], dict)}
    consecutive_repeat = any(_signature(weekly_diets[i][0]) and _signature(weekly_diets[i][0]) == _signature(weekly_diets[i - 1][0]) for i in range(1, len(weekly_diets)) if weekly_diets[i] and weekly_diets[i - 1])
    rotation_limited = bool(diet.get("rotation_limited"))
    if consecutive_repeat:
        (warnings if rotation_limited else errors).append("食谱主菜存在连续重复" + ("（知识库候选不足）" if rotation_limited else ""))
    if len(weekly_diets) >= 7 and len(breakfast_signatures) < 3:
        (warnings if rotation_limited else errors).append("早餐7天可行组合少于3种" + ("（知识库候选不足）" if rotation_limited else ""))
    if len(weekly_diets) >= 7 and len(breakfast_signatures) == 1 and not rotation_limited:
        errors.append("可替代菜品充足但7天食谱完全相同")
    checks["nutrition.rotation"] = "WARN" if any("食谱" in x or "早餐7天" in x for x in warnings) else ("FAIL" if any("食谱" in x or "早餐7天" in x or "可替代菜品" in x for x in errors) else "PASS")
    # V3.0 weekly-combination integrity: a valid weekly prescription must
    # include the documented resistance frequency and action count.  This is
    # deliberately structural; clinical dose values remain catalogue/MDT
    # governed and are not invented here.
    combo = plan.get("exercise_weekly_prescription") or {}
    if weekly and plan.get("rule_version") == "V3.0" and plan.get("safety_level") != "red":
        phenotype = str(plan.get("phenotype") or combo.get("phenotype") or "F")
        ranges = {"A": ((2, 3), (4, 6)), "B": ((2, 3), (4, 6)), "C": ((2, 3), (4, 6)), "D": ((2, 3), (3, 5)), "E": ((2, 3), (2, 4)), "F": ((1, 3), (1, 3))}
        res_range = ranges.get(phenotype, ranges["F"])[0]
        action_range = ranges.get(phenotype, ranges["F"])[1]
        resistance_days = [d for d in weekly if d.get("resistance")]
        if not (res_range[0] <= len(resistance_days) <= res_range[1]):
            errors.append("V3抗阻周频率不完整")
        if any(len(d.get("resistance") or []) < action_range[0] or len(d.get("resistance") or []) > action_range[1] for d in resistance_days):
            errors.append("V3单次抗阻动作数量不完整")
        # No consecutive high-load resistance days (the generated schedule
        # uses odd days; retain this guard for edited drafts too).
        days = sorted(int(d.get("day")) for d in resistance_days if d.get("day") is not None)
        if any(b - a == 1 for a, b in zip(days, days[1:])):
            errors.append("V3不应安排连续高负荷抗阻日")
        loads = [int(bool(d.get("aerobic"))) + int(bool(d.get("resistance"))) for d in weekly]
        total_load = sum(loads)
        if total_load and sum(loads[:3]) / total_load > 0.60:
            errors.append("V3周负荷过度集中在前3天")
        checks["exercise.v3_load_balance"] = "FAIL" if any("周负荷" in e for e in errors) else "PASS"
        checks["exercise.v3_weekly_combination"] = "PASS" if not any(e.startswith("V3") for e in errors) else "FAIL"
    else:
        checks["exercise.v3_weekly_combination"] = "PASS"
    blocked = bool(plan.get("publication_blocked") or (plan.get("safety_level") == "red"))
    checks["safety.publish_block"] = "FAIL" if blocked else "PASS"
    if blocked: errors.append("安全状态或目标冲突阻断发布")
    pending = plan.get("mdt_pending_items") or []
    if mode == "production" and pending:
        warnings.append("存在待MDT确认参数，不能作为正式处方")
        errors.append("生产模式存在PENDING/DRAFT医学参数")
    checks["governance.pending"] = "PASS" if mode == "TEST_ONLY" or not pending else "FAIL"
    status = "FAIL" if errors else "PASS"
    return {"status": status, "errors": errors, "warnings": warnings, "checks": checks, "mode": mode}
