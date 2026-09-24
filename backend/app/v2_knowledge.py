"""Structured V2 knowledge catalogue loader.

The reviewed DOCX files are the source of truth.  This module parses their
tables into stable, item-level records (rather than storing a document
pointer).  Entries remain DRAFT until an MDT explicitly promotes them.
"""
from __future__ import annotations

import re
import zipfile
import json
import posixpath
from copy import deepcopy
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "docs" / "v2_upgrade_20260912" / "rules"
OFFICIAL_FOOD_WORKBOOK = ROOT / "outputs" / "p3b_food_mdt_review" / "FOOD知识库_V1.7_MDT确认正式版.xlsx"
OFFICIAL_FOOD_SHEET = "FOOD_OFFICIAL_V1.7"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    """Read a scalar XLSX cell without requiring an optional spreadsheet package."""
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//a:t", XLSX_NS))
    value = cell.find("a:v", XLSX_NS)
    if value is None:
        return ""
    raw = value.text or ""
    if cell_type == "s":
        return shared_strings[int(raw)] if raw else ""
    if cell_type == "b":
        return raw == "1"
    return raw


def _xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for char in letters.upper():
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _read_xlsx_sheet(path: Path, sheet_name: str) -> list[list[Any]]:
    """Return rows from a named worksheet using the XLSX XML primitives."""
    with zipfile.ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", XLSX_NS):
                shared_strings.append("".join(t.text or "" for t in item.findall(".//a:t", XLSX_NS)))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships
        }
        target = None
        for sheet in workbook.findall("a:sheets/a:sheet", XLSX_NS):
            if sheet.attrib.get("name") != sheet_name:
                continue
            rel_id = sheet.attrib.get("{" + XLSX_NS["r"] + "}id")
            target = relmap.get(rel_id)
            break
        if not target:
            raise ValueError(f"V1.7 FOOD workbook缺少工作表: {sheet_name}")
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = posixpath.join("xl", target)
        worksheet = ET.fromstring(archive.read(target))
        rows: list[list[Any]] = []
        for row in worksheet.findall(".//a:sheetData/a:row", XLSX_NS):
            cells: dict[int, Any] = {}
            for cell in row.findall("a:c", XLSX_NS):
                cells[_xlsx_column_index(cell.attrib.get("r", "A1"))] = _xlsx_cell_value(cell, shared_strings)
            if not cells:
                rows.append([])
                continue
            width = max(cells) + 1
            rows.append([cells.get(i, "") for i in range(width)])
        return rows


def _clean_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def _json_cell(value: Any, default: Any) -> Any:
    value = _clean_cell(value)
    if value is None:
        return deepcopy(default)
    if isinstance(value, (list, dict)):
        return deepcopy(value)
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return deepcopy(default)


