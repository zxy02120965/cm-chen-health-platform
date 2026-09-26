"""Read-only runtime loader for the frozen ZXY Week1 V4 food assets.

This module deliberately uses the XLSX XML primitives already available in
the Python standard library.  It does not depend on ``openpyxl`` and it never
looks in ``outputs/`` or at the legacy V1.7 catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import posixpath
from types import MappingProxyType
from typing import Any, Mapping
import zipfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "backend" / "knowledge" / "zxy_week1"
MANIFEST_PATH = ASSET_ROOT / "manifest.json"
FOOD_COMPONENT_SHEET = "原始数据参考"
FOOD_REVIEW_SHEET = "MDT核心审核表"
FOOD_MAPPING_SHEET = "份量执行映射_候选"
INGREDIENT_SHEET = "Ingredient_Master_MDT"
INGREDIENT_MAPPING_SHEET = "组件→食材映射"

XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


class V4FoodDataError(ValueError):
    """Raised when a frozen V4 food asset cannot satisfy its runtime contract."""


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def _number(value: Any, *, field: str, record_id: str) -> float:
    value = _clean(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        raise V4FoodDataError(f"{field} must be numeric for {record_id}: {value!r}") from None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是"}


def _scale_list(value: Any, *, field: str, record_id: str) -> tuple[float, ...]:
    text = str(_clean(value) or "")
    try:
        values = tuple(float(part.strip()) for part in text.split(",") if part.strip())
    except ValueError:
        raise V4FoodDataError(f"{field} invalid for {record_id}: {value!r}") from None
    if not values or len(set(values)) != len(values):
        raise V4FoodDataError(f"{field} empty/duplicated for {record_id}")
    return tuple(sorted(values))


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for char in letters.upper():
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//a:t", XLSX_NS))
    value = cell.find("a:v", XLSX_NS)
    if value is None:
        return ""
    raw = value.text or ""
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (IndexError, ValueError):
            raise V4FoodDataError(f"invalid shared string index: {raw}") from None
    if cell_type == "b":
        return raw == "1"
    return raw


def _read_xlsx_sheet(path: Path, sheet_name: str) -> list[list[Any]]:
    """Read one worksheet without loading or rewriting the workbook."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", XLSX_NS):
                shared_strings.append("".join(t.text or "" for t in item.findall(".//a:t", XLSX_NS)))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        target = None
        for sheet in workbook.findall("a:sheets/a:sheet", XLSX_NS):
            if sheet.attrib.get("name") != sheet_name:
                continue
            rel_id = sheet.attrib.get("{" + XLSX_NS["r"] + "}id")
            target = relmap.get(rel_id)
            break
        if not target:
            raise V4FoodDataError(f"workbook {path.name} missing sheet {sheet_name}")
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = posixpath.join("xl", target)
        worksheet = ET.fromstring(archive.read(target))
        rows: list[list[Any]] = []
        for row in worksheet.findall(".//a:sheetData/a:row", XLSX_NS):
            cells: dict[int, Any] = {}
            for cell in row.findall("a:c", XLSX_NS):
                cells[_column_index(cell.attrib.get("r", "A1"))] = _cell_value(cell, shared_strings)
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, "") for i in range(width)])
            else:
                rows.append([])
        return rows


def _records(rows: list[list[Any]], header_row: int = 0) -> tuple[list[str], list[dict[str, Any]]]:
    if len(rows) <= header_row:
        raise V4FoodDataError("worksheet has no header row")
    headers = [str(value).strip() if value is not None else "" for value in rows[header_row]]
    if not any(headers):
        raise V4FoodDataError("worksheet header row is empty")
    records: list[dict[str, Any]] = []
    for raw in rows[header_row + 1 :]:
        padded = raw + [""] * max(0, len(headers) - len(raw))
        if not any(_clean(value) is not None for value in padded):
            continue
        records.append({header: padded[i] for i, header in enumerate(headers) if header})
    return headers, records


def _require_headers(headers: list[str], required: tuple[str, ...], label: str) -> None:
    missing = [field for field in required if field not in headers]
    if missing:
        raise V4FoodDataError(f"{label} missing required columns: {missing}")


