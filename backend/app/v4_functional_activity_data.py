"""Manifest-derived loader for the clinician-approved functional-activity asset.

This source is intentionally separate from the legacy V3 exercise catalogue.
It validates the FINAL V1.0 workbook and exposes immutable, provenance-aware
actions without inferring roles from names or categories.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .v4_food_data import ASSET_ROOT, MANIFEST_PATH, V4FoodDataError, _clean, _read_manifest, _read_xlsx_sheet, _records, _require_headers


FUNCTIONAL_ACTIVITY_ROLE = "FUNCTIONAL_ACTIVITY"
FUNCTIONAL_ACTIVITY_ASSET_ROLE = "FUNCTIONAL_ACTIVITY_ACTION_LIBRARY"
_ALLOWED_PARAMETER_ORIGINS = {"SOURCE_SUPPORTED", "CLINICIAN_APPROVED_PROJECT_PARAMETER"}
_REQUIRED_BY_SUBTYPE = {
    "BEDSIDE_MOBILITY": ("repetitions", "sets", "frequency", "position", "execution", "stop_conditions"),
    "FUNCTIONAL_TRANSFER": ("repetitions", "frequency", "execution", "stop_conditions"),
    "DAILY_ACTIVITY_MAINTENANCE": ("duration", "frequency", "intensity", "segmentation", "execution", "stop_conditions"),
}


class FunctionalActivityDataError(V4FoodDataError):
    """Raised when the active functional-activity asset is not executable."""


@dataclass(frozen=True)
class FunctionalActivityAssetProvenance:
    role: str
    version: str
    relative_path: str
    sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "version": self.version,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class FunctionalActivityAction:
    action_id: str
    action_name: str
    session_role: str
    functional_activity_subtype: str
    purpose: str
    population: str
    indications: str
    contraindications: str | None
    stop_conditions: str
    duration: str | None
    frequency: str
    additional_frequency: str | None
    optional_frequency: str | None
    intensity: str | None
    repetitions: str | None
    sets: str | None
    segmentation: str | None
    position: str | None
    execution: str
    progression: str | None
    source_document: str
    source_version: str
    source_asset_version: str
    source_location: str
    dose_source_status: str
    knowledge_status: str
    clinical_content_status: str
    mdt_confirmed: bool
    requires_clinical_review: bool
    clinical_review_status: str
    review_status: str
    review_decision: str
    approval_evidence_status: str
    parameter_origin: Mapping[str, str]
    source_asset: str

    def to_runtime_action(self) -> dict[str, Any]:
        """Convert to the adapter's action shape without legacy V3 identity."""
        return {
            "exercise_id": self.action_id,
            "action_id": self.action_id,
            "name": self.action_name,
            "action_name": self.action_name,
            "patient_display_name": self.action_name,
            "status": self.knowledge_status,
            "mdt_confirmed": self.mdt_confirmed,
            "session_role": FUNCTIONAL_ACTIVITY_ROLE,
            "functional_activity_subtype": self.functional_activity_subtype,
            "purpose": self.purpose,
            "population": self.population,
            "indications": self.indications,
            "contraindications": self.contraindications,
            "stop_conditions": self.stop_conditions,
            "duration_range": self.duration,
            "frequency": self.frequency,
            "additional_frequency": self.additional_frequency,
            "optional_frequency": self.optional_frequency,
            "intensity_range": self.intensity,
            "reps_range": self.repetitions,
            "sets_range": self.sets,
            "segmentation": self.segmentation,
            "position": self.position,
            "execution": self.execution,
            "progression": self.progression,
            "candidate_dose": self.duration or self.repetitions or self.frequency,
            "source_asset": self.source_asset,
            "source_version": self.source_version,
            "source_asset_version": self.source_asset_version,
            "source_document": self.source_document,
            "source_location": self.source_location,
            "knowledge_status": self.knowledge_status,
            "clinical_content_status": self.clinical_content_status,
            "clinical_review_status": self.clinical_review_status,
            "approval_evidence_status": self.approval_evidence_status,
            "parameter_origin": dict(self.parameter_origin),
            "dose_source_status": self.dose_source_status,
            "requires_clinical_review": self.requires_clinical_review,
            "reviewer": None,
            "review_date": None,
        }


@dataclass(frozen=True)
class FunctionalActivityRuntime:
    asset_provenance: FunctionalActivityAssetProvenance
    actions: Mapping[str, FunctionalActivityAction]

    def action(self, action_id: str) -> FunctionalActivityAction:
        try:
            return self.actions[str(action_id)]
        except KeyError:
            raise FunctionalActivityDataError(f"unknown functional activity action: {action_id}") from None


