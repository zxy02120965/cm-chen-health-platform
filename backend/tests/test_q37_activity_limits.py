from app.rules import _normalise_payload, assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


def _payload(**extra):
    value = {
        "sex": "女",
        "age_years": 54,
        "q14_height": 165,
        "q15_weight": 68,
        "q6_surgeryWindow": "4–8周",
        "q12_respiratorySymptoms": ["无"],
        "q28_weightChange": "稳定",
        "q29_appetite": "正常",
        "q30_intake": "正常",
        "q31_eatingDifficulties": ["无明显困难"],
        "q32_foodAllergy": ["无"],
        "q34_dietPattern": ["三餐规律"],
        "q43_metabolicConditions": ["无"],
        "q51_executionBarriers": ["无"],
    }
    value.update(extra)
    return value


def test_q37_canonical_key_maps_to_internal_activity_limitations():
    normalized = _normalise_payload(_payload(q37_activityLimits=["膝痛"]))
    assert normalized["activity_limitations"] == ["膝痛"]
    assert assess_payload(_payload(q37_activityLimits=["膝痛"]))["choice_normalization"]["q37_activityLimits"]["positive_items"] == ["膝痛"]


def test_q37_negative_and_empty_semantics_are_preserved():
    no_limit = assess_payload(_payload(q37_activityLimits=["无"]))
    assert no_limit["choice_normalization"]["q37_activityLimits"]["positive_items"] == []
    assert no_limit["choice_normalization"]["q37_activityLimits"]["explicit_none"] == ["无"]

    empty = assess_payload(_payload(q37_activityLimits=[]))
    assert empty["choice_normalization"]["q37_activityLimits"]["state"] == "empty"


def test_q37_legacy_alias_is_supported_but_canonical_key_wins_on_conflict():
    legacy = _normalise_payload(_payload(q37_activityLimitations=["膝痛"]))
    assert legacy["activity_limitations"] == ["膝痛"]

    canonical_wins = _normalise_payload(_payload(
        q37_activityLimits=["无"], q37_activityLimitations=["膝痛"], activity_limitations=["膝痛"]
    ))
    assert canonical_wins["activity_limitations"] == ["无"]

    canonical_empty = _normalise_payload(_payload(
        q37_activityLimits=[], q37_activityLimitations=["膝痛"], activity_limitations=["膝痛"]
    ))
    assert canonical_empty["activity_limitations"] == []
    plan = build_v2_plan(
        _payload(q37_activityLimits=[], q37_activityLimitations=["膝痛"], activity_limitations=["膝痛"]),
        assess_payload(_payload(q37_activityLimits=[], q37_activityLimitations=["膝痛"], activity_limitations=["膝痛"])),
        active_configs=candidate_test_profile(),
    )
    resistance_ids = [x["exercise_id"] for day in plan["weekly_schedule"] for x in day["resistance"]]
    assert "L01" in resistance_ids


def test_q37_knee_limit_changes_v3_exercise_schedule():
    unrestricted = _payload(q37_activityLimits=["无"])
    knee_limited = _payload(q37_activityLimits=["膝痛"])
    plan_without = build_v2_plan(unrestricted, assess_payload(unrestricted), active_configs=candidate_test_profile())
    plan_with = build_v2_plan(knee_limited, assess_payload(knee_limited), active_configs=candidate_test_profile())

    without_ids = [x["exercise_id"] for day in plan_without["weekly_schedule"] for x in day["resistance"]]
    with_ids = [x["exercise_id"] for day in plan_with["weekly_schedule"] for x in day["resistance"]]
    assert without_ids != with_ids
    assert all(eid not in {"L01", "L02", "L03", "L06"} for eid in with_ids)