def _float_cell(value: Any) -> float | None:
    value = _clean_cell(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _basis_code(value: Any) -> str:
    """Normalize the MDT-confirmed Chinese weight basis to the contract code."""
    text = str(_clean_cell(value) or "")
    if "生重" in text or "干重" in text or "原料重" in text:
        return "raw_weight"
    if "熟重" in text or "熟制" in text:
        return "cooked_weight"
    if "可食部" in text:
        return "edible_portion"
    if "包装净含量" in text or "净含量" in text:
        return "package_net_weight"
    if "标准份" in text or "份" in text:
        return "serving"
    if "混合菜总重" in text:
        return "mixed"
    return "unknown"


def _infer_cooking_method(name: str, category: str) -> str:
    """Keep the legacy display hint when V1.7 has no dedicated method column."""
    if "蒸" in name:
        return "清蒸"
    if "炖" in name:
        return "炖"
    if "煮" in name or "粥" in name:
        return "煮"
    if "炒" in name:
        return "少油炒"
    if category == "snack":
        return "即食"
    return "按组件说明执行"


def _official_food_row(row: dict[str, Any]) -> dict[str, Any]:
    """Adapt one validated FOOD_OFFICIAL_V1.7 row to the runtime contract."""
    component_id = str(row.get("component_id") or "").strip()
    category = str(row.get("category") or "").strip()
    name = str(row.get("component_name") or row.get("original_component_name") or "").strip()
    ingredient_rows = _json_cell(row.get("ingredients"), [])
    ingredient_amounts = _json_cell(row.get("ingredient_amounts"), ingredient_rows)
    # V1.7 keeps a human-readable ingredients column and the structured
    # ingredient_amounts JSON column.  The runtime contract needs the latter
    # whenever the former is plain source text; source_text retains both for
    # traceability.
    if not isinstance(ingredient_rows, list) or not ingredient_rows:
        ingredient_rows = deepcopy(ingredient_amounts) if isinstance(ingredient_amounts, list) else []
    base_portion = _json_cell(row.get("base_portion"), ingredient_amounts)
    portion_options = _json_cell(row.get("portion_options"), [])
    if not isinstance(portion_options, list):
        portion_options = []
    replacement_ids = _json_cell(row.get("replacement_ids"), [])
    use_tags = _json_cell(row.get("use_tags"), [])
    meal_type = _json_cell(row.get("meal_type"), ["breakfast", "lunch", "snack", "dinner"])
    if not isinstance(replacement_ids, list): replacement_ids = []
    if not isinstance(use_tags, list): use_tags = []
    if not isinstance(meal_type, list): meal_type = [str(meal_type)] if meal_type else ["breakfast", "lunch", "snack", "dinner"]
    mdt_status = str(_clean_cell(row.get("MDT_overall_status")) or "")
    confirmed = "确认" in mdt_status and "停用" not in mdt_status
    basis = _basis_code(row.get("weight_basis"))
    # V1.7 explicitly resolves only these two previously unknown mappings.
    subcategory = str(_clean_cell(row.get("subcategory")) or "unknown")
    if component_id == "C009": subcategory = "whole_grain"
    if component_id == "C010": subcategory = "mixed_grain"
    return {
        "item_id": f"V1.7-FOOD-{component_id}", "component_id": component_id, "domain": "FOOD",
        "name": name, "category": category, "subcategory": subcategory,
        "meal_type": meal_type, "ingredients": ingredient_rows, "ingredient_amounts": ingredient_amounts,
        "unit": str(_clean_cell(row.get("portion_unit")) or "x_base_portion"),
        "base_portion": base_portion, "base_portion_status": "complete" if base_portion else "incomplete",
        "raw_or_cooked_basis": basis, "weight_basis": basis, "source_basis_text": _clean_cell(row.get("source_basis_text")),
        "source_text": {key: _clean_cell(row.get(key)) for key in ("component_id", "component_name", "ingredients", "ingredient_amounts", "source_basis_text", "base_portion", "weight_basis", "nutrition_validation_note", "source_document")},
        "source_table": _clean_cell(row.get("source_table")), "cooking_method": _infer_cooking_method(name, category),
        "energy_kcal": _float_cell(row.get("energy_kcal")), "protein_g": _float_cell(row.get("protein_g")),
        "carbohydrate_g": _float_cell(row.get("carbohydrate_g")), "fat_g": _float_cell(row.get("fat_g")),
        "portion_min": _float_cell(row.get("portion_min")), "portion_max": _float_cell(row.get("portion_max")),
        "portion_step": _float_cell(row.get("portion_step")), "portion_options": [float(x) for x in portion_options if _float_cell(x) is not None],
        "portion_multiplier_options": [float(x) for x in portion_options if _float_cell(x) is not None],
        "portion_boundary_status": _clean_cell(row.get("portion_boundary_status")), "portion_boundary_source": _clean_cell(row.get("portion_boundary_source")),
        "use_tags": sorted(set(use_tags)) or _food_use_tags(category, subcategory, name, str(row.get("ingredients") or ""), _float_cell(row.get("protein_g")), _float_cell(row.get("energy_kcal"))),
        "phenotype_tags": _json_cell(row.get("phenotype_tags"), []), "goal_tags": _json_cell(row.get("goal_tags"), []),
        "disease_tags": _json_cell(row.get("disease_tags"), []), "liver_modifier_tags": _json_cell(row.get("liver_modifier_tags"), []),
        "allergy_tags": _json_cell(row.get("allergy_tags"), []), "intolerance_tags": _json_cell(row.get("intolerance_tags"), []),
        "contraindications": _clean_cell(row.get("contraindications")), "replacement_ids": replacement_ids,
        "replacement_group": _clean_cell(row.get("replacement_group")) or category,
        "D_type_suitability": _clean_cell(row.get("D_type_suitability")), "E_type_suitability": _clean_cell(row.get("E_type_suitability")),
        "glucose_control": _clean_cell(row.get("glucose_control")), "dyslipidemia": _clean_cell(row.get("dyslipidemia")),
        "hyperuricemia": _clean_cell(row.get("hyperuricemia")), "hypertension": _clean_cell(row.get("hypertension")), "fatty_liver": _clean_cell(row.get("fatty_liver")),
        "disease_note": _clean_cell(row.get("disease_note")), "nutrition_source_status": _clean_cell(row.get("nutrition_source_status")),
        # The Excel workbook is the runtime authority.  The original Word
        # filename remains in source_text for provenance, never as a loader.
        "source_document": OFFICIAL_FOOD_WORKBOOK.name,
        "source_document_original": _clean_cell(row.get("source_document")),
        "source_version": "V1.7", "review_status": "CONFIRMED" if confirmed else "PENDING",
        "status": "ACTIVE" if confirmed else "DRAFT", "mdt_confirmed": confirmed,
    }


def _load_official_food_components(path: Path = OFFICIAL_FOOD_WORKBOOK) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"运行时FOOD正式文件不存在: {path}")
    rows = _read_xlsx_sheet(path, OFFICIAL_FOOD_SHEET)
    if not rows:
        raise ValueError("V1.7 FOOD工作表为空")
    headers = [str(value).strip() for value in rows[0]]
    if "component_id" not in headers:
        raise ValueError("V1.7 FOOD工作表缺少component_id列")
    records = [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in rows[1:] if any(_clean_cell(x) is not None for x in row)]
    ids = [str(record.get("component_id") or "").strip() for record in records]
    if len(records) != 49 or len(set(ids)) != 49 or any(not value for value in ids):
        raise ValueError(f"V1.7 FOOD完整性失败: rows={len(records)}, unique_ids={len(set(ids))}, empty_ids={sum(not x for x in ids)}")
    required = ("base_portion", "weight_basis", "portion_min", "portion_max", "portion_step", "energy_kcal", "protein_g", "carbohydrate_g", "fat_g")
    missing = {field: [record.get("component_id") for record in records if _clean_cell(record.get(field)) is None] for field in required}
    if any(missing.values()):
        raise ValueError(f"V1.7 FOOD关键字段缺失: {missing}")
    for record in records:
        minimum, maximum, step = (_float_cell(record.get(key)) for key in ("portion_min", "portion_max", "portion_step"))
        if minimum is None or maximum is None or step is None or minimum <= 0 or maximum < minimum or step <= 0:
            raise ValueError(f"V1.7 FOOD份量边界非法: {record.get('component_id')}")
    return [_official_food_row(record) for record in records]

