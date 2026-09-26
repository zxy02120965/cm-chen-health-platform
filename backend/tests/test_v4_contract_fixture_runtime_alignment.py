"""Diagnostic runtime alignment checks; known gaps remain visible, not xfailed."""

import json
from pathlib import Path

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
        mismatches = [field for field in FIELDS if expected.get(field) != actual.get(field)]
        gap = fixture["known_contract_gap"]
        if mismatches:
            assert gap["present"] is True, (fixture["fixture_id"], mismatches)
            assert set(mismatches) == set(gap["fields"]), (fixture["fixture_id"], mismatches, gap)
            assert gap["resolution_status"] == "PENDING_RULE_ALIGNMENT"
        else:
            assert gap["present"] is False


def test_f01_runtime_mismatch_is_explicit_not_substituted_by_other_fixture():
    fixture = json.loads((FIXTURE_DIR / "SYN-F01.json").read_text(encoding="utf-8"))
    actual = _actual(fixture["assessment_payload"])
    assert actual["primary_nutrition_phenotype"] == "C"
    assert actual["complexity_overlay"] == "F"
    assert fixture["expected_contract"]["primary_nutrition_phenotype"] == "B"
    assert "primary_nutrition_phenotype" in fixture["known_contract_gap"]["fields"]

