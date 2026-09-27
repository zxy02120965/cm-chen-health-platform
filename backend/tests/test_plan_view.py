"""Phase 5A-2 structured plan_view contract tests."""

from copy import deepcopy
import json
from pathlib import Path

from app.plan_view import PLAN_VIEW_KEYS, build_plan_view
from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "v4_contract"


def _plan(fixture_id: str):
    fixture = json.loads((FIXTURE_DIR / f"SYN-{fixture_id}.json").read_text(encoding="utf-8"))
    payload = fixture["assessment_payload"]
    return build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())


def test_a_to_f_have_exactly_the_same_ordered_11_keys():
    for fixture_id in ("A01", "B01", "C01", "D01", "E01", "F01"):
        view = _plan(fixture_id)["plan_view"]
        assert tuple(view) == PLAN_VIEW_KEYS
        assert len(view) == 11


def test_empty_modules_are_preserved():
    view = build_plan_view({})
    assert tuple(view) == PLAN_VIEW_KEYS
    assert view["weekly_goals"]["status"] == "PENDING"
    assert view["monitoring"]["status"] == "NOT_SCHEDULED"
    assert view["nutrition_plan"]["status"] == "MISSING"
    assert view["exercise_plan"]["status"] == "MISSING"
    assert view["pulmonary_rehab_plan"]["status"] == "MISSING"


def test_plan_view_mutation_does_not_mutate_canonical_roots():
    plan = _plan("F01")
    original_exercise = deepcopy(plan["exercise_plan_trace"])
    original_pulmonary = deepcopy(plan["pulmonary_rehab_trace"])
    original_diet = deepcopy(plan["diet_plan_trace"])

    view = plan["plan_view"]
    view["exercise_plan"]["days"][0]["sessions"].clear()
    view["pulmonary_rehab_plan"]["selected_action_ids"].clear()
    view["nutrition_plan"]["days"].clear()

    assert plan["exercise_plan_trace"] == original_exercise
    assert plan["pulmonary_rehab_trace"] == original_pulmonary
    assert plan["diet_plan_trace"] == original_diet


def test_e_exercise_roles_and_unavailable_energy_are_preserved():
    view = _plan("E01")["plan_view"]
    assert view["nutrition_basis"]["energy"]["status"] == "UNAVAILABLE"
    assert view["nutrition_basis"]["energy"]["candidate_kcal"] is None
    assert view["nutrition_basis"]["diet_generation_mode"] == "STRUCTURE_ONLY"
    derived = view["exercise_plan"]["weekly_summary"]["derived"]
    assert derived["formal_aerobic_days_actual"] == 0
    assert derived["functional_activity_days_actual"] == 7


def test_f_view_preserves_underlying_b_and_final_overlay_projections():
    plan = _plan("F01")
    view = plan["plan_view"]
    assert view["patient_summary"]["primary_nutrition_phenotype"] == "B"
    assert view["patient_summary"]["complexity_overlay"] == "F"
    assert view["patient_summary"]["display_phenotype"] == "F"
    assert view["pulmonary_rehab_plan"]["selected_action_ids"] == ["P01", "P02"]
    assert view["exercise_plan"]["patient_projection"] == plan["exercise_plan"]


def test_nutrition_basis_keeps_provisional_semantics():
    c_view = _plan("C01")["plan_view"]
    d_view = _plan("D01")["plan_view"]
    assert c_view["nutrition_basis"]["energy"]["status"] == "PROVISIONAL"
    assert c_view["nutrition_basis"]["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"
    assert d_view["nutrition_basis"]["energy"]["status"] == "PROVISIONAL"
    assert d_view["nutrition_basis"]["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"


def test_clinician_review_aggregates_governance_without_becoming_clinical_source():
    plan = _plan("F01")
    review = plan["plan_view"]["clinician_review"]
    assert review["publication_blocked"] is True
    assert review["publication_validation"] == "BLOCKED"
    assert review["audit"]["artifact_manifest_status"] == "PASS"
    assert "artifact_manifest" not in plan["plan_view"]["nutrition_plan"]


def test_plan_view_deterministic_for_a_to_f():
    for fixture_id in ("A01", "B01", "C01", "D01", "E01", "F01"):
        first = _plan(fixture_id)["plan_view"]
        second = _plan(fixture_id)["plan_view"]
        assert first == second


def test_legacy_top_level_compatibility_fields_remain_present():
    plan = _plan("A01")
    assert "diet_plan" in plan
    assert "exercise_plan" in plan
    assert "pulmonary_prehab_plan" in plan
    assert "weekly_schedule" in plan
    assert "plan_view" in plan