def _tables(path: Path) -> list[list[list[str]]]:
    if not path.exists():
        return []
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    out = []
    for tbl in root.findall(".//w:tbl", NS):
        rows = []
        for tr in tbl.findall("./w:tr", NS):
            rows.append(["".join(t.text or "" for t in tc.findall(".//w:t", NS)).strip() for tc in tr.findall("./w:tc", NS)])
        out.append(rows)
    return out

def _num(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text or "", re.I)
    return float(m.group(1)) if m else None

def _weight_basis(text: str) -> str:
    """Return a basis only when the source row states it explicitly.

    The catalogue must not infer raw/cooked or edible weights from the food
    name.  Rows without an explicit qualifier are therefore ``unknown`` while
    the original source text is retained for review.
    """
    value = text or ""
    if re.search(r"可食部", value):
        return "edible_portion"
    if re.search(r"包装净含量|净含量", value):
        return "package_net_weight"
    if re.search(r"熟重|熟制", value):
        return "cooked_weight"
    if re.search(r"生重|干重|原料重", value):
        return "raw_weight"
    if re.search(r"份|人份|每份", value):
        return "serving"
    return "unknown"

def _ingredients(text: str) -> list[dict[str, Any]]:
    parts = [p.strip() for p in re.split(r"[；;]+", text or "") if p.strip()]
    result = []
    for part in parts:
        m = re.match(r"(.+?)(\d+(?:\.\d+)?\s*(?:g|ml|个|份))$", part, re.I)
        basis = _weight_basis(part)
        result.append({
            "ingredient_name": m.group(1).strip() if m else part,
            "amount": float(re.search(r"\d+(?:\.\d+)?", m.group(2)).group()) if m else None,
            "unit": re.search(r"[a-zA-Z]+|个|份", m.group(2), re.I).group() if m else None,
            "raw_or_cooked_basis": basis,
            "source_basis_text": part,
        })
    return result