@dataclass(frozen=True)
class IngredientRecord:
    ingredient_id: str
    ingredient_name: str
    unit: str
    min_amount: float
    max_amount: float
    step: float
    discrete_rule: str
    package_rule: str | None
    nutrition_source: str
    nutrition_status: str
    knowledge_status: str
    final_decision: str
    execution_eligible: bool
    exact_nutrition_eligible: bool
    nutrition_source_pending: bool
    requires_clinician_review: bool
    # Compatibility alias retained for callers from the Phase 2A first pass.
    active: bool


@dataclass(frozen=True)
class ComponentIngredientMapping:
    ingredient_id: str
    ingredient_name: str
    algorithmic_amount: float
    executable_amount: float
    unit: str
    execution_rule_status: str


@dataclass(frozen=True)
class StandardComponentRecord:
    component_id: str
    component_name: str
    category: str
    subcategory: str | None
    allowed_scales: tuple[float, ...]
    mappings_by_scale: Mapping[float, tuple[ComponentIngredientMapping, ...]]
    nutrition_status: str
    scale_resolution_status: str
    final_decision: str
    execution_eligible: bool
    exact_nutrition_eligible: bool
    nutrition_source_pending: bool
    requires_clinician_review: bool
    # Compatibility alias: active means exact-nutrition eligible, not merely executable.
    active: bool


@dataclass(frozen=True)
class V4FoodRuntime:
    manifest_path: Path
    ingredient_source: Path
    food_source: Path
    ingredients: Mapping[str, IngredientRecord]
    components: Mapping[str, StandardComponentRecord]

    def ingredient(self, ingredient_id: str) -> IngredientRecord:
        try:
            return self.ingredients[ingredient_id]
        except KeyError:
            raise V4FoodDataError(f"unknown ingredient_id: {ingredient_id}") from None

    def component(self, component_id: str) -> StandardComponentRecord:
        try:
            return self.components[component_id]
        except KeyError:
            raise V4FoodDataError(f"unknown component_id: {component_id}") from None


