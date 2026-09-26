import pytest

from app.v4_safety_contract import apply_v4_safety_contract_floor


def floor(existing, primary, overlay="none", reasons=None):
    return apply_v4_safety_contract_floor(
        existing_safety_level=existing,
        existing_reason_codes=reasons or [],
        primary_nutrition_phenotype=primary,
        complexity_overlay=overlay,
    )


def test_a_green_remains_green_without_floor_reason():
    result = floor("GREEN", "A")
    assert result["safety_level"] == "green"
    assert result["safety_reason_codes"] == []
    assert result["safety_floor_applied"] is False


def test_c_green_raises_to_yellow_with_fixed_reason():
    result = floor("green", "C")
    assert result["safety_level"] == "yellow"
    assert result["safety_reason_codes"] == ["MUSCLE_FUNCTION_RISK_REVIEW"]
    assert result["safety_floor_sources"] == ["primary_nutrition_phenotype:C"]


def test_d_green_raises_to_yellow_with_fixed_reason():
    result = floor("green", "D")
    assert result["safety_level"] == "yellow"
    assert result["safety_reason_codes"] == ["NUTRITION_RISK_REVIEW"]


def test_b_f_green_raises_to_yellow_with_complexity_reason():
    result = floor("green", "B", "F")
    assert result["safety_level"] == "yellow"
    assert result["safety_reason_codes"] == ["COMPLEXITY_EXECUTION_REVIEW"]


@pytest.mark.parametrize(
    ("primary", "expected"),
    [("C", ["MUSCLE_FUNCTION_RISK_REVIEW", "COMPLEXITY_EXECUTION_REVIEW"]),
     ("D", ["NUTRITION_RISK_REVIEW", "COMPLEXITY_EXECUTION_REVIEW"])],
)
def test_multiple_floor_reasons_are_preserved(primary, expected):
    result = floor("green", primary, "F")
    assert result["safety_level"] == "yellow"
    assert result["safety_reason_codes"] == expected


@pytest.mark.parametrize(
    ("existing", "primary", "overlay"),
    [("red", "C", "none"), ("red", "D", "none"), ("red", "B", "F"),
     ("yellow", "A", "none")],
)
def test_existing_red_or_yellow_is_never_downgraded(existing, primary, overlay):
    result = floor(existing, primary, overlay)
    assert result["safety_level"] == existing


def test_plain_a_or_b_does_not_gain_floor():
    assert floor("green", "A")["safety_level"] == "green"
    assert floor("green", "B")["safety_level"] == "green"


def test_existing_reason_codes_are_retained_and_deduplicated():
    result = floor("yellow", "C", reasons=["EXISTING_REVIEW", "MUSCLE_FUNCTION_RISK_REVIEW"])
    assert result["safety_reason_codes"] == ["EXISTING_REVIEW", "MUSCLE_FUNCTION_RISK_REVIEW"]


def test_yellow_floor_does_not_itself_block_an_active_candidate():
    from app.rules import assess_payload
    from app.v2_engine import build_v2_plan

    payload = {
        "sex": "女", "age_years": 54, "q14_height": 160, "q15_weight": 72,
        "q18_bodyFat": 40, "q24_skeletalMuscle": 17, "q26_smi": 5.2,
        "q43_metabolicConditions": ["血脂异常"], "q34_dietPattern": ["长期节食"],
        "q12_respiratorySymptoms": ["无"], "q31_eatingDifficulties": ["无"],
    }
    active_configs = {
        "V2-REE-FORMULA": {"ree_formula_id": "MSJ", "status": "ACTIVE"},
        "V2-PAL-RULE": {"default": 1.4, "status": "ACTIVE"},
    }
    evaluation = assess_payload(payload)
    plan = build_v2_plan(payload, evaluation, active_configs=active_configs)
    assert plan["safety_level"] == "yellow"
    assert plan["safety_rules"]["reason_codes"] == ["MUSCLE_FUNCTION_RISK_REVIEW"]
    assert plan["energy_state"]["energy_target"]["status"] == "ACTIVE"
    assert plan["publication_blocked"] is False