def _food_subcategory(category: str, name: str, ingredient_text: str) -> str:
    """Map only source-explicit terms to a stable subcategory."""
    text = f"{name or ''} {ingredient_text or ''}"
    if category == "staple":
        if "白米" in text:
            return "refined_grain"
        if "糙米" in text or "全麦" in text or "燕麦" in text or "荞麦" in text:
            return "whole_grain"
        if "杂粮" in text or "杂豆" in text:
            return "mixed_grain"
        if "红薯" in text or "山药" in text:
            return "tuber"
        return "unknown"
    if category == "protein":
        if any(term in text for term in ("鲈鱼", "鳕鱼", "鱼", "虾仁")):
            return "fish"
        if "鸡胸" in text or "鸡腿" in text:
            return "poultry"
        if "鸡蛋" in text or "蛋" in text:
            return "egg"
        if "豆腐" in text or "豆浆" in text:
            return "soy"
        if "牛奶" in text or "酸奶" in text:
            return "dairy"
        if "瘦牛肉" in text or "里脊" in text:
            return "lean_meat"
        return "other"
    if category == "snack":
        has_dairy = any(term in text for term in ("牛奶", "酸奶"))
        has_fruit = any(term in text for term in ("苹果", "草莓", "梨", "香蕉", "橙", "猕猴桃"))
        has_nuts = any(term in text for term in ("核桃", "杏仁"))
        has_protein = "鸡蛋" in text or "豆浆" in text
        if has_dairy and not (has_fruit or has_nuts or has_protein):
            return "dairy"
        if has_fruit and not (has_dairy or has_nuts or has_protein):
            return "fruit"
        if has_nuts and not (has_dairy or has_fruit or has_protein):
            return "nuts"
        if has_protein and not (has_dairy or has_fruit or has_nuts):
            return "protein_snack"
        if has_dairy or has_fruit or has_nuts or has_protein:
            return "mixed_snack"
        return "unknown"
    if category == "vegetable":
        # The source rows identify vegetables but do not explicitly label
        # them as non-starchy; keep the subtype unknown rather than infer it.
        return "unknown"
    return "unknown"

def _food_use_tags(category: str, subcategory: str, name: str, ingredient_text: str, protein: float | None, energy: float | None) -> list[str]:
    """Engineering retrieval tags derived from existing source data only."""
    tags = {"regular_meal"} if category in {"staple", "protein", "vegetable"} else {"snack_candidate"}
    if category == "protein" or subcategory in {"dairy", "protein_snack", "soy"} or (protein or 0) >= 8:
        tags.add("protein_support")
    if category == "snack" and (energy or 0) >= 120:
        tags.add("energy_support")
    return sorted(tags)

