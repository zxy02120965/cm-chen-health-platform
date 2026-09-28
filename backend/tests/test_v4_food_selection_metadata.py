"""Regression coverage for the manifest-backed MDT FOOD selection asset."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile
from app.v4_food_selection import (
    V4FoodSelectionError,
    clear_v4_food_selection_cache,
    load_v4_food_selection_metadata,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "v4_contract"


def _fixture_payload(name: str) -> dict:
    return json.loads((FIXTURE_DIR / f"SYN-{name}.json").read_text(encoding="utf-8"))["assessment_payload"]


def _f01_plan() -> dict:
    payload = _fixture_payload("F01")
    return build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())


def test_manifest_backed_selection_asset_is_v14_and_complete():
    runtime = load_v4_food_selection_metadata()
    assert runtime.provenance.role == "FOOD_SELECTION_METADATA"
    assert runtime.provenance.version == "V1.4"
    assert runtime.provenance.status == "ACTIVE"
    assert runtime.provenance.mdt_status == "MDT_APPROVED_FINAL"
    assert len(runtime.records) == 49
    assert all(record.mdt_finalized for record in runtime.records.values())


def test_selection_asset_fails_closed_when_manifest_asset_is_missing(monkeypatch, tmp_path):
    import app.v4_food_selection as selection

    manifest = {
        "assets": [{
            "role": "FOOD_SELECTION_METADATA",
            "active": True,
            "version": "V1.4",
            "status": "ACTIVE",
            "mdt_status": "MDT_APPROVED_FINAL",
            "relative_path": "data/missing-selection.json",
            "sha256": "0" * 64,
        }]
    }
    monkeypatch.setattr(selection, "_read_manifest", lambda: manifest)
    clear_v4_food_selection_cache()
    with pytest.raises(V4FoodSelectionError, match="missing manifest selection asset"):
        load_v4_food_selection_metadata()
    clear_v4_food_selection_cache()


def test_selection_asset_fails_closed_on_sha_mismatch(monkeypatch):
    import app.v4_food_selection as selection

    manifest = copy.deepcopy(selection._read_manifest())
    entry = next(item for item in manifest["assets"] if item.get("role") == "FOOD_SELECTION_METADATA")
    entry["sha256"] = "0" * 64
    monkeypatch.setattr(selection, "_read_manifest", lambda: manifest)
    clear_v4_food_selection_cache()
    with pytest.raises(V4FoodSelectionError, match="SHA256 mismatch"):
        load_v4_food_selection_metadata()
    clear_v4_food_selection_cache()


def test_candidate_profile_uses_v14_selection_and_v13_execution_truth():
    profile = candidate_test_profile()
    selection = profile["FOOD_SELECTION_METADATA"]
    foods = profile["V2-FOOD-COMPONENTS"]["items"]
    assert selection["role"] == "FOOD_SELECTION_METADATA"
    assert selection["version"] == "V1.4"
    assert selection["provenance"]["manifest_registered"] is True
    assert len(foods) == 49
    assert {item["selection_metadata_source_version"] for item in foods} == {"V1.4"}
    assert {item["source_version"] for item in foods} == {"V1.3"}
    assert all("V1.7" not in str(item.get("source_document")) for item in foods)


def test_v14_meal_slots_and_breakfast_priority_are_consumed():
    profile = candidate_test_profile()
    foods = {item["component_id"]: item for item in profile["V2-FOOD-COMPONENTS"]["items"]}
    assert "breakfast" not in foods["P001"]["meal_type"]
    assert foods["P001"]["breakfast_allowed"] == "NO"
    assert "breakfast" not in foods["P005"]["meal_type"]
    assert foods["P005"]["breakfast_allowed"] == "NO"
    assert "breakfast" in foods["P014"]["meal_type"]
    assert foods["P014"]["breakfast_priority"] == "PREFERRED"


def test_v14_breakfast_slot_contract_survives_replacement_search():
    for fixture_id in ("A01", "B01", "C01", "D01", "E01", "F01"):
        payload = _fixture_payload(fixture_id)
        plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
        breakfast_ids = {
            item["component_id"]
            for day in plan["canonical_week_diet"]["days"]
            for item in day["meals"]["breakfast"].get("food_items", [])
        }
        assert "P001" not in breakfast_ids
        assert "P005" not in breakfast_ids


def test_p015_breakfast_suitability_does_not_bypass_v13_execution_gate():
    profile = candidate_test_profile()
    p015 = next(item for item in profile["V2-FOOD-COMPONENTS"]["items"] if item["component_id"] == "P015")
    assert "breakfast" in p015["meal_type"]
    assert p015["breakfast_allowed"] == "YES"
    assert p015["breakfast_priority"] == "PREFERRED"
    assert p015["exact_nutrition_eligible"] is False
    assert p015["execution_eligible"] is True
    assert p015["nutrition_source_pending"] is True
    assert p015["final_execution_basis"] == "V1.3_EXECUTION_TRUTH"

    plan = _f01_plan()
    breakfasts = []
    for day in plan["canonical_week_diet"]["days"]:
        breakfast = day["meals"]["breakfast"]
        breakfasts.extend(item["component_id"] for item in breakfast.get("food_items", []))
    assert "P015" not in breakfasts


def test_approved_replacements_are_loaded_but_unapproved_remain_empty():
    runtime = load_v4_food_selection_metadata()
    assert sum(bool(record.approved_replacement_component_ids) for record in runtime.records.values()) == 38
    assert sum(not record.approved_replacement_component_ids for record in runtime.records.values()) == 11
    assert runtime.record("C001").approved_replacement_component_ids == ("C002", "C003", "C005")
    assert runtime.record("P001").approved_replacement_component_ids == ("P003", "P008")
    assert runtime.record("P015").approved_replacement_component_ids == ()
    assert runtime.record("S009").approved_replacement_component_ids == ()


def test_f_overlay_consumes_v14_selection_source_and_preserves_b_direction():
    plan = _f01_plan()
    assert plan["primary_nutrition_phenotype"] == "B"
    assert plan["complexity_overlay"] == "F"
    trace = plan["nutrition_trace"]
    assert trace["food_selection_source"]["role"] == "FOOD_SELECTION_METADATA"
    assert trace["food_selection_source"]["version"] == "V1.4"
    assert plan["canonical_week_diet"]["generation_context"]["food_selection_source"]["version"] == "V1.4"
    assert plan["canonical_week_diet"]["generation_context"]["execution_source"]["version"] == "V1.3"
    assert plan["canonical_week_diet"]["generation_context"]["ingredient_source"]["version"] == "V1.3"
