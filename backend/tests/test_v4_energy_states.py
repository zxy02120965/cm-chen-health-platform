from copy import deepcopy

import pytest

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile
from app.v4_contract import derive_v4_phenotype
from app.v4_energy_state import derive_energy_state, validate_energy_state


def _contract(primary="B", overlay="none", display=None):
    return {
        "primary_nutrition_phenotype": primary,
        "complexity_overlay": overlay,
        "display_phenotype": display or ("F" if overlay == "F" else primary),
    }


def _trace(target=1800.0, *, bia=1390.0, pal=1.3, ratio=0.8, mdt=False):
    return {
        "bia_bmr": bia,
        "pal": pal,
        "tee_base": round(bia * pal, 1) if bia is not None and pal is not None else None,
        "prescription_ratio": ratio,
        "daily_energy_target_kcal": target,
        "mdt_confirmed": mdt,
        "energy_estimation_conflict": False,
    }


def test_active_maps_to_exact_active():
    state = derive_energy_state(
        phenotype_contract=_contract(),
        energy_trace=_trace(target=1800, mdt=True),
        active_configs={
            "V2-REE-FORMULA": {"status": "ACTIVE"},
            "V2-PAL-RULE": {"status": "ACTIVE"},
        },
    )
    assert state["energy_target"]["status"] == "ACTIVE"
    assert state["diet_generation_mode"] == "EXACT_ACTIVE"
    assert state["energy_target"]["prescribed_energy_target_kcal"] == 1800