def _food_row(row: list[str], source: str, source_table: int | None = None) -> dict[str, Any] | None:
    if len(row) < 7 or not re.match(r"^(C|P|V|S)\d{3}$", row[0]):
        return None
    nutrition = row[3]
    item_id, name, ingredients = row[:3]
    category = "staple" if item_id.startswith("C") else "protein" if item_id.startswith("P") else "vegetable" if item_id.startswith("V") else "snack"
    subcategory = _food_subcategory(category, name, ingredients)
    method = "清蒸" if "蒸" in name else "炖" if "炖" in name else "煮" if "煮" in name or "粥" in name else "少油炒" if "炒" in name else "即食" if category == "snack" else "按原文烹调"
    ingredient_rows = _ingredients(ingredients)
    energy = _num(nutrition, r"([\d.]+)\s*kcal")
    protein = _num(nutrition, r"P\s*([\d.]+)")
    return {
        "item_id": f"V2-FOOD-{item_id}", "component_id": item_id, "domain": "FOOD",
        "name": name, "category": category, "subcategory": subcategory, "meal_type": ["breakfast", "lunch", "snack", "dinner"],
        "ingredients": ingredient_rows, "ingredient_amounts": deepcopy(ingredient_rows), "unit": "g/ml",
        "base_portion": deepcopy(ingredient_rows),
        "base_portion_status": "complete" if ingredient_rows and all(x.get("amount") is not None and x.get("unit") for x in ingredient_rows) else "incomplete",
        "raw_or_cooked_basis": next((x.get("raw_or_cooked_basis") for x in ingredient_rows if x.get("raw_or_cooked_basis") != "unknown"), "unknown"),
        "source_basis_text": ingredients, "source_table": source_table,
        "source_text": {"id": item_id, "name": name, "ingredients": ingredients, "nutrition": nutrition, "tags": row[4], "restrictions": row[5], "replacement": row[6]},
        "cooking_method": method, "energy_kcal": energy,
        "protein_g": protein, "carbohydrate_g": _num(nutrition, r"C\s*([\d.]+)"),
        "fat_g": _num(nutrition, r"F\s*([\d.]+)"), "portion_options": [0.5, 0.75, 1, 1.25, 1.5],
        "portion_multiplier_options": [0.5, 0.75, 1, 1.25, 1.5],
        "use_tags": _food_use_tags(category, subcategory, name, ingredients, protein, energy),
        "phenotype_tags": [x.strip() for x in row[4].replace("、", ",").split(",") if x.strip()],
        "goal_tags": [x.strip() for x in row[4].replace("、", ",").split(",") if x.strip()],
        "disease_tags": [], "liver_modifier_tags": [], "allergy_tags": [], "intolerance_tags": [],
        "contraindications": row[5], "replacement_ids": re.findall(r"[CPVS]\d{3}", row[6]),
        "replacement_group": category, "source_document": source, "source_version": "V2.0",
        "review_status": "PENDING", "status": "DRAFT", "mdt_confirmed": False,
    }

def load_food_components(base: Path = RULES) -> list[dict[str, Any]]:
    # V1.7 is the sole runtime FOOD source.  If it is unavailable or invalid,
    # return no FOOD items so the generator marks nutrition generation
    # incomplete instead of silently falling back to a historical DOCX menu.
    official_path = OFFICIAL_FOOD_WORKBOOK if base == RULES else base / OFFICIAL_FOOD_WORKBOOK.name
    return _load_official_food_components(official_path)

def _exercise_row(row: list[str], source: str) -> dict[str, Any] | None:
    if len(row) < 2 or not re.match(r"^[A-Z]\d{2}$", row[0]): return None
    rid, name = row[:2]
    dose = row[3] if len(row) > 3 else None
    return {
        "item_id": f"V2-EX-{rid}", "exercise_id": rid, "domain": "EXERCISE", "name": name,
        "category": "aerobic" if rid.startswith("A") else "resistance" if rid[0] in "ULR" else "flexibility",
        "purpose": row[2] if len(row)>2 else None, "phenotype_tags": [], "goal_tags": [], "functional_level": None,
        "stage": "preop_week1", "indications": row[2] if len(row)>2 else None, "contraindications": row[5] if len(row)>5 else None,
        "position": row[4] if len(row)>4 else None, "equipment": None, "preparation": row[4] if len(row)>4 else None,
        "steps": row[4] if len(row)>4 else None, "duration_range": dose, "reps_range": None, "sets_range": None,
        "frequency_range": (re.findall(r"\d+[–-]\d+次/周", dose)[0] if dose and re.findall(r"\d+[–-]\d+次/周", dose) else None), "intensity_range": None, "rpe_borg_range": None,
        "rest_interval": None, "progression_rule": None, "regression_rule": None,
        "precautions": row[5] if len(row)>5 else None, "stop_conditions": row[5] if len(row)>5 else "出现不适立即停止并联系医护",
        "alternative_ids": re.findall(r"[A-Z]\d{2}", row[6] if len(row)>6 else ""), "requires_supervision": False,
        "requires_clinician_order": False, "video_id": None, "source_document": source, "source_version": "V2.0",
        "status": "DRAFT", "mdt_confirmed": False,
    }


