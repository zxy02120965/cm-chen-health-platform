"""Root-derived artifact manifest contract tests."""

from copy import deepcopy
import json
from pathlib import Path

from app.artifact_manifest import build_artifact_manifest
from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "v4_contract"


def _plan(fixture_id: str):
    fixture = json.loads((FIXTURE_DIR / f"{fixture_id}.json").read_text(encoding="utf-8"))
    payload = fixture["assessment_payload"]
    return build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())


def test_manifest_is_derived_from_exactly_three_full_roots_for_a_to_f():
    for fixture_id in ("SYN-A01", "SYN-B01", "SYN-C01", "SYN-D01", "SYN-E01", "SYN-F01"):
        plan = _plan(fixture_id)
        manifest = plan["artifact_manifest"]
        assert manifest["derived_only_from"] == [
            "diet_plan_trace",
            "exercise_plan_trace",
            "pulmonary_rehab_trace",
        ]
        assert manifest["all_required_roots_present"] is True
        assert manifest["all_required_roots_full"] is True
        assert manifest["all_root_validators_pass"] is True
        assert manifest["status"] == "PASS"
        assert manifest["diet_trace"]["schema_version"] == "FOOD_TRACE_V4_2"
        assert manifest["exercise_trace"]["schema_version"] == "EXERCISE_TRACE_V4_2"
        assert manifest["pulmonary_trace"]["schema_version"] == "PULMONARY_TRACE_V4_2"
        assert all(manifest[key]["days_materialized"] == 7 for key in ("diet_trace", "exercise_trace", "pulmonary_trace"))
        assert plan["artifact_return"]["pulmonary_trace"] == {
            "present": True,
            "materialization": "FULL",
            "schema_version": "PULMONARY_TRACE_V4_2",
            "days_materialized": 7,
        }


def test_missing_diet_root_cannot_report_full():
    plan = _plan("SYN-A01")
    manifest = build_artifact_manifest(None, plan["exercise_plan_trace"], plan["pulmonary_rehab_trace"])
    assert manifest["diet_trace"]["present"] is False
    assert manifest["all_required_roots_full"] is False
    assert manifest["status"] == "FAIL"


def test_summary_only_exercise_root_cannot_report_full():
    plan = _plan("SYN-A01")
    exercise = deepcopy(plan["exercise_plan_trace"])
    exercise["trace_materialization_status"] = "SUMMARY_ONLY"
    manifest = build_artifact_manifest(plan["diet_plan_trace"], exercise, plan["pulmonary_rehab_trace"])
    assert manifest["exercise_trace"]["materialization"] == "SUMMARY_ONLY"
    assert manifest["all_required_roots_full"] is False
    assert manifest["status"] == "FAIL"


def test_missing_pulmonary_root_cannot_report_full():
    plan = _plan("SYN-A01")
    manifest = build_artifact_manifest(plan["diet_plan_trace"], plan["exercise_plan_trace"], None)
    assert manifest["pulmonary_trace"]["present"] is False
    assert manifest["all_required_roots_present"] is False
    assert manifest["status"] == "FAIL"


def test_root_validator_failure_fails_aggregate_manifest():
    plan = _plan("SYN-A01")
    pulmonary = deepcopy(plan["pulmonary_rehab_trace"])
    pulmonary["trace_validation"] = {"status": "FAIL"}
    manifest = build_artifact_manifest(plan["diet_plan_trace"], plan["exercise_plan_trace"], pulmonary)
    assert manifest["pulmonary_trace"]["validation_status"] == "FAIL"
    assert manifest["all_root_validators_pass"] is False
    assert manifest["status"] == "FAIL"


def test_manifest_full_does_not_override_publication_governance():
    plan = _plan("SYN-F01")
    assert plan["artifact_manifest"]["status"] == "PASS"
    assert plan["publication_blocked"] is True
    assert plan["publish_eligible"] is False


def test_manifest_mutation_does_not_change_patient_projections():
    plan = _plan("SYN-F01")
    exercise_ids = [item["exercise_id"] for item in plan["exercise_plan"]]
    pulmonary_ids = [item["pulmonary_id"] for item in plan["pulmonary_prehab_plan"]]
    diet_component_ids = [
        component.get("component_id")
        for meal in (plan["weekly_schedule"][0].get("diet") or [])
        for component in (meal.get("components") or [])
    ]

    plan["artifact_manifest"]["status"] = "FAIL"
    plan["artifact_manifest"]["diet_trace"]["materialization"] = "MISSING"

    assert [item["exercise_id"] for item in plan["exercise_plan"]] == exercise_ids
    assert [item["pulmonary_id"] for item in plan["pulmonary_prehab_plan"]] == pulmonary_ids
    assert [
        component.get("component_id")
        for meal in (plan["weekly_schedule"][0].get("diet") or [])
        for component in (meal.get("components") or [])
    ] == diet_component_ids


def test_patient_projections_remain_root_consistent():
    plan = _plan("SYN-F01")
    exercise_root_ids = {
        action.get("action_id")
        for day in plan["exercise_plan_trace"]["daily_schedule"]
        for session in day.get("sessions", [])
        for action in session.get("actions", [])
    }
    pulmonary_root_ids = {
        action.get("action_id")
        for day in plan["pulmonary_rehab_trace"]["daily_schedule"]
        for action in day.get("actions", [])
    }
    assert {item["exercise_id"] for item in plan["exercise_plan"]} <= exercise_root_ids
    assert {item["pulmonary_id"] for item in plan["pulmonary_prehab_plan"]} <= pulmonary_root_ids
    assert plan["artifact_manifest"]["status"] == "PASS"
