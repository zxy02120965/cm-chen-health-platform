from app.v2_engine import (
    _phenotype,
    build_v2_plan,
    candidate_test_profile,
    energy_trace,
    normalize_selection,
    weekly_review,
)


def _case(phenotype: str, **kwargs):
    base = {"q14_height": 165, "q15_weight": 65, "q43_metabolicConditions": ["无"], "q27_walkTest": {"distance": 500}}
    base.update(kwargs)
    return phenotype, base


def test_negative_choice_is_not_positive_disease():
    result = normalize_selection(["无"])
    assert result["state"] == "explicit_none"
    assert result["positive_items"] == []
    assert _phenotype(_case("A", q18_bodyFat=30)[1])[0] == "A"


def test_synthetic_18_phenotypes():
    cases = [
        _case("A", q18_bodyFat=35, q26_smi=6.7), _case("A", q18_bodyFat=28), _case("A", q18_bodyFat=36.5),
        _case("B", q15_weight=92, q43_metabolicConditions=["高血压", "血脂异常", "脂肪肝"]),
        _case("B", q15_weight=74, q43_metabolicConditions=["糖耐量异常", "血脂异常", "脂肪肝"]),
        _case("B", q15_weight=98, q43_metabolicConditions=["高尿酸", "睡眠呼吸暂停", "血脂异常"]),
        _case("C", q18_bodyFat=40, q26_smi=5.2), _case("C", q27_walkTest="未做（选填缺失）", q51_executionBarriers=["疼痛限制", "不知道怎么运动"]), _case("C", q26_smi=5.0),
        _case("D", q15_weight=47, q29_appetite="下降", q30_intake="减少25%"), _case("D", q29_appetite="下降", q30_intake="减少25%"), _case("D", q29_appetite="下降", q30_intake="减少25%"),
        _case("E", q28_weightChange="不明原因下降", q30_intake="减少50%"), _case("E", q28_weightChange="不明原因下降", q30_intake="减少50%"), _case("E", q28_weightChange="不明原因下降", q30_intake="几乎无法进食"),
        _case("F", q43_metabolicConditions=["高血压", "糖尿病", "血脂异常", "睡眠呼吸暂停"], q51_executionBarriers=["外卖多"]),
        _case("F", q43_metabolicConditions=["高血压", "心血管疾病", "甲状腺疾病"], q51_executionBarriers=["不会操作设备", "不会运动"]),
        _case("F", q43_metabolicConditions=["高血压", "糖尿病", "心血管疾病", "血脂异常"]),
    ]
    actual = [_phenotype(payload)[0] for _, payload in cases]
    assert actual == [expected for expected, _ in cases]


def test_energy_priority_paths_and_cross_check():
    payload = {"q14_height": 170, "q15_weight": 70, "age_years": 58, "sex": "女", "bia_bmr": 1400}
    measured = energy_trace({**payload, "measured_ree_kcal": 1350}, "A", {"has_clinician_goal": False}, "green", active_configs={"V2-PAL-RULE": {"default": 1.4}})
    assert measured["ree_source"] == "P1_MEASURED_REE"
    predicted = energy_trace(payload, "A", {"has_clinician_goal": False}, "green", active_configs={"V2-REE-FORMULA": {"ree_formula_id": "MSJ", "status": "ACTIVE"}, "V2-PAL-RULE": {"default": 1.4}})
    assert predicted["ree_source"] == "P2_APPROVED_FORMULA"
    assert predicted["kcal_per_kg_reference_min"] == 1750
    pending = energy_trace(payload, "A", {"has_clinician_goal": False}, "green")
    assert pending["daily_energy_target_kcal"] is None