def _exercise_v3_row(row: list[str], source: str) -> dict[str, Any] | None:
    """Parse the V3.0 action catalogue (table with 9 labelled columns).

    V2 used a compact table whose fourth column was a dose string.  V3 adds
    explicit stage/intensity/indication/frequency columns; keeping this
    parser separate prevents the old positional assumptions from silently
    dropping the weekly prescription metadata.
    """
    if len(row) < 7 or not re.match(r"^[A-Z]\d{2}$", row[0].strip()):
        return None
    rid, name, tag, stage, intensity, indication, dose = [x.strip() for x in row[:7]]
    stop = row[7].strip() if len(row) > 7 else "出现不适立即停止并联系医护"
    frequency = row[8].strip() if len(row) > 8 else None
    domain = "aerobic" if "有氧" in tag else "resistance" if "抗阻" in tag or rid[0] in "ULR" else "flexibility" if "柔韧" in tag else "core" if "核心" in tag else "breathing"
    return {
        "item_id": f"V3-EX-{rid}", "exercise_id": rid, "domain": "EXERCISE",
        "name": name, "category": domain, "purpose": tag, "phenotype_tags": re.findall(r"[A-F]", indication),
        "goal_tags": [], "functional_level": indication, "stage": stage,
        "indications": indication, "contraindications": stop, "position": None,
        "equipment": "resistance_band" if "弹力带" in name else "none",
        "preparation": None, "steps": f"按动作库执行：{name}。", "duration_range": dose,
        "reps_range": dose if "次" in dose or "步" in dose else None,
        "sets_range": dose if "组" in dose else None, "frequency_range": frequency,
        "intensity_range": intensity, "rpe_borg_range": None, "rest_interval": "组间按耐受休息",
        "progression_rule": "每次仅调整一个变量，先时间/次数后强度。",
        "regression_rule": "症状或功能受限时降阶并使用替代动作。",
        "precautions": stop, "stop_conditions": stop,
        "alternative_ids": [], "requires_supervision": "平衡差" in indication,
        "requires_clinician_order": False, "video_id": None, "source_document": source,
        "source_version": "V3.0", "status": "DRAFT", "mdt_confirmed": False,
        "candidate_dose": dose, "candidate_frequency": frequency,
    }

def load_exercises(base: Path = RULES) -> list[dict[str, Any]]:
    # V3 is the current exercise authority; V2 remains a history/fallback.
    paths = sorted(base.glob("*运动处方生成规则与动作库*.docx"))
    path = next((p for p in paths if "V3.0" in p.name), paths[0] if paths else None)
    if not path: return []
    result=[]
    for table in _tables(path):
        is_v3_action_table = bool(table and "默认频率" in " ".join(table[0]))
        for row in table[1:]:
            item = _exercise_v3_row(row, path.name) if is_v3_action_table else _exercise_row(row,path.name)
            # P01-P06 belong to the pulmonary-prehab catalogue, not the
            # 31-item EXERCISE action set, even though the V3 document repeats
            # them in its cross-domain table.
            if item and str(item.get("exercise_id", ""))[:1] in {"A", "C", "S", "U", "L", "R"}:
                result.append(item)
    for item in result:
        dose = item.get("duration_range")
        if dose:
            item["candidate_dose"] = dose
            freq = re.search(r"\d+[–-]\d+次/周|\d+[–-]\d+组/周", dose)
            reps = re.search(r"\d+[–-]\d+次(?:/组)?(?!/周|/日)", dose)
            sets = re.search(r"\d+[–-]\d+组", dose)
            if freq:
                item["frequency_range"] = freq.group(0)
            if sets:
                item["sets_range"] = sets.group(0)
            if reps:
                item["reps_range"] = reps.group(0)
    return list({x["exercise_id"]: x for x in result}.values())

