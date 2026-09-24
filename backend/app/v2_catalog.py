"""Versioned V2 knowledge/config catalog.

Entries are intentionally seeded as DRAFT/PENDING.  A clinician/MDT must
promote them to ACTIVE before a production generator can use numeric values.
The importer is idempotent and never changes existing rows.
"""
from __future__ import annotations

from typing import Any
try:  # keep catalogue introspection usable in lightweight test environments
    from sqlalchemy import select
    from .db import KnowledgeItemRow, MdtConfigRow
except ModuleNotFoundError:  # pragma: no cover - runtime dependency is installed by API image
    select = None
    KnowledgeItemRow = MdtConfigRow = None
from .v2_engine import FOODS, EXERCISES, PULMONARY
from .v2_knowledge import structured_catalog

V2_CONFIGS = [
    ("V2-REE-SOURCE-PRIORITY", "ENERGY", "V2 REE来源优先级", {"priority": ["measured_REE", "approved_formula", "bia_bmr_auxiliary", "kcal_per_kg_reference"]}),
    ("V2-REE-FORMULA", "ENERGY", "V2 REE预测公式（待MDT确认）", {"ree_formula_id": None, "ree_formula_version": None}),
    ("V2-PAL-RULE", "ENERGY", "V2 PAL活动系数规则（待MDT确认）", {"default": None}),
    ("V2-AF-ENERGY-MODES", "NUTRITION", "V2 A-F能量模式候选配置", {"status": "CANDIDATE_TEST_ONLY", "modes": {"A": "STANDARD_FAT_LOSS", "B": "STANDARD_FAT_LOSS", "C": "MUSCLE_PRESERVATION", "D": "NUTRITION_RECOVERY", "E": "STOP_WEIGHT_LOSS", "F": "SAFE_EXECUTABLE"}}),
    ("V2-FOOD-COMPONENTS", "FOOD", "V2菜品与食谱组件库调用规则", {"active_only": True, "require_weight_basis": True}),
    ("V2-EXERCISE-ACTIONS", "EXERCISE", "V2术前运动动作库调用规则", {"active_only": True, "ids": ["A01", "A02", "R04"]}),
    ("V2-PULMONARY-ACTIONS", "PULMONARY", "V2肺预康复P01-P06调用规则", {"active_only": True, "ids": ["P01", "P02", "P03", "P04", "P05", "P06"]}),
    ("V2-WEEKLY-REVIEW", "ADAPTIVE", "V2七日复评决策顺序", {"decisions": ["MAINTAIN", "BARRIER_FIRST", "DATA_INSUFFICIENT", "PRESERVE_MUSCLE", "NUTRITION_RECOVERY", "INTENSIFY_CANDIDATE", "DEINTENSIFY", "SAFETY_REVIEW"]}),
]

V2_KNOWLEDGE = [
    ("V2-FOOD-C002", "FOOD", "糙米饭基础份", {"component_id": "C002", "source": "V2 food component", "mdt_confirmed": False}),
    ("V2-FOOD-P001", "FOOD", "清蒸鲈鱼", {"component_id": "P001", "source": "V2 food component", "mdt_confirmed": False}),
    ("V2-FOOD-V001", "FOOD", "清炒西兰花", {"component_id": "V001", "source": "V2 food component", "mdt_confirmed": False}),
    ("V2-FOOD-S001", "FOOD", "无糖酸奶", {"component_id": "S001", "source": "V2 food component", "mdt_confirmed": False}),
    ("V2-EX-A01", "EXERCISE", "缓慢步行", {"exercise_id": "A01", "mdt_confirmed": False}),
    ("V2-EX-A02", "EXERCISE", "快步走", {"exercise_id": "A02", "mdt_confirmed": False}),
    ("V2-EX-R04", "EXERCISE", "坐姿腿屈伸", {"exercise_id": "R04", "mdt_confirmed": False}),
    ("V2-PR-P01", "PULMONARY", "缩唇呼吸", {"pulmonary_id": "P01", "mdt_confirmed": False}),
    ("V2-PR-P02", "PULMONARY", "腹式呼吸", {"pulmonary_id": "P02", "mdt_confirmed": False}),
    ("V2-PR-P03", "PULMONARY", "胸廓扩张训练", {"pulmonary_id": "P03", "mdt_confirmed": False}),
    ("V2-TEMPLATE-W1", "TEMPLATE", "V2.1术前第一周方案模板", {"contract_version": "2.1", "status": "CANDIDATE_TEST_ONLY"}),
    ("V2-SAFETY-VALIDATOR", "TEMPLATE", "V2安全规则与禁忌替代引擎", {"requires_clinician_review": True, "red_blocks_publish": True}),
    ("V2-ENERGY-RULE", "TEMPLATE", "V2 REE/TEE与周动态规则", {"formula_status": "PENDING_MDT"}),
]

# Expand the seed into one retrievable item per reviewed component/action.
# Existing rows are left untouched by the idempotent importer; new entries are
# DRAFT until MDT approval.  This keeps historical V1 rows available.
_parsed = structured_catalog()
_food_source = _parsed["FOOD"] or FOODS
_exercise_source = _parsed["EXERCISE"] or list(EXERCISES.values())
_pulmonary_source = _parsed["PULMONARY"] or list(PULMONARY.values())
_food_items = [(f"V1.7-FOOD-{f['component_id']}", "FOOD", f["name"], {**f, "domain": "FOOD"}) for f in _food_source]
_exercise_items = [(f"V2-EX-{e['exercise_id']}", "EXERCISE", e["name"], {**e, "domain": "EXERCISE", "status": "DRAFT", "source_version": "V2.0"}) for e in _exercise_source]
_pulmonary_items = [(f"V2-PR-{p['pulmonary_id']}", "PULMONARY", p["name"], {**p, "domain": "PULMONARY", "status": "DRAFT", "source_version": "V2.0"}) for p in _pulmonary_source]
V2_KNOWLEDGE = list({item[0]: item for item in [*V2_KNOWLEDGE, *_food_items, *_exercise_items, *_pulmonary_items]}.values())

def seed_v2_catalog(session: Any) -> dict[str, int]:
    if KnowledgeItemRow is None or MdtConfigRow is None:
        raise RuntimeError("seed_v2_catalog requires backend database dependencies")
    configs = knowledge = 0
    for config_id, domain, name, value in V2_CONFIGS:
        if session.get(MdtConfigRow, config_id) is None:
            session.add(MdtConfigRow(config_id=config_id, domain=domain, display_name=name, value_json=value, status="PENDING", source_version="V2.0", responsible_mdt="MDT待确认"))
            configs += 1
    for item_id, item_type, name, content in V2_KNOWLEDGE:
        if session.scalars(select(KnowledgeItemRow).where(KnowledgeItemRow.item_id == item_id)).first() is None:
            session.add(KnowledgeItemRow(item_id=item_id, item_type=item_type, display_name=name, content_json=content, status="DRAFT", source_document="docs/v2_upgrade_20260912", source_version="V2.0"))
            knowledge += 1
    return {"configs_added": configs, "knowledge_added": knowledge}
