import json
from pathlib import Path

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "v4_contract"


def _plan(fixture_id):
    fixture = json.loads((FIXTURE_DIR / f"SYN-{fixture_id}.json").read_text(encoding="utf-8"))
    payload = fixture["assessment_payload"]
    return build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())


def test_f01_base_and_final_pulmonary_snapshots_are_auditable():
    plan = _plan("F01")
    trace = plan["pulmonary_rehab_trace"]
    base = trace["base_pulmonary_before_f_overlay"]
    final = trace["final_pulmonary_after_f_overlay"]
    assert base["selected_action_ids"] == ["P01", "P02", "P05"]
    assert final["selected_action_ids"] == ["P01", "P02"]
    assert base["daily_action_ids"]["1"] == ["P01", "P02", "P05"]
    assert final["daily_action_ids"]["1"] == ["P01", "P02"]
    assert all(final["daily_action_ids"][str(day)] == ["P01", "P02"] for day in range(1, 8))


def test_f01_applies_only_optional_p05_task_load_reduction():
    trace = _plan("F01")["pulmonary_rehab_trace"]
    overlay = trace["pulmonary_complexity_overlay"]
    strategy = overlay["strategy"]["REDUCE_OPTIONAL_TASK_LOAD"]
    assert overlay["overlay"] == "F"
    assert overlay["applied"] is True
    assert strategy["applicability"] == "APPLIED"
    assert strategy["removed_or_deferred_action_ids"] == ["P05"]
    assert "PAIN_LIMITATION" in overlay["source_reasons"]
    assert "TIME_CONSTRAINT" in overlay["source_reasons"]
    assert "不知道怎么运动" not in overlay["source_reasons"]
    assert overlay["unsupported_strategies"]["dose_reduction"]["status"] == "NOT_APPLIED"
    assert overlay["unsupported_strategies"]["seated_or_supported"]["status"] == "NOT_APPLIED"
    assert overlay["unsupported_strategies"]["increased_supervision"]["status"] == "NOT_APPLIED"


def test_f01_p05_is_deferred_not_contraindicated_and_p01_p02_unchanged():
    trace = _plan("F01")["pulmonary_rehab_trace"]
    assert trace["p05_gate"] == {
        "selected": False,
        "mode": "NOT_SELECTED",
        "skill_learning": False,
        "clinical_need_for_clearance": False,
        "reason": "OPTIONAL_SKILL_LEARNING_DEFERRED_FOR_COMPLEXITY",
        "sputum_or_clearance_need": False,
        "dose_source_available": True,
    }
    assert trace["p05_gate"]["reason"] != "P05_CONTRAINDICATED"
    assert trace["final_pulmonary_after_f_overlay"]["dose"]["P01"] == trace["base_pulmonary_before_f_overlay"]["dose"]["P01"]
    assert trace["final_pulmonary_after_f_overlay"]["dose"]["P02"] == trace["base_pulmonary_before_f_overlay"]["dose"]["P02"]
    assert trace["p06_gate"] == trace["base_pulmonary_before_f_overlay"]["p06_gate"]


def test_f01_minimum_set_projection_and_full_trace():
    plan = _plan("F01")
    trace = plan["pulmonary_rehab_trace"]
    minimum = trace["minimum_sufficient_set"]
    assert minimum["selected_action_ids"] == ["P01", "P02"]
    assert minimum["omitted_action_ids"] == ["P03", "P04", "P05", "P06"]
    assert minimum["omission_reasons"]["P05"] == "OPTIONAL_SKILL_LEARNING_DEFERRED_FOR_COMPLEXITY"
    assert trace["trace_materialization_status"] == "FULL"
    assert trace["pulmonary_trace_full"] is True
    assert trace["trace_validation"]["status"] == "PASS"
    assert {item["pulmonary_id"] for item in plan["pulmonary_prehab_plan"]} == {"P01", "P02"}


def test_non_f_pulmonary_plans_keep_base_selection_and_p05():
    for fixture_id in ("A01", "B01", "C01", "D01", "E01"):
        trace = _plan(fixture_id)["pulmonary_rehab_trace"]
        assert trace["pulmonary_complexity_overlay"]["overlay"] == "none"
        assert trace["pulmonary_complexity_overlay"]["applied"] is False
        assert trace["selected_action_ids"] == ["P01", "P02", "P05"]
        assert trace["p05_gate"]["mode"] == "SKILL_LEARNING"
        assert trace["trace_materialization_status"] == "FULL"

