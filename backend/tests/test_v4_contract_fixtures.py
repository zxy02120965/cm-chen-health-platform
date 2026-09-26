"""Integrity tests for the separate V4 canonical regression fixture layer."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "v4_contract"
LEGACY_WORKBOOK = ROOT.parent / "docs" / "v2_upgrade_20260912" / "template" / "Q1-Q56_合成患者测试数据_A-F分型_18例.xlsx"
LEGACY_WORKBOOK_SHA256 = "FA92B8FD5BC943B6B83F6B43E410D4962E56DB1109C7C52424F9A5FEF1CE476A"

EXPECTED = {
    "SYN-A01": ("A", "none", "A", "GREEN", "PROVISIONAL", 1561, "EXACT_PROVISIONAL_REVIEW"),
    "SYN-B01": ("B", "none", "B", "YELLOW", "PROVISIONAL", 1840, "EXACT_PROVISIONAL_REVIEW"),
    "SYN-C01": ("C", "none", "C", "YELLOW", "PROVISIONAL", 1728, "EXACT_PROVISIONAL_REVIEW"),
    "SYN-D01": ("D", "none", "D", "YELLOW", "PROVISIONAL", 1660, "EXACT_PROVISIONAL_REVIEW"),
    "SYN-E01": ("E", "none", "E", "YELLOW", "UNAVAILABLE", None, "STRUCTURE_ONLY"),
    "SYN-F01": ("B", "F", "F", "YELLOW", "PROVISIONAL", 1446, "EXACT_PROVISIONAL_REVIEW"),
}


def _load(case_id):
    return json.loads((FIXTURE_DIR / f"{case_id}.json").read_text(encoding="utf-8"))


def test_six_v4_contract_fixtures_exist_and_are_unique():
    paths = sorted(FIXTURE_DIR.glob("SYN-*.json"))
    assert [p.stem for p in paths] == sorted(EXPECTED)
    fixtures = [_load(p.stem) for p in paths]
    assert len({fixture["fixture_id"] for fixture in fixtures}) == 6
    assert all(fixture["fixture_role"] == "V4_CANONICAL_CONTRACT_FIXTURE" for fixture in fixtures)
    assert all("expected_contract" not in fixture["assessment_payload"] for fixture in fixtures)


def test_expected_contract_values_are_frozen_and_energy_toleranced():
    for case_id, expected in EXPECTED.items():
        contract = _load(case_id)["expected_contract"]
        assert tuple(contract[key] for key in (
            "primary_nutrition_phenotype", "complexity_overlay", "display_phenotype", "safety_level",
            "energy_status", "provisional_energy_target_kcal", "diet_generation_mode",
        )) == expected
        if expected[5] is not None:
            assert abs(float(contract["provisional_energy_target_kcal"]) - expected[5]) <= 1.0
        assert contract["publication_blocked"] is True
    f01 = _load("SYN-F01")["expected_contract"]
    assert f01["primary_nutrition_phenotype"] == "B"
    assert f01["complexity_overlay"] == "F"
    e01 = _load("SYN-E01")["expected_contract"]
    assert e01["energy_status"] == "UNAVAILABLE"
    assert e01["diet_generation_mode"] == "STRUCTURE_ONLY"


def test_legacy_workbook_remains_present_and_byte_stable():
    assert LEGACY_WORKBOOK.exists()
    digest = hashlib.sha256(LEGACY_WORKBOOK.read_bytes()).hexdigest().upper()
    assert digest == LEGACY_WORKBOOK_SHA256

