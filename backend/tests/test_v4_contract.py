import pytest

from app.v4_contract import derive_v4_phenotype, validate_phenotype_contract


def _payload(**updates):
    payload = {
        "height_cm": 165,
        "weight_kg": 68,
        "q18_bodyFat": 30,
        "q24_skeletalMuscle": 24,
        "q31_eatingDifficulties": ["无"],
        "q43_metabolicConditions": ["无"],
        "q51_executionBarriers": ["无"],
    }
    payload.update(updates)
    return payload


def test_primary_phenotype_is_a_to_e_or_null():
    assert derive_v4_phenotype(_payload())["primary_nutrition_phenotype"] == "A"
    for primary in {"A", "B", "C", "D", "E"}:
        contract = validate_phenotype_contract({
            "primary_nutrition_phenotype": primary,
            "complexity_overlay": "none",
            "display_phenotype": primary,
        })
        assert contract["primary_nutrition_phenotype"] == primary
    assert derive_v4_phenotype({})["primary_nutrition_phenotype"] is None


def test_f_is_only_a_complexity_overlay_and_keeps_underlying_b():
    contract = derive_v4_phenotype(_payload(
        q43_metabolicConditions=["高血压", "糖尿病", "血脂异常", "睡眠呼吸暂停"],
        q51_executionBarriers=["不会操作设备"],
    ))
    assert contract["primary_nutrition_phenotype"] == "B"
    assert contract["complexity_overlay"] == "F"
    assert contract["display_phenotype"] == "F"


def test_ordinary_education_need_does_not_trigger_f_overlay():
    contract = derive_v4_phenotype(_payload(q51_executionBarriers=["不知道怎么吃", "不知道怎么运动"]))
    assert contract["complexity_overlay"] == "none"
    assert contract["display_phenotype"] == contract["primary_nutrition_phenotype"]


def test_f_overlay_requires_underlying_primary():
    with pytest.raises(ValueError):
        validate_phenotype_contract({
            "primary_nutrition_phenotype": None,
            "complexity_overlay": "F",
            "display_phenotype": "F",
        })


def test_invalid_primary_is_rejected():
    with pytest.raises(ValueError):
        validate_phenotype_contract({
            "primary_nutrition_phenotype": "F",
            "complexity_overlay": "none",
            "display_phenotype": "F",
        })
