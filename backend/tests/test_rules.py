import pytest

from app.rules import _normalise_payload, assess_payload, generate_plan_draft


def test_missing_safety_data_is_tier_one():
    result = assess_payload({"sex": "女", "height_cm": 160, "weight_kg": 60})
    assert result["tier"] == 1
    assert "食物过敏/禁忌" in result["missing"]


def test_complete_data_can_generate_draft():
    payload = {"sex": "女", "height_cm": 160, "weight_kg": 60, "food_allergy": "无", "swallowing": "否", "recent_weight_intake": "稳定", "surgery_window_days": 30, "six_minute_walk_m": 420, "spo2_percent": 98}
    result = assess_payload(payload)
    assert result["tier"] == 3
    draft = generate_plan_draft({}, payload, result)
    assert draft["kind"] == "draft"


def test_red_symptom_blocks_plan():
    payload = {"sex": "女", "height_cm": 160, "weight_kg": 60, "food_allergy": "无", "swallowing": "否", "respiratory_symptoms": ["咯血"]}
    result = assess_payload(payload)
    assert result["safety"] == "red"
    assert generate_plan_draft({}, payload, result)["kind"] == "safety_notice"


@pytest.mark.parametrize(
    ("q31", "expected_swallowing", "is_missing", "q31_explicit_none"),
    [
        (None, None, True, False),
        ([], None, True, False),
        (["吞咽困难"], "吞咽困难", False, False),
        (["早饱"], "无", False, False),
        (["早饱", "恶心"], "无", False, False),
        (["咀嚼困难"], "无", False, False),
        (["无"], "无", False, True),
    ],
)
def test_q31_derives_swallowing_without_overwriting_q31_semantics(
    q31, expected_swallowing, is_missing, q31_explicit_none
):
    payload = {"q31_eatingDifficulties": q31}
    normalized = _normalise_payload(payload)
    assert normalized["swallowing"] == expected_swallowing

    result = assess_payload(payload)
    assert ("吞咽困难" in result["missing"]) is is_missing
    assert ("q31_eatingDifficulties" in result["explicit_none"]) is q31_explicit_none