def _pulmonary_rows(base: Path = RULES) -> list[dict[str, Any]]:
    path = next(base.glob("*肺预康复知识库*.docx"), None)
    if not path: return []
    result=[]
    dose_rows: dict[str, list[str]] = {}
    for table in _tables(path):
        if not table:
            continue
        if any("项目剂量" in h for h in table[0]):
            for row in table[1:]:
                if row and re.match(r"^P0[1-6]", row[0].strip()):
                    dose_rows[row[0].strip()[:3]] = row
            continue
        if not any("动作" in h for h in table[0]):
            continue
        for row in table[1:]:
            if len(row)<2 or not re.match(r"^P0[1-6]$", row[0].strip()): continue
            pid = re.match(r"^(P0[1-6])", row[0]).group(1)
            result.append({
                "item_id":f"V2-PR-{pid}","pulmonary_id":pid,"domain":"PULMONARY","name":row[1],
                "purpose":row[2] if len(row)>2 else None,"indications":None,
                "position":row[3] if len(row)>3 else None,"equipment":"医护指定设备" if pid=="P06" else None,"preparation":None,"steps":row[4] if len(row)>4 else None,
                "dose_range":None,"frequency_range":None,"cycle_range":None,
                "precautions":row[5] if len(row)>5 else None,"stop_conditions":row[5] if len(row)>5 else "出现不适立即停止并联系医护",
                "contraindications":row[1] if len(row)>1 else None,"alternative_ids":re.findall(r"P0[1-6]", " ".join(row)),
                "requires_device":pid=="P06","requires_clinician_order":pid=="P06","requires_supervision":pid=="P06",
                "video_id":None,"source_document":path.name,"source_version":"V2.0","status":"DRAFT","mdt_confirmed":False,
            })
    merged = []
    for item in result:
        row = dose_rows.get(item["pulmonary_id"])
        if row:
            item["dose_range"] = row[1] or None
            item["candidate_dose"] = row[1] or None
            item["indications"] = row[2] if len(row) > 2 else item.get("indications")
            item["stop_conditions"] = row[3] if len(row) > 3 else item.get("stop_conditions")
            item["alternative_ids"] = re.findall(r"P0[1-6]", row[4] if len(row) > 4 else "")
            text = row[1] or ""
            # Keep documented daily cadence separate from the exercise dose
            # string. P03/P04 express frequency as groups per day.
            freq = re.findall(r"\d+[–-]\d+次/日|\d+[–-]\d+组/日|按需|按设备\+医护处方", text)
            item["frequency_range"] = freq[0] if freq else None
            item["cycle_range"] = text if "循环" in text else None
        merged.append(item)
    return list({x["pulmonary_id"]:x for x in merged}.values())

FOOD_COMPONENTS_V2 = load_food_components()
EXERCISE_ACTIONS_V2 = load_exercises()
PULMONARY_ACTIONS_V2 = _pulmonary_rows()

