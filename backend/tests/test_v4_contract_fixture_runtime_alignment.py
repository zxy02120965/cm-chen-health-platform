"""Diagnostic runtime alignment checks; known gaps remain visible, not xfailed."""

import json
from pathlib import Path

import pytest

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "v4_contract"
FIELDS = (
    "primary_nutrition_phenotype", "complexity_overlay", "display_phenotype", "safety_level",
    "energy_status", "provisional_energy_target_kcal", "diet_generation_mode", "publication_blocked",
)


def _actual(payload):
    evaluation = assess_payload(payload)
    plan = build_v2_plan(payload, evaluation, active_configs=candidate_test_profile())
    energy = plan["energy_state"]["energy_target"]
    return {
        "primary_nutrition_phenotype": plan["primary_nutrition_phenotype"],
        "complexity_overlay": plan["complexity_overlay"],
        "display_phenotype": plan["display_phenotype"],
        "safety_level": str(evaluation["safety"]).upper(),
        "energy_status": energy["status"],
        "provisional_energy_target_kcal": energy.get("provisional_energy_target_kcal"),
        "diet_generation_mode": plan["energy_state"]["diet_generation_mode"],
        "publication_blocked": plan["publication_blocked"],
    }


def test_runtime_alignment_reports_known_gaps_explicitly():
    for path in sorted(FIXTURE_DIR.glob("SYN-*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        expected = fixture["expected_contract"]
        actual = _actual(fixture["assessment_payload"])
        mismatches = []
        for field in FIELDS:
            if field == "provisional_energy_target_kcal" and expected.get(field) is not None and actual.get(field) is not None:
                if abs(float(expected[field]) - float(actual[field])) <= 5.0:
                    continue
            if expected.get(field) != actual.get(field):
                mismatches.append(field)
        gap = fixture["known_contract_gap"]
        if mismatches:
            assert gap["present"] is True, (fixture["fixture_id"], mismatches)
            assert set(mismatches) == set(gap["fields"]), (fixture["fixture_id"], mismatches, gap)
            assert gap["resolution_status"] == "PENDING_MDT_SAFETY_ALIGNMENT"
        else:
            assert gap["present"] is False
            if fixture["fixture_id"] in {"SYN-C01", "SYN-D01", "SYN-F01"}:
                assert gap["resolution_status"] == "SAFETY_CONTRACT_ALIGNED"
        if expected["provisional_energy_target_kcal"] is not None:
            assert abs(float(actual["provisional_energy_target_kcal"]) - float(expected["provisional_energy_target_kcal"])) <= 5.0
        assert actual["publication_blocked"] is True


def test_f01_runtime_preserves_underlying_b_and_f_overlay():
    fixture = json.loads((FIXTURE_DIR / "SYN-F01.json").read_text(encoding="utf-8"))
    actual = _actual(fixture["assessment_payload"])
    assert actual["primary_nutrition_phenotype"] == "B"
    assert actual["complexity_overlay"] == "F"
    assert actual["display_phenotype"] == "F"
    assert fixture["expected_contract"]["primary_nutrition_phenotype"] == "B"
    assert fixture["known_contract_gap"]["present"] is False
    assert fixture["known_contract_gap"]["resolution_status"] == "SAFETY_CONTRACT_ALIGNED"


def test_canonical_provisional_energy_uses_p3_and_q35_candidate_pal():
    expected = {
        "SYN-A01": (1.35, 0.85, 1561),
        "SYN-B01": (1.30, 0.80, 1840),
        "SYN-C01": (1.35, 1.00, 1728),
        "SYN-D01": (1.35, 1.10, 1660),
        "SYN-F01": (1.30, 0.80, 1446),
    }
    for fixture_id, (pal, ratio, target) in expected.items():
        fixture = json.loads((FIXTURE_DIR / f"{fixture_id}.json").read_text(encoding="utf-8"))
        evaluation = assess_payload(fixture["assessment_payload"])
        plan = build_v2_plan(fixture["assessment_payload"], evaluation, active_configs=candidate_test_profile())
        trace = plan["energy_calculation"]
        assert trace["ree_source"] == "P3_BIA_BMR_TEMP"
        assert trace["primary_energy_source"] == "P3_BIA_BMR_TEMP"
        assert trace["p2_primary_eligible"] is False
        assert trace["pal"] == pal
        assert trace["pal_source"] == "Q27_FUNCTIONAL_CAPACITY_CANDIDATE_MAPPING"
        assert trace["prescription_ratio"] == ratio
        assert plan["publication_blocked"] is True
        assert plan["energy_state"]["energy_target"]["provisional_energy_target_kcal"] == pytest.approx(target, abs=5.0)
