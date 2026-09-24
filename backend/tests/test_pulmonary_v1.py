from app.v2_engine import build_v2_plan, candidate_test_profile


def _plan(*, safety="green", symptoms=None, pulmonary_inputs=None, q37=None):
    payload = {
        "q14_height": 170,
        "q15_weight": 70,
        "q6_surgeryWindow": "4–8周",
        "q12_respiratorySymptoms": symptoms if symptoms is not None else ["无"],
        "q37_activityLimits": q37 if q37 is not None else ["无"],
    }
    evaluation = {
        "phenotype_code": "A",
        "safety": safety,
        "safety_label": {"green": "绿色", "yellow": "黄色", "red": "红色"}[safety],
        "missing_data": [],
        "need_clinician_review": safety != "green",
        "liver": {},
    }
    return build_v2_plan(
        payload,
        evaluation,
        active_configs=candidate_test_profile(),
        pulmonary_clinician_inputs=pulmonary_inputs,
    )


def _pulmonary(plan):
    return {(x["pulmonary_id"], x.get("pulmonary_mode")): x for x in plan["pulmonary_prehab_plan"]}


def test_green_base_and_p05_education_are_standard():
    plan = _plan()
    items = _pulmonary(plan)
    assert ("P01", None) in items and ("P02", None) in items
    assert ("P03", None) not in items
    assert ("P05", "EDUCATION") in items
    assert ("P05", "AIRWAY_CLEARANCE") not in items
    assert plan["pulmonary_dose_level"] == "STANDARD"
    assert items[("P01", None)]["candidate_dose"] == "3–5分钟/次"
    assert items[("P02", None)]["candidate_dose"] == "5–10分钟/次"


def test_yellow_uses_conservative_base_doses():
    plan = _plan(safety="yellow")
    items = _pulmonary(plan)
    assert plan["pulmonary_dose_level"] == "CONSERVATIVE"
    assert items[("P01", None)]["candidate_dose"] == "3分钟/次"
    assert items[("P02", None)]["candidate_dose"] == "5分钟/次"
    assert items[("P02", None)]["frequency_range"] == "1–2次/日"


def test_red_blocks_all_pulmonary_tasks():
    plan = _plan(safety="red", symptoms=["咳痰"], pulmonary_inputs={"p03_indicated": True, "p06_device_available": True, "p06_clinician_ordered": True})
    assert plan["pulmonary_prehab_plan"] == []
    assert plan["pulmonary_dose_level"] == "BLOCKED_RED"


def test_p03_is_explicit_clinician_gate():
    assert ("P03", None) not in _pulmonary(_plan(pulmonary_inputs={"p03_indicated": False}))
    p03 = _pulmonary(_plan(pulmonary_inputs={"p03_indicated": True}))["P03", None]
    assert p03["candidate_dose"] == "5–10次/组"
    conservative = _pulmonary(_plan(safety="yellow", pulmonary_inputs={"p03_indicated": True}))["P03", None]
    assert conservative["candidate_dose"] == "5次/组"


def test_p04_is_not_auto_added_and_can_be_explicitly_indicated():
    assert ("P04", None) not in _pulmonary(_plan())
    assert ("P04", None) in _pulmonary(_plan(pulmonary_inputs={"p04_indicated": True}))


def test_cough_is_not_airway_clearance_but_sputum_is():
    cough = _pulmonary(_plan(symptoms=["咳嗽"]))
    sputum = _pulmonary(_plan(symptoms=["咳痰"]))
    assert ("P05", "EDUCATION") in cough
    assert ("P05", "AIRWAY_CLEARANCE") not in cough
    assert sputum[("P05", "AIRWAY_CLEARANCE")]["frequency_range"] == "按需"


def test_p05_education_is_not_copied_to_all_seven_days():
    plan = _plan()
    weekly = plan["weekly_schedule"]
    education_days = [
        day["day"] for day in weekly
        if any(item.get("mode_id") == "P05_EDUCATION" for item in day.get("pulmonary_prehab", []))
    ]
    assert education_days == [1]


def test_p06_requires_both_device_and_clinician_order():
    for inputs in (
        {"p06_device_available": False, "p06_clinician_ordered": False},
        {"p06_device_available": True, "p06_clinician_ordered": False},
        {"p06_device_available": False, "p06_clinician_ordered": True},
    ):
        assert ("P06", None) not in _pulmonary(_plan(pulmonary_inputs=inputs))
    selected = _pulmonary(_plan(pulmonary_inputs={"p06_device_available": True, "p06_clinician_ordered": True}))
    assert ("P06", None) in selected
    assert selected[("P06", None)]["device_available"] is True
    assert selected[("P06", None)]["clinician_ordered"] is True


def test_knee_limit_does_not_change_pulmonary_selection():
    unrestricted = _pulmonary(_plan(q37=["无"]))
    knee = _pulmonary(_plan(q37=["膝痛"]))
    assert set(unrestricted) == set(knee)
    assert [(k, unrestricted[k].get("candidate_dose")) for k in unrestricted] == [(k, knee[k].get("candidate_dose")) for k in knee]
