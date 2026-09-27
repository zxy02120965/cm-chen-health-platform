"""Phase 3B-2B-1 minimal F overlay contract tests."""

import json
from pathlib import Path

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


FIXTURE = Path(__file__).parent / "fixtures" / "v4_contract" / "SYN-F01.json"


def _f_plan():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))["assessment_payload"]
    return build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())


def test_f_uses_underlying_b_template_and_preserves_overlay_identity():
    plan = _f_plan()
    trace = plan["exercise_plan_trace"]
    context = trace["context_snapshot"]
    assert plan["exercise_weekly_prescription"]["phenotype"] == "B"
    assert context["primary_nutrition_phenotype"] == "B"
    assert context["complexity_overlay"] == "F"
    assert context["display_phenotype"] == "F"
    assert trace["weekly_schedule_derived"]["resistance_days_actual"] == 2


def test_complexity_trace_separates_patient_burden_from_education_only():
    context = _f_plan()["exercise_plan_trace"]["context_snapshot"]
    overlay = context["complexity_overlay_trace"]
    assert overlay["overlay"] == "F"
    assert overlay["major_complexity_trigger_present"] is True
    assert overlay["material_execution_burden_present"] is True
    assert overlay["education_only"] is False
    assert "PAIN_LIMITATION" in overlay["trigger_reasons"]
    assert "TIME_CONSTRAINT" in overlay["trigger_reasons"]
    assert any(item["evidence_type"] == "education_only" for item in overlay["source_facts"])


def test_only_supported_minimal_strategies_are_applied():
    overlay = _f_plan()["exercise_plan_trace"]["context_snapshot"]["f_exercise_overlay"]
    strategies = overlay["strategies"]
    assert strategies["SPLIT_OR_SHORTEN"]["applicability"] == "APPLIED"
    assert strategies["SPLIT_OR_SHORTEN"]["affected_action_ids"]
    assert strategies["SLOW_PROGRESSION"]["applicability"] == "APPLIED"
    assert strategies["REDUCE_ACTION_COUNT"]["applicability"] == "NOT_APPLIED"
    assert strategies["SEATED_OR_SUPPORTED"]["applicability"] == "UNCERTAIN"
    assert strategies["REDUCE_COORDINATION_DEMAND"]["applicability"] == "UNCERTAIN"
    assert strategies["INCREASE_SUPERVISION"]["applicability"] == "UNCERTAIN"
    assert overlay["resistance_coverage"]["coverage_status"] == "ADEQUATE"


def test_f_overlay_has_before_after_audit_and_no_numeric_invention():
    trace = _f_plan()["exercise_plan_trace"]
    context = trace["context_snapshot"]
    overlay = context["f_exercise_overlay"]
    audit = overlay["before_after_audit"]
    assert audit["base"] != audit["final"]
    assert context["progression_policy"]["automatic_progression"] is False
    assert context["progression_policy"]["status"] == "HOLD_FOR_REVIEW"
    assert context["complexity_reduction"]["what_was_reduced"]["action_count"] is False
    assert trace["schedule_consistency_validation"]["status"] == "PASS"
    assert trace["trace_materialization_status"] == "FULL"
    for day in trace["daily_schedule"]:
        for session in day["sessions"]:
            for action in session["actions"]:
                if "f_overlay_adjustment" in action:
                    assert action["f_overlay_adjustment"]["original_allowed_range"]
                    assert action["f_overlay_adjustment"]["selected_dose"]
                    assert action["f_overlay_adjustment"]["selection_basis"].startswith("EXISTING_RANGE")
                assert action["progression_policy"]["automatic_progression"] is False


def test_non_f_overlay_is_not_applied():
    payload = json.loads((Path(__file__).parent / "fixtures" / "v4_contract" / "SYN-B01.json").read_text(encoding="utf-8"))["assessment_payload"]
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    context = plan["exercise_plan_trace"]["context_snapshot"]
    assert context["complexity_overlay"] == "none"
    assert context["f_exercise_overlay"]["applied"] is False
    assert all(item["applicability"] == "NOT_APPLIED" for item in context["f_exercise_overlay"]["strategies"].values())