def test_missing_catalog_does_not_materialize_fixed_structured_menu():
    payload = {"q14_height": 170, "q15_weight": 70, "age_years": 58, "sex": "女", "q22_bmr": 1400, "q6_surgeryWindow": "4–8周"}
    evaluation = {"phenotype_code": "A", "safety": "green", "safety_label": "绿色", "missing_data": [], "need_clinician_review": False, "liver": {}}
    active = {
        "V2-REE-FORMULA": {"ree_formula_id": "MSJ", "status": "ACTIVE"}, "V2-PAL-RULE": {"default": 1.4, "status": "ACTIVE"},
        "V2-FOOD-COMPONENTS": {"status": "ACTIVE", "ids": ["C002", "P001", "S001", "V001"]},
        "V2-EXERCISE-ACTIONS": {"status": "ACTIVE", "ids": ["A02", "R04"]},
        "V2-PULMONARY-ACTIONS": {"status": "ACTIVE", "ids": ["P01", "P02"]},
    }
    plan = build_v2_plan(payload, evaluation, active_configs=active)
    assert plan["nutrition_generation_status"] == "incomplete"
    assert plan["diet_plan"]["components"] == []
    assert plan["validation_result"]["nutrition_plan_validation"] == "FAIL"
    assert plan["energy_calculation"]["daily_energy_target_kcal"] is not None
    assert plan["nutrition_generation_missing_reasons"]


def test_q56_red_conflict_blocks_publication():
    payload = {"q14_height": 170, "q15_weight": 70, "q6_surgeryWindow": "2周以内", "q56_goal": {"has_clinician_goal": True, "primary_goal": "ENHANCED_FAT_LOSS"}}
    evaluation = {"phenotype_code": "F", "safety": "red", "safety_label": "红色", "missing_data": [], "need_clinician_review": True, "liver": {}}
    plan = build_v2_plan(payload, evaluation)
    assert plan["enhanced_eligible"] is False
    assert plan["goal_conflict"] is True
    assert plan["publication_blocked"] is True
    assert plan["manual_review_required"] is True


def test_candidate_baseline_is_reviewable_and_publishable_when_safe():
    """Patient-level MDT governance metadata must not block the baseline flow."""
    payload = {
        "q14_height": 170,
        "q15_weight": 70,
        "age_years": 58,
        "sex": "女",
        "q6_surgeryWindow": "4–8周",
    }
    evaluation = {
        "phenotype_code": "A",
        "safety": "green",
        "safety_label": "绿色",
        "missing_data": [],
        "need_clinician_review": False,
        "liver": {},
    }
    plan = build_v2_plan(payload, evaluation, active_configs=candidate_test_profile())
    assert plan["rule_authority"] == "PROJECT_BASELINE_V2_V3"
    assert plan["candidate_draft"] is True
    assert plan["publication_blocked"] is False
    assert plan["review_eligible"] is True
    assert plan["publish_eligible"] is True
    assert plan["validation_result"]["publish_validation"] == "PASS"


def test_liver_q50_is_modifier_not_fibrosis_diagnosis():
    from app.rules import assess_payload
    uncertain = assess_payload({"height_cm": 170, "weight_kg": 70, "q50_liverElastography": {"performed": "是", "lsm": 12}})
    assert uncertain["liver_modifier"] == "已检查但报告结论缺失"
    assert uncertain["liver_uncertain"]
    reviewed = assess_payload({"height_cm": 170, "weight_kg": 70, "q50_liverElastography": {"performed": "是", "conclusion": "显著/进展期纤维化"}})
    assert reviewed["safety"] == "yellow"


def test_weekly_review_uses_real_trends_and_pending_exclusion():
    records = [{"record_date": str(i), "record_type": "VITAL", "metadata_json": {"weight_kg": 70 - i * .1, "skeletal_muscle_mass": 30 - i * .2, "diet_completion": .4}, "pending_sync": False} for i in range(7)]
    records.append({"record_date": "8", "metadata_json": {"weight_kg": 1}, "pending_sync": True})
    review = weekly_review(records, phenotype="A")
    assert review["evidence"]["valid_record_count"] == 7
    assert review["decision"] in {"BARRIER_FIRST", "PRESERVE_MUSCLE"}
    assert "muscle_trend" in review["evidence"]
