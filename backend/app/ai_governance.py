"""Authoritative, versioned control plane for AI plan generation.

Clinical values are deliberately absent from this module.  They belong in
``mdt_config.value_json`` only after the responsible MDT has approved them.
This keeps prompts as an orchestration layer rather than a hidden source of
medical thresholds.
"""
from __future__ import annotations

from typing import Any


AUTHORITY_ORDER = ("safety_rule", "mdt_config", "knowledge_item", "plan_template", "prompt")

PENDING_CONFIGS = (
    ("NUT-CFG-001", "NUTRITION", "医院批准的能量估算方法", "营养科"),
    ("NUT-CFG-002", "NUTRITION", "体重基准和调整体重算法", "营养科+内分泌科"),
    ("NUT-CFG-003", "NUTRITION", "A/B型术前能量缺口上限", "营养科+胸外科"),
    ("NUT-CFG-004", "NUTRITION", "C型能量维持或轻度负平衡规则", "营养科+康复医学科"),
    ("NUT-CFG-005", "NUTRITION", "D/E型能量恢复规则", "营养科"),
    ("NUT-CFG-006", "NUTRITION", "蛋白目标与体重基准", "营养科+胸外科"),
    ("NUT-CFG-007", "NUTRITION", "CKD/肾功能风险的高蛋白限制", "肾内科+营养科"),
    ("NUT-CFG-008", "NUTRITION", "加餐比例与餐次分配", "营养科"),
    ("NUT-CFG-009", "NUTRITION", "按手术窗口的能量策略", "胸外科+营养科"),
    ("NUT-CFG-010", "NUTRITION", "ONS启用条件、品类和审核路径", "营养科"),
    ("FOOD-CFG-001", "FOOD", "三餐及加餐默认能量分配", "营养科"),
    ("FOOD-CFG-002", "FOOD", "同类替换容差", "营养科"),
    ("FOOD-CFG-003", "FOOD", "默认一份食物克重", "营养科"),
    ("FOOD-CFG-004", "FOOD", "A-F组件选择权重", "营养科+产品"),
    ("FOOD-CFG-005", "FOOD", "糖代谢异常主食调整", "内分泌科+营养科"),
    ("FOOD-CFG-006", "FOOD", "高血压钠目标及低钠盐条件", "心血管科+营养科"),
    ("FOOD-CFG-007", "FOOD", "高尿酸/痛风食物筛选", "内分泌科+风湿科+营养科"),
    ("FOOD-CFG-008", "FOOD", "肾功能异常饮食触发条件", "肾内科+营养科"),
    ("FOOD-CFG-009", "FOOD", "短手术窗口生冷食物限制", "胸外科+营养科"),
    ("FOOD-CFG-010", "FOOD", "营养数据库来源、版本和重算服务", "营养科+工程"),
    ("EX-CFG-001", "EXERCISE", "强度与Borg/RPE/生理指标映射", "康复医学科+胸外科"),
    ("EX-CFG-002", "EXERCISE", "运动停止和转人工阈值", "康复+心血管+内分泌"),
    ("EX-CFG-003", "EXERCISE", "有氧频率及进阶上限", "康复医学科"),
    ("EX-CFG-004", "EXERCISE", "抗阻剂量、阻力与动作质量", "康复医学科"),
    ("EX-CFG-005", "EXERCISE", "关节/腰背限制替代矩阵", "康复医学科+骨关节科"),
    ("EX-CFG-006", "EXERCISE", "6MWT缺失时保守起始规则", "康复医学科+胸外科"),
    ("EX-CFG-007", "EXERCISE", "手术一周内允许动作", "胸外科+康复医学科"),
    ("EX-CFG-008", "EXERCISE", "动作视频版本", "康复医学科+护理+产品"),
    ("PR-CFG-001", "PULMONARY", "肺预康复基础池与条件调用", "康复医学科+胸外科"),
    ("PR-CFG-002", "PULMONARY", "P01-P05剂量和频率", "康复医学科"),
    ("PR-CFG-003", "PULMONARY", "P03动作定义和标准名称", "康复医学科+护理"),
    ("PR-CFG-004", "PULMONARY", "呼吸训练停止和升级阈值", "康复医学科+胸外科"),
    ("PR-CFG-005", "PULMONARY", "P05学习与排痰频率", "康复医学科+胸外科"),
    ("PR-CFG-006", "PULMONARY", "P06 OPEP处方与设备条件", "呼吸治疗+康复+胸外科"),
    ("PR-CFG-007", "PULMONARY", "肺预康复视频版本", "康复医学科+护理+产品"),
    ("PR-CFG-008", "PULMONARY", "IMT/激励性肺量计启用规则", "MDT"),
)

