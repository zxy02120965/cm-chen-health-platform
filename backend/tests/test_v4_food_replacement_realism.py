"""Phase 5B-8B replacement-chain and meal-realism regression coverage."""

import json
from pathlib import Path

from app.main import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile
from app.v4_food_replacement import _materialize_candidate, validate_replacement_root
from app.v4_food_selection import build_manifest_backed_food_catalog
from app.v4_food_realism import validate_meal_realism_root


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "v4_contract"


def _plan(fixture_id: str):
    payload = json.loads((FIXTURE_DIR / f"SYN-{fixture_id}.json").read_text(encoding="utf-8"))["assessment_payload"]
    return build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())


def test_approved_replacements_are_loaded_from_v14_and_unapproved_ids_are_not_invented():
    catalog, provenance = build_manifest_backed_food_catalog()
    by_id = {item["component_id"]: item for item in catalog}
    assert provenance["role"] == "FOOD_SELECTION_METADATA"
    assert by_id["P001"]["replacement_ids"] == ["P003", "P008"]
    assert by_id["P015"]["replacement_ids"] == []


def test_f01_root_contains_final_replacements_and_realism():
    plan = _plan("F01")
    root = plan["diet_plan_trace"]
    assert root["trace_materialization_status"] == "FULL"
    assert validate_replacement_root(root)["status"] == "PASS"
    assert validate_meal_realism_root(root)["status"] == "PASS"
    for day in root["days"]:
        breakfast_ids = {item["component_id"] for item in day["meals"]["breakfast"]["food_items"]}
        assert "P001" not in breakfast_ids
        assert "P005" not in breakfast_ids
        assert day["meals"]["breakfast"]["meal_realism"]["coherent_meal_structure"] is True
        assert all(
            replacement.get("replacement_for_component_id") in {item.get("component_id") for item in day["meals"]["breakfast"]["food_items"]}
            for replacement in [candidate for item in day["meals"]["breakfast"]["food_items"] for candidate in item.get("replacements") or []]
        )
        for meal in day["meals"].values():
            for item in meal["food_items"]:
                for replacement in item.get("replacements") or []:
                    assert replacement["replacement_component_id"] in {
                        candidate["replacement_component_id"]
                        for candidate in (item.get("replacements") or [])
                    }
                    if replacement["replacement_integrity"]["status"] == "PASS":
                        assert replacement["ingredients"]
                        assert replacement["component_portion_scale"] is not None
                        assert replacement["nutrition_recalculation_status"] in {"COMPLETED", "NOT_APPLICABLE"}


def test_plan_view_projects_replacements_and_meal_realism_from_root():
    plan = _plan("F01")
    root = plan["diet_plan_trace"]
    view = plan["plan_view"]["nutrition_plan"]
    assert view["replacement_integrity_validation"] == root["replacement_integrity_validation"]
    assert view["meal_realism_validation"] == root["meal_realism_validation"]
    root_item = root["days"][0]["meals"]["dinner"]["food_items"][0]
    projected_item = plan["weekly_schedule"][0]["diet"][3]["components"][0]
    assert projected_item["replacements"] == root_item["replacements"]


def test_source_pending_replacement_cannot_be_promoted_to_exact():
    catalog, _ = build_manifest_backed_food_catalog()
    by_id = {item["component_id"]: item for item in catalog}
    runtime = __import__("app.v4_food_data", fromlist=["load_v4_food_data"]).load_v4_food_data()
    source = dict(by_id["P014"])
    pending = dict(by_id["P015"])
    pending["approved_replacement_group"] = source["approved_replacement_group"]
    result = _materialize_candidate(pending, "P014", "breakfast", energy_state={"diet_generation_mode": "EXACT_PROVISIONAL_REVIEW"}, runtime=runtime)
    assert result["replacement_integrity"]["status"] == "SOURCE_PENDING"
    assert result["materialization_status"] == "NOT_MATERIALIZED"
    assert result["planned_nutrition"] is None


def test_old_root_without_new_fields_remains_backward_compatible():
    plan = _plan("A01")
    old_root = dict(plan["diet_plan_trace"])
    old_root.pop("replacement_integrity_validation", None)
    old_root.pop("meal_realism_validation", None)
    assert validate_replacement_root(old_root)["status"] == "PASS"
    assert validate_meal_realism_root(old_root)["status"] == "PASS"
