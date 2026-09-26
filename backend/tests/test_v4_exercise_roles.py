from app.v4_exercise_trace import build_canonical_exercise_week


def _a(eid, category="aerobic"):
    return {"exercise_id": eid, "name": eid, "category": category, "status": "DRAFT", "mdt_confirmed": False, "candidate_dose": "按需"}


def test_explicit_non_aerobic_session_roles_are_not_counted_as_formal_aerobic():
    legacy = [
        {"day": 1, "aerobic": [], "resistance": [], "flexibility": [], "functional_activity": [_a("W1")], "functional_activity_session_role": "FUNCTIONAL_ACTIVITY"},
        {"day": 2, "aerobic": [], "resistance": [], "flexibility": [], "recovery": [_a("W2")], "recovery_session_role": "RECOVERY"},
        {"day": 3, "aerobic": [], "resistance": [], "flexibility": [], "warmup": [_a("W3")], "warmup_session_role": "WARMUP"},
        {"day": 4, "aerobic": [], "resistance": [], "flexibility": []},
        {"day": 5, "aerobic": [], "resistance": [], "flexibility": []},
        {"day": 6, "aerobic": [], "resistance": [], "flexibility": []},
        {"day": 7, "aerobic": [], "resistance": [], "flexibility": []},
    ]
    trace, _, _ = build_canonical_exercise_week(legacy, allowed_action_ids={"W1", "W2", "W3"})
    roles = [s["session_role"] for day in trace["daily_schedule"] for s in day["sessions"]]
    assert roles == ["FUNCTIONAL_ACTIVITY", "RECOVERY", "WARMUP"]
    assert trace["weekly_schedule_derived"]["formal_aerobic_days_actual"] == 0
    assert trace["trace_validation"]["formal_vs_functional_activity_semantics_correct"] is True


def test_unknown_status_is_unverified_and_draft_is_not_promoted():
    legacy = [{"day": i, "aerobic": [_a("A01")], "resistance": [], "flexibility": []} if i == 1 else {"day": i, "aerobic": [], "resistance": [], "flexibility": []} for i in range(1, 8)]
    legacy[0]["aerobic"][0]["status"] = "SOMETHING_NEW"
    trace, _, _ = build_canonical_exercise_week(legacy, allowed_action_ids={"A01"})
    action = trace["daily_schedule"][0]["sessions"][0]["actions"][0]
    assert action["knowledge_status"] == "UNVERIFIED"
    assert action["dose_status"] == "PROVISIONAL"

