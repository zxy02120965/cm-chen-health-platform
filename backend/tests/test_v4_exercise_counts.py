from app.v4_exercise_trace import build_canonical_exercise_week


def _day(day, aerobic=None, resistance=None, flexibility=None):
    def a(eid, category):
        return {"exercise_id": eid, "name": eid, "category": category, "status": "DRAFT", "mdt_confirmed": False, "candidate_dose": "dose"}
    return {
        "day": day,
        "aerobic": [a(x, "aerobic") for x in (aerobic or [])],
        "resistance": [a(x, "resistance") for x in (resistance or [])],
        "flexibility": [a(x, "flexibility") for x in (flexibility or [])],
    }


def test_same_role_multiple_sessions_on_one_day_count_once_and_declared_range_passes():
    legacy = [_day(1, aerobic=["A1", "A2"], resistance=["R1"])] + [_day(i) for i in range(2, 8)]
    trace, _, _ = build_canonical_exercise_week(
        legacy,
        combo={"aerobic_days_target": [1, 2], "resistance_days_target": [1, 1]},
        allowed_action_ids={"A1", "A2", "R1"},
    )
    assert trace["weekly_schedule_derived"]["formal_aerobic_days_actual"] == 1
    assert trace["weekly_schedule_derived"]["resistance_days_actual"] == 1
    assert trace["schedule_consistency_validation"]["status"] == "PASS"


def test_declared_vs_derived_mismatch_is_fail_without_changing_schedule():
    trace, _, _ = build_canonical_exercise_week(
        [_day(1, aerobic=["A1"])] + [_day(i) for i in range(2, 8)],
        combo={"aerobic_days_target": 5},
        allowed_action_ids={"A1"},
    )
    assert trace["weekly_schedule_derived"]["formal_aerobic_days_actual"] == 1
    assert trace["schedule_consistency_validation"]["status"] == "FAIL"
    assert trace["trace_materialization_status"] == "MISSING"