ADAPTIVE_RULES = (
    ("ADJ-001", "连续3天摄入不足或食欲下降", "YELLOW", "冻结能量限制和运动进阶", "营养科", ["diet_plan"], "生成营养恢复草稿"),
    ("ADJ-002", "近7天任务完成率低于医护配置下限", "REVIEW", "不强化处方，先记录执行障碍", "护理+责任医护", ["reminder", "task_complexity"], "生成简化方案草稿"),
    ("ADJ-003", "近7天肌肉或功能趋势下降", "YELLOW", "冻结减能量和有氧进阶", "营养科+康复医学科", ["diet_plan", "exercise_plan"], "生成保肌草稿"),
    ("ADJ-004", "新发或加重症状", "YELLOW", "冻结相关模块的自动调整", "责任医护", [], "仅生成转人工摘要"),
    ("ADJ-005", "红色安全事件", "RED", "暂停相关任务，禁止方案进阶", "责任医护", [], "不得自动生成新处方"),
    ("ADJ-006", "手术日期提前或进入更短窗口", "REVIEW", "冻结激进减重和陌生高负荷训练", "胸外科+营养科+康复医学科", ["schedule", "task_complexity"], "生成术前保守草稿"),
    ("ADJ-007", "连续7天数据不足", "REVIEW", "不判定无效，不改变剂量", "护理+责任医护", ["reminder", "recording_method"], "生成补数提醒草稿"),
)


def pending_config_ids(configs: list[dict[str, Any]]) -> list[str]:
    return [item["config_id"] for item in configs if item.get("status") != "ACTIVE"]


def validate_draft(content: dict[str, Any], configs: list[dict[str, Any]]) -> list[str]:
    """Return blocking validation messages; no model output is trusted alone."""
    errors: list[str] = []
    if (content or {}).get("clinician_notes", {}).get("review_required") is not True:
        errors.append("方案必须要求医护审核")
    if (content or {}).get("generation_source") == "PROMPT_ONLY":
        errors.append("提示词不能作为医学参数来源")
    if (content or {}).get("safety_rules", {}).get("safety_level") == "red":
        if (content or {}).get("exercise_plan") or (content or {}).get("pulmonary_prehab_plan"):
            errors.append("红色安全状态不得保留运动或肺预康复任务")
    if (content or {}).get("publication_blocked") is True or (content or {}).get("safety_rules", {}).get("publication_blocked") is True:
        errors.append("方案标记为禁止发布，必须由医护解除阻断后再审核")
    for section in ("diet_plan", "exercise_plan", "pulmonary_prehab_plan"):
        value = (content or {}).get(section)
        values = value if isinstance(value, list) else [value]
        for item in values:
            # V2/V3 baseline values are already adopted by this project. They
            # may still carry candidate provenance for audit, but that
            # provenance must not block a clinician review/publish workflow.
            if isinstance(item, dict) and item.get("mdt_confirmed") is not True and (content or {}).get("rule_authority") != "PROJECT_BASELINE_V2_V3":
                numeric = any(isinstance(item.get(key), (int, float)) for key in ("daily_energy_target_kcal", "daily_energy_target", "protein_target_g", "protein_target", "estimated_energy", "estimated_protein", "estimated_carbohydrate", "estimated_fat", "ingredient_amount", "amount", "duration", "duration_min", "repetitions", "reps", "sets", "daily_frequency"))
                if numeric:
                    errors.append(f"{section} 含未经MDT确认的数值")
    return errors


def build_generation_context(*, configs: list[dict[str, Any]], knowledge: list[dict[str, Any]], rules: list[dict[str, Any]]) -> dict[str, Any]:
    """The only context an AI gateway should receive for clinical values."""
    return {
        "authority_order": AUTHORITY_ORDER,
        "active_mdt_configs": [x for x in configs if x.get("status") == "ACTIVE"],
        "pending_mdt_config_ids": pending_config_ids(configs),
        "approved_knowledge": [x for x in knowledge if x.get("status") == "ACTIVE"],
        "adaptive_rules": rules,
        "prompt_role": "orchestration_only",
        "publish_policy": "AI_GENERATED_PENDING_REVIEW only; clinician review and safety validation required before PUBLISHED",
    }


def evaluate_adjustment(signals: dict[str, Any], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn structured daily/7-day signals into reviewable rule matches.

    Threshold values are intentionally supplied by active MDT configuration,
    never embedded here.  Boolean signals are set by the trend service after
    applying those active values.
    """
    keys = {
        "ADJ-001": "intake_insufficient_3_days",
        "ADJ-002": "completion_below_configured_floor",
        "ADJ-003": "muscle_or_function_declining_7_days",
        "ADJ-004": "new_or_worsening_symptom",
        "ADJ-005": "red_safety_event",
        "ADJ-006": "surgery_window_shortened",
        "ADJ-007": "insufficient_data_7_days",
    }
    active = {x.get("rule_id"): x for x in rules if x.get("status") == "ACTIVE"}
    matches = []
    for rule_id, signal_key in keys.items():
        if signals.get(signal_key) and rule_id in active:
            rule = active[rule_id]
            matches.append({"rule_id": rule_id, "signal": signal_key, "safety_level": rule.get("safety_level"),
                "system_action": rule.get("action"), "reviewer_role": rule.get("reviewer_role"),
                "adjustable_fields": rule.get("adjustable_fields", []), "requires_new_plan_version": rule_id not in {"ADJ-004", "ADJ-005", "ADJ-007"}})
    return matches