def test_provisional_maps_to_exact_provisional_review():
    state = derive_energy_state(
        phenotype_contract=_contract("B"),
        energy_trace=_trace(target=1446, bia=1390, pal=1.3, ratio=0.8),
        active_configs={"V2-PAL-RULE": {"status": "CANDIDATE"}},
    )
    assert state["energy_target"]["status"] == "PROVISIONAL"
    assert state["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"
    assert state["energy_target"]["prescribed_energy_target_kcal"] is None
    assert state["energy_target"]["provisional_energy_target_kcal"] == 1446


def test_syn_a01_v4_provisional_energy_regression_lock():
    payload = {
        "height_cm": 165,
        "weight_kg": 70,
        "q14_height": 165,
        "q15_weight": 70,
        "q43_metabolicConditions": ["无"],
    }
    contract = derive_v4_phenotype(payload)
    state = derive_energy_state(
        phenotype_contract=contract,
        energy_trace=_trace(target=None, bia=1360, pal=1.35, ratio=0.85),
        active_configs={"V2-PAL-RULE": {"status": "CANDIDATE"}},
    )
    assert contract["primary_nutrition_phenotype"] == "A"
    assert contract["complexity_overlay"] == "none"
    assert state["energy_target"]["status"] == "PROVISIONAL"
    assert state["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"
    assert state["energy_target"]["prescribed_energy_target_kcal"] is None
    assert state["energy_target"]["provisional_energy_target_kcal"] == pytest.approx(1560.6, abs=0.1)


def test_syn_b01_v4_provisional_energy_regression_lock():
    payload = {
        "height_cm": 165,
        "weight_kg": 90,
        "q14_height": 165,
        "q15_weight": 90,
        "q43_metabolicConditions": ["糖尿病"],
    }
    contract = derive_v4_phenotype(payload)
    state = derive_energy_state(
        phenotype_contract=contract,
        energy_trace=_trace(target=None, bia=1770, pal=1.30, ratio=0.80),
        active_configs={"V2-PAL-RULE": {"status": "CANDIDATE"}},
    )
    assert contract["primary_nutrition_phenotype"] == "B"
    assert contract["complexity_overlay"] == "none"
    assert state["energy_target"]["status"] == "PROVISIONAL"
    assert state["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"
    assert state["energy_target"]["prescribed_energy_target_kcal"] is None
    assert state["energy_target"]["provisional_energy_target_kcal"] == pytest.approx(1840.8, abs=0.1)


def test_unavailable_maps_to_structure_only():
    state = derive_energy_state(
        phenotype_contract=_contract("E"),
        energy_trace=_trace(target=None, bia=None, pal=None),
        active_configs={},
    )
    assert state["energy_target"]["status"] == "UNAVAILABLE"
    assert state["diet_generation_mode"] == "STRUCTURE_ONLY"
    assert state["energy_target"]["provisional_energy_target_kcal"] is None


def test_f01_keeps_b_underlying_chain_and_candidate_energy():
    state = derive_energy_state(
        phenotype_contract=_contract("B", "F", "F"),
        energy_trace=_trace(target=1446, bia=1390, pal=1.3, ratio=0.8),
        active_configs={"V2-PAL-RULE": {"status": "CANDIDATE"}},
        safety_level="yellow",
    )
    assert state["energy_target"]["status"] == "PROVISIONAL"
    assert state["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"
    assert state["energy_target"]["provisional_energy_target_kcal"] == 1446


def test_c01_and_d01_provisional_are_not_structure_only():
    for primary in ("C", "D"):
        state = derive_energy_state(
            phenotype_contract=_contract(primary),
            energy_trace=_trace(target=1660 if primary == "D" else 1728),
            active_configs={"V2-PAL-RULE": {"status": "CANDIDATE"}},
        )
        assert state["energy_target"]["status"] == "PROVISIONAL"
        assert state["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"


def test_e01_severe_decline_is_structure_only_even_with_bia_candidate():
    state = derive_energy_state(
        phenotype_contract=_contract("E"),
        energy_trace=_trace(target=1541, bia=1340, pal=1.3, ratio=1.15),
        payload={"q28_weightChange": "不明原因下降", "q30_intake": "减少50%"},
        active_configs={"V2-PAL-RULE": {"status": "CANDIDATE"}},
    )
    assert state["energy_target"]["status"] == "UNAVAILABLE"
    assert state["diet_generation_mode"] == "STRUCTURE_ONLY"


@pytest.mark.parametrize(
    "status,mode",
    [
        ("PROVISIONAL", "EXACT_ACTIVE"),
        ("PROVISIONAL", "STRUCTURE_ONLY"),
        ("UNAVAILABLE", "EXACT_PROVISIONAL_REVIEW"),
        ("UNAVAILABLE", "EXACT_ACTIVE"),
        ("ACTIVE", "STRUCTURE_ONLY"),
    ],
)
def test_illegal_energy_state_combinations_fail(status, mode):
    state = {
        "energy_target": {
            "status": status,
            "prescribed_energy_target_kcal": 1800 if status == "ACTIVE" else None,
            "provisional_energy_target_kcal": 1800 if status == "PROVISIONAL" else None,
        },
        "diet_generation_mode": mode,
    }
    with pytest.raises(ValueError):
        validate_energy_state(state)


def test_build_plan_exposes_v4_contract_without_changing_legacy_display_field():
    payload = {
        "sex": "女", "height_cm": 158, "weight_kg": 78,
        "q14_height": 158, "q15_weight": 78, "q22_bmr": 1390,
        "q12_respiratorySymptoms": ["无"], "q28_weightChange": "稳定",
        "q29_appetite": "正常", "q30_intake": "正常",
        "q31_eatingDifficulties": ["无"], "q32_foodAllergy": ["无"],
        "q43_metabolicConditions": ["高血压", "糖尿病", "血脂异常", "睡眠呼吸暂停"],
        "q51_executionBarriers": ["不会操作设备"],
    }
    evaluation = assess_payload(payload)
    configs = candidate_test_profile()
    configs["V2-PAL-RULE"] = {"status": "CANDIDATE", "default": 1.3}
    plan = build_v2_plan(payload, evaluation, active_configs=configs)
    assert plan["primary_nutrition_phenotype"] == "B"
    assert plan["complexity_overlay"] == "F"
    assert plan["display_phenotype"] == "F"
    assert plan["energy_state"]["diet_generation_mode"] == "EXACT_PROVISIONAL_REVIEW"
    assert plan["energy_state"]["energy_target"]["provisional_energy_target_kcal"] == pytest.approx(1446.0, abs=0.5)


def test_yellow_is_not_converted_to_red_by_energy_state():
    state = derive_energy_state(
        phenotype_contract=_contract("B"),
        energy_trace=_trace(),
        active_configs={"V2-PAL-RULE": {"status": "CANDIDATE"}},
        safety_level="yellow",
    )
    assert state["safety_level"] == "yellow"
    assert state["energy_target"]["status"] == "PROVISIONAL"