def _active_entry() -> dict[str, Any]:
    manifest = _read_manifest()
    entries = [
        asset for asset in manifest.get("assets", [])
        if asset.get("active") is True and asset.get("role") == FUNCTIONAL_ACTIVITY_ASSET_ROLE
    ]
    if len(entries) != 1:
        raise FunctionalActivityDataError(
            f"manifest must contain exactly one active {FUNCTIONAL_ACTIVITY_ASSET_ROLE} asset"
        )
    entry = entries[0]
    path = ASSET_ROOT / str(entry.get("relative_path") or "")
    if not path.is_file():
        raise FunctionalActivityDataError(f"missing functional activity asset: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != str(entry.get("sha256") or "").lower():
        raise FunctionalActivityDataError(f"functional activity asset SHA256 mismatch: {path}")
    return entry


def get_functional_activity_asset_provenance(entry: Mapping[str, Any] | None = None) -> FunctionalActivityAssetProvenance:
    entry = dict(entry) if entry is not None else _active_entry()
    return FunctionalActivityAssetProvenance(
        role=str(entry["role"]),
        version=str(entry["version"]),
        relative_path=Path(str(entry["relative_path"])).as_posix(),
        sha256=str(entry["sha256"]).lower(),
    )


def _required_value(record: Mapping[str, Any], field: str, action_id: str) -> str:
    value = _clean(record.get(field))
    if value is None:
        raise FunctionalActivityDataError(f"{action_id} missing required parameter: {field}")
    return str(value)


def _load_runtime() -> FunctionalActivityRuntime:
    entry = _active_entry()
    path = ASSET_ROOT / str(entry["relative_path"])
    rows = _read_xlsx_sheet(path, "Functional_Activity_Final")
    # Five metadata rows precede the structured action header in the FINAL
    # workbook. Keep the parser aligned with that actual sheet layout.
    headers, records = _records(rows, header_row=5)
    _require_headers(
        headers,
        (
            "action_id", "action_name", "session_role", "functional_activity_subtype", "purpose",
            "population", "indications", "stop_conditions", "frequency", "execution", "source_document",
            "source_version", "source_location", "knowledge_status", "clinical_content_status",
            "mdt_confirmed", "requires_clinical_review", "clinical_review_status", "review_status",
            "review_decision", "approval_evidence_status", "parameter_origin", "reviewer", "review_date",
        ),
        "Functional_Activity_Final",
    )
    # Keep the parsed manifest entry used for selection, hash validation, and
    # provenance.  This prevents data and audit metadata from drifting apart.
    provenance = get_functional_activity_asset_provenance(entry)
    actions: dict[str, FunctionalActivityAction] = {}
    for record in records:
        action_id = str(_clean(record.get("action_id")) or "")
        if not action_id:
            raise FunctionalActivityDataError("functional activity asset contains empty action_id")
        if action_id in actions:
            raise FunctionalActivityDataError(f"duplicate functional activity action_id: {action_id}")
        role = str(_clean(record.get("session_role")) or "")
        subtype = str(_clean(record.get("functional_activity_subtype")) or "")
        if role != FUNCTIONAL_ACTIVITY_ROLE:
            raise FunctionalActivityDataError(f"{action_id} has invalid session_role: {role}")
        if subtype not in _REQUIRED_BY_SUBTYPE:
            raise FunctionalActivityDataError(f"{action_id} has invalid functional_activity_subtype: {subtype}")
        for field in _REQUIRED_BY_SUBTYPE[subtype]:
            _required_value(record, field, action_id)
        if str(_clean(record.get("knowledge_status")) or "") != "ACTIVE":
            raise FunctionalActivityDataError(f"{action_id} is not ACTIVE")
        if str(_clean(record.get("clinical_review_status")) or "") != "APPROVED":
            raise FunctionalActivityDataError(f"{action_id} clinical_review_status is not APPROVED")
        if str(_clean(record.get("review_decision")) or "") != "APPROVE":
            raise FunctionalActivityDataError(f"{action_id} review_decision is not APPROVE")
        if str(_clean(record.get("clinical_content_status")) or "") != "CLINICIAN_APPROVED":
            raise FunctionalActivityDataError(f"{action_id} clinical_content_status is not CLINICIAN_APPROVED")
        if str(_clean(record.get("approval_evidence_status")) or "") != "USER_CONFIRMED_CLINICIAN_REVIEW":
            raise FunctionalActivityDataError(f"{action_id} approval evidence is invalid")
        if str(_clean(record.get("review_status")) or "") != "APPROVED":
            raise FunctionalActivityDataError(f"{action_id} review_status is not APPROVED")
        if record.get("mdt_confirmed") is not False or record.get("requires_clinical_review") is not False:
            raise FunctionalActivityDataError(f"{action_id} has invalid approval flags")
        if _clean(record.get("reviewer")) is not None or _clean(record.get("review_date")) is not None:
            raise FunctionalActivityDataError(f"{action_id} must not fabricate reviewer/date")
        try:
            parameter_origin = json.loads(str(record.get("parameter_origin") or "{}"))
        except json.JSONDecodeError as exc:
            raise FunctionalActivityDataError(f"{action_id} parameter_origin is invalid JSON") from exc
        if not isinstance(parameter_origin, dict) or not parameter_origin:
            raise FunctionalActivityDataError(f"{action_id} parameter_origin is empty")
        if set(parameter_origin.values()) - _ALLOWED_PARAMETER_ORIGINS:
            raise FunctionalActivityDataError(f"{action_id} has unsupported parameter origin")
        source_version = str(_clean(record.get("source_version")) or "")
        source_document = str(_clean(record.get("source_document")) or "")
        if not source_version or not source_document:
            raise FunctionalActivityDataError(f"{action_id} missing source provenance")
        actions[action_id] = FunctionalActivityAction(
            action_id=action_id,
            action_name=_required_value(record, "action_name", action_id),
            session_role=role,
            functional_activity_subtype=subtype,
            purpose=_required_value(record, "purpose", action_id),
            population=_required_value(record, "population", action_id),
            indications=_required_value(record, "indications", action_id),
            contraindications=_clean(record.get("contraindications")),
            stop_conditions=_required_value(record, "stop_conditions", action_id),
            duration=_clean(record.get("duration")),
            frequency=_required_value(record, "frequency", action_id),
            additional_frequency=_clean(record.get("additional_frequency")),
            optional_frequency=_clean(record.get("optional_frequency")),
            intensity=_clean(record.get("intensity")),
            repetitions=_clean(record.get("repetitions")),
            sets=_clean(record.get("sets")),
            segmentation=_clean(record.get("segmentation")),
            position=_clean(record.get("position")),
            execution=_required_value(record, "execution", action_id),
            progression=_clean(record.get("progression")),
            source_document=source_document,
            source_version=source_version,
            source_asset_version=provenance.version,
            source_location=_required_value(record, "source_location", action_id),
            dose_source_status=str(_clean(record.get("dose_source_status")) or ""),
            knowledge_status="ACTIVE",
            clinical_content_status="CLINICIAN_APPROVED",
            mdt_confirmed=False,
            requires_clinical_review=False,
            clinical_review_status="APPROVED",
            review_status="APPROVED",
            review_decision="APPROVE",
            approval_evidence_status="USER_CONFIRMED_CLINICIAN_REVIEW",
            parameter_origin=MappingProxyType(dict(parameter_origin)),
            source_asset=provenance.relative_path,
        )
    if len(actions) != 5:
        raise FunctionalActivityDataError(f"expected 5 functional activity actions, got {len(actions)}")
    return FunctionalActivityRuntime(asset_provenance=provenance, actions=MappingProxyType(actions))


@lru_cache(maxsize=1)
def load_functional_activity_data() -> FunctionalActivityRuntime:
    return _load_runtime()


def clear_functional_activity_data_cache() -> None:
    load_functional_activity_data.cache_clear()


def select_e_deferred_functional_activity(
    *, payload: Mapping[str, Any], safety_level: str, eligibility: Mapping[str, Any]
) -> tuple[list[FunctionalActivityAction], dict[str, Any]]:
    """Select a minimal metadata-matched action set for deferred E patients."""
    if str(eligibility.get("status")) != "DEFERRED_FOR_NUTRITION_RECOVERY":
        return [], {"status": "NOT_ELIGIBLE", "selected_action_ids": [], "reason_codes": ["E_FORMAL_AEROBIC_NOT_DEFERRED"]}
    if str(safety_level).upper() == "RED":
        return [], {"status": "SAFETY_BLOCKED", "selected_action_ids": [], "reason_codes": ["SAFETY_RED_BLOCKS_FUNCTIONAL_ACTIVITY"]}
    runtime = load_functional_activity_data()
    payload_text = " ".join(str(value) for value in payload.values())
    candidates: list[FunctionalActivityAction] = []
    for action in runtime.actions.values():
        metadata = " ".join((action.functional_activity_subtype, action.purpose, action.population, action.indications))
        if action.functional_activity_subtype != "DAILY_ACTIVITY_MAINTENANCE":
            continue
        if "E型" not in metadata and "功能活动" not in metadata:
            continue
        if action.contraindications and any(token in payload_text for token in ("跌倒", "无法行走")):
            continue
        candidates.append(action)
    if not candidates:
        provenance = runtime.asset_provenance.to_dict()
        return [], {
            "status": "UNAVAILABLE",
            "selected_action_ids": [],
            "reason_codes": ["FUNCTIONAL_ACTIVITY_SOURCE_UNAVAILABLE"],
            "source_asset": provenance,
            "asset_name": Path(provenance["relative_path"]).name,
            "asset_version": provenance["version"],
        }
    selected = [sorted(candidates, key=lambda item: (item.functional_activity_subtype, item.action_id))[0]]
    provenance = runtime.asset_provenance.to_dict()
    return selected, {
        "status": "MATERIALIZED",
        "selected_action_ids": [action.action_id for action in selected],
        "reason_codes": [],
        "source_asset": provenance,
        "asset_name": Path(provenance["relative_path"]).name,
        "asset_version": provenance["version"],
        "source_version": provenance["version"],
        "asset_role": provenance["role"],
        "asset_sha256": provenance["sha256"],
        "knowledge_status": "ACTIVE",
        "clinical_review_status": "APPROVED",
        "approval_evidence_status": "USER_CONFIRMED_CLINICIAN_REVIEW",
        "mdt_confirmed": False,
    }