def _asset_paths() -> tuple[Path, Path]:
    if not MANIFEST_PATH.exists():
        raise V4FoodDataError(f"missing V4 manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_role = {asset.get("role"): asset for asset in manifest.get("assets", []) if asset.get("active") is True}
    ingredient = by_role.get("MDT_INGREDIENT_MASTER")
    food = by_role.get("MDT_STANDARD_COMPONENT_EXECUTION")
    if not ingredient or not food:
        raise V4FoodDataError("manifest must contain active Ingredient Master and FOOD V1.2 assets")
    paths: list[Path] = []
    for asset in (ingredient, food):
        path = ASSET_ROOT / str(asset["relative_path"])
        if not path.exists():
            raise V4FoodDataError(f"missing manifest asset: {path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != asset.get("sha256"):
            raise V4FoodDataError(f"asset SHA256 mismatch: {path}")
        paths.append(path)
    return paths[0], paths[1]


def _load_runtime() -> V4FoodRuntime:
    ingredient_path, food_path = _asset_paths()

    ingredient_rows = _read_xlsx_sheet(ingredient_path, INGREDIENT_SHEET)
    ingredient_headers, ingredient_records = _records(ingredient_rows)
    _require_headers(
        ingredient_headers,
        (
            "ingredient_id", "ingredient_name", "nutrition_source_status", "execution_unit",
            "candidate_min", "candidate_max", "candidate_step", "离散单位/包装规则",
            "knowledge_status", "MDT_final_decision",
        ),
        INGREDIENT_SHEET,
    )
    ingredients: dict[str, IngredientRecord] = {}
    for record in ingredient_records:
        ingredient_id = str(_clean(record.get("ingredient_id")) or "")
        if not ingredient_id:
            raise V4FoodDataError("Ingredient Master contains an empty ingredient_id")
        if ingredient_id in ingredients:
            raise V4FoodDataError(f"duplicate ingredient_id: {ingredient_id}")
        minimum = _number(record.get("candidate_min"), field="candidate_min", record_id=ingredient_id)
        maximum = _number(record.get("candidate_max"), field="candidate_max", record_id=ingredient_id)
        step = _number(record.get("candidate_step"), field="candidate_step", record_id=ingredient_id)
        if minimum <= 0 or maximum < minimum or step <= 0:
            raise V4FoodDataError(f"invalid execution bounds for {ingredient_id}")
        rule = str(_clean(record.get("离散单位/包装规则")) or "")
        knowledge_status = str(_clean(record.get("knowledge_status")) or "")
        final_decision = str(_clean(record.get("MDT_final_decision")) or "")
        execution_eligible = bool(
            str(_clean(record.get("execution_unit")) or "")
            and minimum > 0
            and maximum >= minimum
            and step > 0
        )
        exact_nutrition_eligible = execution_eligible and (
            knowledge_status == "ACTIVE"
            and final_decision == "ACTIVE_FOR_EXACT"
        )
        ingredients[ingredient_id] = IngredientRecord(
            ingredient_id=ingredient_id,
            ingredient_name=str(_clean(record.get("ingredient_name")) or ""),
            unit=str(_clean(record.get("execution_unit")) or ""),
            min_amount=minimum,
            max_amount=maximum,
            step=step,
            discrete_rule=rule,
            package_rule=rule if ("包装" in rule or "净含量" in rule) else None,
            nutrition_source=str(_clean(record.get("nutrition_source_status")) or ""),
            nutrition_status=str(_clean(record.get("candidate_data_check")) or ""),
            knowledge_status=knowledge_status,
            final_decision=final_decision,
            execution_eligible=execution_eligible,
            exact_nutrition_eligible=exact_nutrition_eligible,
            nutrition_source_pending=not exact_nutrition_eligible,
            requires_clinician_review=not exact_nutrition_eligible,
            active=exact_nutrition_eligible,
        )
    if len(ingredients) != 48:
        raise V4FoodDataError(f"Ingredient Master expected 48 unique rows, got {len(ingredients)}")

    ingredient_mapping_rows = _read_xlsx_sheet(ingredient_path, INGREDIENT_MAPPING_SHEET)
    mapping_headers, ingredient_mapping_records = _records(ingredient_mapping_rows)
    _require_headers(mapping_headers, ("component_id", "ingredient_id", "ingredient_name"), INGREDIENT_MAPPING_SHEET)
    component_ingredient_ids: dict[tuple[str, str], str] = {}
    for record in ingredient_mapping_records:
        component_id = str(_clean(record.get("component_id")) or "")
        ingredient_id = str(_clean(record.get("ingredient_id")) or "")
        ingredient_name = str(_clean(record.get("ingredient_name")) or "")
        if not component_id or not ingredient_id:
            raise V4FoodDataError("component→ingredient mapping has an empty key")
        if ingredient_id not in ingredients:
            raise V4FoodDataError(f"mapping references unknown ingredient_id: {ingredient_id}")
        key = (component_id, ingredient_name)
        if key in component_ingredient_ids and component_ingredient_ids[key] != ingredient_id:
            raise V4FoodDataError(f"ambiguous component ingredient mapping: {key}")
        component_ingredient_ids[key] = ingredient_id

    food_rows = _read_xlsx_sheet(food_path, FOOD_COMPONENT_SHEET)
    food_headers, food_records = _records(food_rows)
    _require_headers(food_headers, ("component_id", "component_name", "category", "subcategory"), FOOD_COMPONENT_SHEET)
    food_by_id: dict[str, dict[str, Any]] = {}
    for record in food_records:
        component_id = str(_clean(record.get("component_id")) or "")
        if not component_id:
            raise V4FoodDataError("FOOD component sheet contains an empty component_id")
        if component_id in food_by_id:
            raise V4FoodDataError(f"duplicate component_id: {component_id}")
        food_by_id[component_id] = record
    if len(food_by_id) != 49:
        raise V4FoodDataError(f"FOOD component sheet expected 49 unique rows, got {len(food_by_id)}")

    review_rows = _read_xlsx_sheet(food_path, FOOD_REVIEW_SHEET)
    review_headers, review_records = _records(review_rows, header_row=2)
    _require_headers(review_headers, ("component_id", "nutrition_status", "allowed_component_scales", "scale_resolution_status", "MDT_final_decision"), FOOD_REVIEW_SHEET)
    review_by_id: dict[str, dict[str, Any]] = {}
    for record in review_records:
        component_id = str(_clean(record.get("component_id")) or "")
        if not component_id:
            continue
        if component_id in review_by_id:
            raise V4FoodDataError(f"duplicate component_id in review sheet: {component_id}")
        review_by_id[component_id] = record
    if set(review_by_id) != set(food_by_id):
        raise V4FoodDataError("FOOD review and component sheets do not contain the same component IDs")

    execution_rows = _read_xlsx_sheet(food_path, FOOD_MAPPING_SHEET)
    execution_headers, execution_records = _records(execution_rows)
    _require_headers(execution_headers, ("component_id", "原料", "内部scale", "单位", "算法量", "允许该scale", "执行量候选数值（公式）"), FOOD_MAPPING_SHEET)
    mappings: dict[tuple[str, float], list[ComponentIngredientMapping]] = {}
    for record in execution_records:
        component_id = str(_clean(record.get("component_id")) or "")
        if component_id not in food_by_id:
            raise V4FoodDataError(f"execution mapping references unknown component_id: {component_id}")
        # Disallowed scales are represented by intentional placeholder rows
        # without an ingredient.  They are not executable mappings.
        allowed = _bool(record.get("允许该scale"))
        if not allowed:
            continue
        ingredient_name = str(_clean(record.get("原料")) or "")
        ingredient_id = component_ingredient_ids.get((component_id, ingredient_name))
        if ingredient_id is None:
            raise V4FoodDataError(f"cannot resolve ingredient mapping: {component_id}/{ingredient_name}")
        scale = _number(record.get("内部scale"), field="内部scale", record_id=component_id)
        algorithmic = _number(record.get("算法量"), field="算法量", record_id=component_id)
        executable_raw = _clean(record.get("执行量候选数值（公式）"))
        if executable_raw is None:
            raise V4FoodDataError(f"allowed execution row lacks executable amount: {component_id}/{scale}/{ingredient_id}")
        executable = _number(executable_raw, field="执行量候选数值（公式）", record_id=component_id)
        key = (component_id, scale)
        mappings.setdefault(key, []).append(ComponentIngredientMapping(
            ingredient_id=ingredient_id,
            ingredient_name=ingredient_name,
            algorithmic_amount=algorithmic,
            executable_amount=executable,
            unit=str(_clean(record.get("单位")) or ""),
            execution_rule_status="MAPPED_EXECUTABLE",
        ))

    components: dict[str, StandardComponentRecord] = {}
    for component_id, record in food_by_id.items():
        review = review_by_id[component_id]
        allowed_scales = _scale_list(review.get("allowed_component_scales"), field="allowed_component_scales", record_id=component_id)
        by_scale: dict[float, tuple[ComponentIngredientMapping, ...]] = {}
        for scale in allowed_scales:
            entries = tuple(mappings.get((component_id, scale), ()))
            if not entries:
                raise V4FoodDataError(f"missing execution mapping: {component_id}/{scale}")
            if len({entry.ingredient_id for entry in entries}) != len(entries):
                raise V4FoodDataError(f"duplicate ingredient mapping: {component_id}/{scale}")
            by_scale[scale] = entries
        final_decision = str(_clean(review.get("MDT_final_decision")) or "")
        nutrition_status = str(_clean(review.get("nutrition_status")) or "")
        execution_eligible = all(
            ingredients[entry.ingredient_id].execution_eligible
            for entries in by_scale.values()
            for entry in entries
        )
        exact_nutrition_eligible = execution_eligible and (
            final_decision == "ACTIVE_FOR_EXACT"
            and nutrition_status == "ACTIVE_RECALCULATED"
            and all(
                ingredients[entry.ingredient_id].exact_nutrition_eligible
                for entries in by_scale.values()
                for entry in entries
            )
        )
        components[component_id] = StandardComponentRecord(
            component_id=component_id,
            component_name=str(_clean(record.get("component_name")) or ""),
            category=str(_clean(record.get("category")) or ""),
            subcategory=_clean(record.get("subcategory")),
            allowed_scales=allowed_scales,
            mappings_by_scale=MappingProxyType(by_scale),
            nutrition_status=nutrition_status,
            scale_resolution_status=str(_clean(review.get("scale_resolution_status")) or ""),
            final_decision=final_decision,
            execution_eligible=execution_eligible,
            exact_nutrition_eligible=exact_nutrition_eligible,
            nutrition_source_pending=not exact_nutrition_eligible,
            requires_clinician_review=not exact_nutrition_eligible,
            active=exact_nutrition_eligible,
        )
    return V4FoodRuntime(
        manifest_path=MANIFEST_PATH,
        ingredient_source=ingredient_path,
        food_source=food_path,
        ingredients=MappingProxyType(ingredients),
        components=MappingProxyType(components),
    )


@lru_cache(maxsize=1)
def load_v4_food_data() -> V4FoodRuntime:
    """Load and validate the frozen V4 runtime assets once per process."""
    return _load_runtime()


def clear_v4_food_data_cache() -> None:
    load_v4_food_data.cache_clear()
