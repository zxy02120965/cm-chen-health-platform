"""Provenance contract tests for manifest-selected V4 food assets."""

from copy import deepcopy

import pytest

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile
import app.v4_food_data as food_data
from app.v4_diet_materialization import _materialize_item


def _golden_payload(case_id: str):
    pytest.importorskip("openpyxl")
    from test_v2_catalog_and_golden import _payload

    return _payload(case_id)


def test_provenance_matches_active_manifest_entries():
    runtime = food_data.load_v4_food_data()
    provenance = food_data.get_week1_food_asset_provenance()
    manifest = food_data._read_manifest()
    active = {entry["role"]: entry for entry in manifest["assets"] if entry.get("active") is True}

    assert provenance.to_dict() == runtime.asset_provenance.to_dict()
    assert provenance.manifest_relative_path == "backend/knowledge/zxy_week1/manifest.json"
    assert provenance.food_execution.to_dict() == {
        "role": active["MDT_STANDARD_COMPONENT_EXECUTION"]["role"],
        "version": active["MDT_STANDARD_COMPONENT_EXECUTION"]["version"],
        "relative_path": active["MDT_STANDARD_COMPONENT_EXECUTION"]["relative_path"],
        "sha256": active["MDT_STANDARD_COMPONENT_EXECUTION"]["sha256"],
    }
    assert provenance.ingredient_master.to_dict() == {
        "role": active["MDT_INGREDIENT_MASTER"]["role"],
        "version": active["MDT_INGREDIENT_MASTER"]["version"],
        "relative_path": active["MDT_INGREDIENT_MASTER"]["relative_path"],
        "sha256": active["MDT_INGREDIENT_MASTER"]["sha256"],
    }


def test_manifest_version_is_not_inferred_from_filename(monkeypatch):
    manifest = deepcopy(food_data._read_manifest())
    for entry in manifest["assets"]:
        if entry.get("active") and entry.get("role") in {"MDT_INGREDIENT_MASTER", "MDT_STANDARD_COMPONENT_EXECUTION"}:
            entry["version"] = "V9.9-test"
    monkeypatch.setattr(food_data, "_read_manifest", lambda: manifest)

    provenance = food_data.get_week1_food_asset_provenance()
    assert provenance.food_execution.version == "V9.9-test"
    assert provenance.ingredient_master.version == "V9.9-test"


def test_standard_component_trace_uses_active_asset_provenance():
    payload = _golden_payload("SYN-A01")
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    runtime = food_data.load_v4_food_data()
    trace = plan["diet_plan_trace"]

    assert trace["generation_context"]["asset_provenance"] == runtime.asset_provenance.to_dict()
    assert trace["generation_context"]["food_source"] == f"ZXY_WEEK1_V4_FREEZE/{runtime.asset_provenance.food_execution.version}"
    assert trace["trace_materialization_status"] == "FULL"
    item = next(
        item
        for day in trace["days"]
        for meal in day["meals"].values()
        for item in meal["food_items"]
        if item["food_item_type"] == "STANDARD_COMPONENT"
    )
    assert item["materialization_source"] == "COMPONENT_EXECUTION_MAPPING_V1_2"
    assert item["materialization_method"] == "COMPONENT_EXECUTION_MAPPING"
    assert item["source_version"] == runtime.asset_provenance.food_execution.version
    assert item["source_asset_role"] == runtime.asset_provenance.food_execution.role
    assert item["source_version"] != "V1.2"


@pytest.mark.parametrize("case_id", ["SYN-A01", "SYN-B01", "SYN-C01", "SYN-D01", "SYN-E01", "SYN-F01"])
def test_a01_to_f01_traces_use_active_provenance(case_id):
    payload = _golden_payload(case_id)
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    runtime = food_data.load_v4_food_data()
    trace = plan["diet_plan_trace"]
    assert trace["trace_materialization_status"] == "FULL"
    assert trace["generation_context"]["asset_provenance"] == runtime.asset_provenance.to_dict()
    assert trace["generation_context"]["food_source"].endswith(f"/{runtime.asset_provenance.food_execution.version}")


def test_ai_generated_dish_uses_ingredient_master_method_provenance():
    runtime = food_data.load_v4_food_data()
    item = _materialize_item(
        1,
        "snack",
        0,
        {
            "food_item_type": "AI_GENERATED_DISH",
            "generated_dish_id": "AI-PROV-001",
            "dish_name": "测试执行网格菜",
            "simple_method": "清蒸",
            "ingredients": [{"ingredient_id": "ING020", "algorithmic_amount": 100, "unit": "g"}],
        },
        energy_state={"diet_generation_mode": "EXACT_PROVISIONAL_REVIEW"},
        runtime=runtime,
    )
    assert item["materialization_method"] == "INGREDIENT_MASTER_EXECUTION_GRID"
    assert item["source_version"] == runtime.asset_provenance.ingredient_master.version
    assert item["source_asset_role"] == runtime.asset_provenance.ingredient_master.role