def food_catalog_audit(items: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Return item-level, read-only provenance for every FOOD component."""
    foods = list(items if items is not None else FOOD_COMPONENTS_V2)
    fields = (
        "component_id", "name", "category", "subcategory", "source_document",
        "source_table", "source_text", "ingredients", "ingredient_amounts",
        "energy_kcal", "protein_g", "carbohydrate_g", "fat_g",
        "raw_or_cooked_basis", "source_basis_text", "base_portion",
        "base_portion_status", "portion_options", "portion_multiplier_options",
        "portion_min", "portion_max", "portion_step", "weight_basis", "portion_boundary_status",
        "use_tags", "status", "source_version", "source_document_original",
    )
    return [{field: deepcopy(item.get(field)) for field in fields} for item in foods]

def food_catalog_gap_report(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return a read-only structural audit of the parsed FOOD catalogue.

    Counts are derived from source rows and existing fields; this helper never
    invents portions, medical limits, or new components.
    """
    foods = list(items if items is not None else FOOD_COMPONENTS_V2)
    basis_unknown = [x["component_id"] for x in foods if x.get("raw_or_cooked_basis") == "unknown"]
    base_incomplete = [x["component_id"] for x in foods if x.get("base_portion_status") != "complete"]
    subcategory_unknown = [x["component_id"] for x in foods if x.get("subcategory") == "unknown"]
    source_text = {x["component_id"]: str((x.get("source_text") or {}).get("ingredients") or "") for x in foods}
    snack = [x for x in foods if x.get("category") == "snack"]
    snack_text = {x["component_id"]: str((x.get("source_text") or {}).get("ingredients") or "") for x in snack}
    candidate_id_groups = {
        "dairy": [x["component_id"] for x in snack if any(term in snack_text[x["component_id"]] for term in ("牛奶", "酸奶"))],
        "fruit": [x["component_id"] for x in snack if any(term in snack_text[x["component_id"]] for term in ("苹果", "草莓", "梨", "香蕉", "橙", "猕猴桃"))],
        "nuts": [x["component_id"] for x in snack if any(term in snack_text[x["component_id"]] for term in ("核桃", "杏仁"))],
        "protein_snack": [x["component_id"] for x in snack if "protein_support" in (x.get("use_tags") or [])],
        "energy_support": [x["component_id"] for x in snack if "energy_support" in (x.get("use_tags") or [])],
        "staple": [x["component_id"] for x in foods if x.get("category") == "staple"],
        "other_snack": [x["component_id"] for x in snack if x.get("subcategory") == "mixed_snack"],
    }
    return {
        "total": len(foods),
        "category_counts": {category: sum(1 for x in foods if x.get("category") == category) for category in ("staple", "protein", "vegetable", "snack")},
        "field_completeness": {
            field: sum(1 for x in foods if x.get(field) not in (None, "", []))
            for field in ("ingredients", "ingredient_amounts", "portion_options", "energy_kcal", "protein_g", "carbohydrate_g", "fat_g")
        },
        "explicit_portion_min_count": sum(1 for x in foods if x.get("portion_min") is not None),
        "explicit_portion_max_count": sum(1 for x in foods if x.get("portion_max") is not None),
        "explicit_portion_step_count": sum(1 for x in foods if x.get("portion_step") is not None),
        "weight_basis_explicit_count": len(foods) - len(basis_unknown),
        "weight_basis_unknown_ids": basis_unknown,
        "base_portion_incomplete_ids": base_incomplete,
        "subcategory_counts": {subcategory: sum(1 for x in foods if x.get("subcategory") == subcategory) for subcategory in sorted({x.get("subcategory") for x in foods})},
        "subcategory_unknown_ids": subcategory_unknown,
        "d_e_candidate_counts": {
            "dairy": len(candidate_id_groups["dairy"]),
            "fruit": len(candidate_id_groups["fruit"]),
            "nuts": len(candidate_id_groups["nuts"]),
            "protein_snack": len(candidate_id_groups["protein_snack"]),
            "staple": len(candidate_id_groups["staple"]),
            "other_snack": len(candidate_id_groups["other_snack"]),
            "energy_support": len(candidate_id_groups["energy_support"]),
        },
        "d_e_candidate_ids": candidate_id_groups,
        "unreliable_for_portion_optimization_ids": sorted(set(basis_unknown + base_incomplete)),
    }

def structured_catalog() -> dict[str, list[dict[str, Any]]]:
    return {"FOOD": FOOD_COMPONENTS_V2, "EXERCISE": EXERCISE_ACTIONS_V2, "PULMONARY": PULMONARY_ACTIONS_V2}
