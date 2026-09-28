"""Manifest-backed FOOD selection metadata for the Week1 runtime.

Selection suitability is deliberately separate from execution and nutrition
truth.  This module reads only the MDT-finalized V1.4 metadata asset; amounts,
ingredient mappings and exact nutrition eligibility remain owned by
``v4_food_data`` (the manifest-backed V1.3 execution assets).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "backend" / "knowledge" / "zxy_week1"
MANIFEST_PATH = ASSET_ROOT / "manifest.json"
SELECTION_ROLE = "FOOD_SELECTION_METADATA"
SELECTION_VERSION = "V1.4"
MDT_STATUS = "MDT_APPROVED_FINAL"
ALLOWED_MEAL_SLOTS = frozenset({"breakfast", "lunch", "dinner", "snack", "any"})
ALLOWED_BREAKFAST_ALLOWED = frozenset({"YES", "NO"})
ALLOWED_BREAKFAST_PRIORITY = frozenset({"PREFERRED", "ACCEPTABLE", "NOT_PREFERRED", "NOT_ALLOWED"})
ALLOWED_READINESS = frozenset({"READY", "SOURCE_PENDING", "REPLACEMENT_PENDING", "SOURCE_AND_REPLACEMENT_PENDING"})
ALLOWED_REVIEW_DECISIONS = frozenset({"APPROVED", "NEEDS_REVISION"})


class V4FoodSelectionError(ValueError):
    """Raised when the active MDT selection asset is missing or invalid."""


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def _csv_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        values = value
    else:
        values = str(_clean(value) or "").split(",")
    return tuple(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().upper() in {"YES", "TRUE", "1"}


@dataclass(frozen=True)
class FoodSelectionRecord:
    component_id: str
    dish_name: str
    category: str
    approved_meal_slots: tuple[str, ...]
    breakfast_allowed: str
    breakfast_priority: str
    approved_setting_tags: tuple[str, ...]
    approved_replacement_group: str | None
    approved_replacement_component_ids: tuple[str, ...]
    final_runtime_readiness: str
    final_execution_basis: str
    review_decision: str
    replacement_review_decision: str
    mdt_finalized: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "dish_name": self.dish_name,
            "category": self.category,
            "approved_meal_slots": list(self.approved_meal_slots),
            "breakfast_allowed": self.breakfast_allowed,
            "breakfast_priority": self.breakfast_priority,
            "approved_setting_tags": list(self.approved_setting_tags),
            "approved_replacement_group": self.approved_replacement_group,
            "approved_replacement_component_ids": list(self.approved_replacement_component_ids),
            "final_runtime_readiness": self.final_runtime_readiness,
            "final_execution_basis": self.final_execution_basis,
            "review_decision": self.review_decision,
            "replacement_review_decision": self.replacement_review_decision,
            "mdt_finalized": self.mdt_finalized,
            "source_version": SELECTION_VERSION,
            "mdt_status": MDT_STATUS,
        }


@dataclass(frozen=True)
class FoodSelectionProvenance:
    role: str
    version: str
    relative_path: str
    sha256: str
    status: str
    mdt_status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "version": self.version,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "status": self.status,
            "mdt_status": self.mdt_status,
            "manifest_registered": True,
        }


@dataclass(frozen=True)
class FoodSelectionRuntime:
    manifest_path: Path
    asset_path: Path
    records: Mapping[str, FoodSelectionRecord]
    provenance: FoodSelectionProvenance

    def record(self, component_id: str) -> FoodSelectionRecord:
        try:
            return self.records[str(component_id)]
        except KeyError:
            raise V4FoodSelectionError(f"unknown selection component_id: {component_id}") from None


def _read_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise V4FoodSelectionError(f"missing V4 manifest: {MANIFEST_PATH}")
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise V4FoodSelectionError(f"invalid V4 manifest: {MANIFEST_PATH}") from exc


def _active_selection_entry() -> dict[str, Any]:
    manifest = _read_manifest()
    entries = [
        entry for entry in manifest.get("assets", [])
        if entry.get("role") == SELECTION_ROLE and entry.get("active") is True
    ]
    if len(entries) != 1:
        raise V4FoodSelectionError(f"manifest must contain exactly one active {SELECTION_ROLE} asset")
    entry = entries[0]
    if str(entry.get("version") or "") != SELECTION_VERSION:
        raise V4FoodSelectionError(f"{SELECTION_ROLE} must be version {SELECTION_VERSION}")
    if str(entry.get("status") or "") != "ACTIVE":
        raise V4FoodSelectionError(f"{SELECTION_ROLE} must be ACTIVE")
    if str(entry.get("mdt_status") or "") != MDT_STATUS:
        raise V4FoodSelectionError(f"{SELECTION_ROLE} must be {MDT_STATUS}")
    relative_path = str(entry.get("relative_path") or "")
    if not relative_path or relative_path.lower().startswith("outputs/") or "outputs" in relative_path.lower():
        raise V4FoodSelectionError("selection metadata asset cannot be loaded from outputs/")
    path = ASSET_ROOT / relative_path
    if not path.is_file():
        raise V4FoodSelectionError(f"missing manifest selection asset: {path}")
    expected_sha = str(entry.get("sha256") or "").lower()
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if not expected_sha or actual_sha != expected_sha:
        raise V4FoodSelectionError(f"selection metadata SHA256 mismatch: {path}")
    return entry


def _parse_record(raw: Mapping[str, Any]) -> FoodSelectionRecord:
    required = (
        "component_id", "dish_name", "category", "approved_meal_slots",
        "breakfast_allowed", "breakfast_priority", "approved_replacement_group",
        "approved_replacement_component_ids", "final_runtime_readiness",
        "final_execution_basis", "review_decision", "mdt_finalized",
    )
    missing = [field for field in required if field not in raw]
    if missing:
        raise V4FoodSelectionError(f"selection metadata missing fields: {missing}")
    component_id = str(_clean(raw.get("component_id")) or "")
    if not component_id:
        raise V4FoodSelectionError("selection metadata contains an empty component_id")
    slots = _csv_values(raw.get("approved_meal_slots"))
    if not slots or not set(slots).issubset(ALLOWED_MEAL_SLOTS):
        raise V4FoodSelectionError(f"invalid approved_meal_slots for {component_id}: {slots}")
    breakfast_allowed = str(_clean(raw.get("breakfast_allowed")) or "")
    if breakfast_allowed not in ALLOWED_BREAKFAST_ALLOWED:
        raise V4FoodSelectionError(f"invalid breakfast_allowed for {component_id}: {breakfast_allowed}")
    breakfast_priority = str(_clean(raw.get("breakfast_priority")) or "")
    if breakfast_priority not in ALLOWED_BREAKFAST_PRIORITY:
        raise V4FoodSelectionError(f"invalid breakfast_priority for {component_id}: {breakfast_priority}")
    readiness = str(_clean(raw.get("final_runtime_readiness")) or "")
    if readiness not in ALLOWED_READINESS:
        raise V4FoodSelectionError(f"invalid final_runtime_readiness for {component_id}: {readiness}")
    decision = str(_clean(raw.get("review_decision")) or "")
    replacement_decision = str(_clean(raw.get("replacement_review_decision")) or decision)
    if decision not in ALLOWED_REVIEW_DECISIONS:
        raise V4FoodSelectionError(f"invalid review_decision for {component_id}: {decision}")
    if replacement_decision not in ALLOWED_REVIEW_DECISIONS:
        raise V4FoodSelectionError(f"invalid replacement_review_decision for {component_id}: {replacement_decision}")
    if not _bool(raw.get("mdt_finalized")):
        raise V4FoodSelectionError(f"selection metadata is not MDT finalized for {component_id}")
    return FoodSelectionRecord(
        component_id=component_id,
        dish_name=str(_clean(raw.get("dish_name")) or ""),
        category=str(_clean(raw.get("category")) or ""),
        approved_meal_slots=slots,
        breakfast_allowed=breakfast_allowed,
        breakfast_priority=breakfast_priority,
        approved_setting_tags=_csv_values(raw.get("approved_setting_tags")),
        approved_replacement_group=_clean(raw.get("approved_replacement_group")),
        approved_replacement_component_ids=_csv_values(raw.get("approved_replacement_component_ids")),
        final_runtime_readiness=readiness,
        final_execution_basis=str(_clean(raw.get("final_execution_basis")) or ""),
        review_decision=decision,
        replacement_review_decision=replacement_decision,
        mdt_finalized=True,
    )


@lru_cache(maxsize=1)
def load_v4_food_selection_metadata() -> FoodSelectionRuntime:
    entry = _active_selection_entry()
    path = ASSET_ROOT / str(entry["relative_path"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise V4FoodSelectionError(f"invalid selection metadata JSON: {path}") from exc
    if payload.get("asset_role") != SELECTION_ROLE or payload.get("version") != SELECTION_VERSION or payload.get("source_version") != SELECTION_VERSION:
        raise V4FoodSelectionError("selection metadata JSON identity does not match manifest")
    if payload.get("mdt_status") != MDT_STATUS:
        raise V4FoodSelectionError("selection metadata JSON is not MDT_APPROVED_FINAL")
    raw_components = payload.get("components")
    if not isinstance(raw_components, list) or len(raw_components) != 49:
        raise V4FoodSelectionError("selection metadata must contain 49 components")
    records: dict[str, FoodSelectionRecord] = {}
    for raw in raw_components:
        if not isinstance(raw, Mapping):
            raise V4FoodSelectionError("selection metadata component row must be an object")
        record = _parse_record(raw)
        if record.component_id in records:
            raise V4FoodSelectionError(f"duplicate selection component_id: {record.component_id}")
        records[record.component_id] = record
    provenance = FoodSelectionProvenance(
        role=str(entry["role"]),
        version=str(entry["version"]),
        relative_path=Path(str(entry["relative_path"])).as_posix(),
        sha256=str(entry["sha256"]),
        status=str(entry.get("status") or ""),
        mdt_status=str(entry.get("mdt_status") or ""),
    )
    return FoodSelectionRuntime(
        manifest_path=MANIFEST_PATH,
        asset_path=path,
        records=MappingProxyType(records),
        provenance=provenance,
    )


def clear_v4_food_selection_cache() -> None:
    load_v4_food_selection_metadata.cache_clear()


def _component_base_nutrition(component: Any, runtime: Any) -> dict[str, float | None]:
    """Calculate selector estimates only from V1.3 exact ingredient truth.

    Pending V1.3 sources deliberately return no estimate.  They remain
    selectable metadata candidates when no exact alternative exists, but they
    can never be promoted to exact nutrition by this adapter.
    """
    if not component.exact_nutrition_eligible:
        return {"energy_kcal": None, "protein_g": None, "carbohydrate_g": None, "fat_g": None}
    scale = 1.0 if 1.0 in component.allowed_scales else min(component.allowed_scales)
    totals = {"energy_kcal": 0.0, "protein_g": 0.0, "carbohydrate_g": 0.0, "fat_g": 0.0}
    for mapping in component.mappings_by_scale[scale]:
        ingredient = runtime.ingredient(mapping.ingredient_id)
        factor = float(mapping.executable_amount) / 100.0
        totals["energy_kcal"] += float(ingredient.energy_kcal_per100g or 0) * factor
        totals["protein_g"] += float(ingredient.protein_g_per100g or 0) * factor
        totals["carbohydrate_g"] += float(ingredient.carbohydrate_g_per100g or 0) * factor
        totals["fat_g"] += float(ingredient.fat_g_per100g or 0) * factor
    return {key: round(value, 4) for key, value in totals.items()}


def build_manifest_backed_food_catalog() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Merge V1.4 selection metadata with manifest-backed V1.3 execution data.

    The returned catalog is the compatibility shape consumed by the existing
    selector.  It contains no V1.7 fields and never copies V1.7 nutrition or
    amounts.
    """
    selection = load_v4_food_selection_metadata()
    from .v4_food_data import load_v4_food_data

    execution = load_v4_food_data()
    catalog: list[dict[str, Any]] = []
    for record in selection.records.values():
        component = execution.component(record.component_id)
        nutrition = _component_base_nutrition(component, execution)
        base_scale = 1.0 if 1.0 in component.allowed_scales else min(component.allowed_scales)
        mappings = component.mappings_by_scale[base_scale]
        ingredient_names = [mapping.ingredient_name for mapping in mappings]
        ingredient_amounts = [
            {"ingredient_id": mapping.ingredient_id, "ingredient_name": mapping.ingredient_name, "amount": mapping.executable_amount, "unit": mapping.unit}
            for mapping in mappings
        ]
        catalog.append({
            "component_id": record.component_id,
            "name": record.dish_name,
            "dish_name": record.dish_name,
            "meal_name": record.dish_name,
            "category": record.category,
            "subcategory": component.subcategory,
            "contraindications": component.contraindications,
            "meal_type": list(record.approved_meal_slots),
            "ingredients": ingredient_names,
            "ingredient_amounts": ingredient_amounts,
            "ingredient_name": ingredient_names,
            "ingredient_amount": ingredient_amounts,
            "portion_scale": base_scale,
            "portion_options": list(component.allowed_scales),
            "portion_min": min(component.allowed_scales),
            "portion_max": max(component.allowed_scales),
            # A singleton V1.3 scale is a fixed execution choice; expose an
            # explicit zero step for legacy compatibility without inventing a
            # second executable scale.
            "portion_step": min((b - a) for a, b in zip(component.allowed_scales, component.allowed_scales[1:])) if len(component.allowed_scales) > 1 else 0.0,
            "portion_boundary_source": "MDT_STANDARD_COMPONENT_EXECUTION_V1.3",
            "raw_or_cooked_basis": "execution_amount",
            "weight_basis": "execution_amount",
            "cooking_method": "按V1.3组件执行映射烹调",
            "brief_instructions": "按V1.3执行映射和医护审核份量执行。",
            "replacement_ids": list(record.approved_replacement_component_ids),
            "replacement_options": list(record.approved_replacement_component_ids),
            "breakfast_allowed": record.breakfast_allowed,
            "breakfast_priority": record.breakfast_priority,
            "approved_setting_tags": list(record.approved_setting_tags),
            "final_runtime_readiness": record.final_runtime_readiness,
            "final_execution_basis": record.final_execution_basis,
            "review_decision": record.review_decision,
            "replacement_review_decision": record.replacement_review_decision,
            "mdt_finalized": record.mdt_finalized,
            "execution_eligible": component.execution_eligible,
            "exact_nutrition_eligible": component.exact_nutrition_eligible,
            "nutrition_source_pending": component.nutrition_source_pending,
            "source_version": execution.asset_provenance.food_execution.version,
            "source_document": execution.food_source.name,
            "knowledge_version": SELECTION_VERSION,
            "selection_metadata_source_role": SELECTION_ROLE,
            "selection_metadata_source_version": SELECTION_VERSION,
            "selection_metadata_mdt_status": MDT_STATUS,
            **nutrition,
        })
    return catalog, selection.provenance.to_dict()
