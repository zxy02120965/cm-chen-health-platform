from copy import deepcopy

from app.plan_validator import validate_plan
from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile, food_candidate_score, _portion_options_for
from app.v2_knowledge import food_catalog_audit, food_catalog_gap_report, structured_catalog


def _payload(patient_id: str, *, phenotype_hint: str | None = None, weight: float = 68):
    # The same deterministic generator is used for every patient; the id is
    # only a stable tie-breaker, never a patient-specific rule.
    return {
        "patient_id": patient_id,
        "sex": "女", "age_years": 54, "q14_height": 165, "q15_weight": weight,
        "height_cm": 165, "weight_kg": weight, "q6_surgeryWindow": "4–8周",
        "q12_respiratorySymptoms": ["无"], "q28_weightChange": "稳定",
        "q29_appetite": "正常", "q30_intake": "正常",
        "q31_eatingDifficulties": ["无明显困难"], "q32_foodAllergy": ["无"],
        "q33_foodIntolerance": ["无"], "q34_dietPattern": ["三餐规律"],
        "q37_activityLimitations": ["无明显限制"], "q43_metabolicConditions": (["糖尿病"] if phenotype_hint == "B" else ["无"]),
        "q51_executionBarriers": ["无"],
    }


def _breakfast_signature(day):
    meal = next(x for x in day["diet"] if x.get("meal_type") == "breakfast")
    return tuple(x.get("component_id") for x in meal.get("components", []))


def test_candidate_week_rotates_food_components_and_breakfasts():
    plans = []
    for patient_id, hint, weight in (("SYN-A-ROT-1", None, 68), ("SYN-A-ROT-2", None, 75), ("SYN-B-ROT-1", "B", 68), ("SYN-B-ROT-2", "B", 75)):
        payload = _payload(patient_id, phenotype_hint=hint, weight=weight)
        plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
        plans.append(plan)
        assert plan["phenotype"] in {"A", "B"}
        signatures = [_breakfast_signature(day) for day in plan["weekly_schedule"]]
        # V1.4 meal-slot plus V1.3 exact-execution filtering leaves two
        # executable breakfast protein choices; both rotate without using
        # lunch/dinner proteins in breakfast.
        assert len(set(signatures)) >= 2
        assert all(signatures[i] != signatures[i - 1] for i in range(1, len(signatures)))
        # V1.4 meal-slot filtering leaves only one V1.3-exact snack candidate;
        # the week still rotates staples/proteins and breakfasts, while the
        # trace honestly records the source-limited snack rotation.
        assert plan["diet_plan"]["rotation_limited"] is True
    # V1.7 nutrition values can make the same target choose the same optimal
    # rotation; the invariant here is safe intra-week rotation.  A metabolic
    # context still produces a distinct candidate set.
    assert [_breakfast_signature(d) for d in plans[0]["weekly_schedule"]] != [_breakfast_signature(d) for d in plans[2]["weekly_schedule"]]
    assert [_breakfast_signature(d) for d in plans[1]["weekly_schedule"]] != [_breakfast_signature(d) for d in plans[3]["weekly_schedule"]]


def test_rotation_validator_flags_a_repeated_week():
    payload = _payload("SYN-ROT-REPEAT")
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    repeated = deepcopy(plan["weekly_schedule"][0]["diet"])
    for day in plan["weekly_schedule"]:
        day["diet"] = deepcopy(repeated)
    result = validate_plan(plan, mode="TEST_ONLY")
    assert result["checks"]["nutrition.rotation"] == "WARN"
    assert any("连续重复" in warning or "完全相同" in warning for warning in result["warnings"])


def test_catalog_missing_does_not_fallback_to_fixed_menu():
    payload = _payload("P001")
    configs = candidate_test_profile()
    # Simulate a caller that has no usable food catalog. The generator must
    # return an explicit incomplete diet instead of selecting legacy defaults.
    configs["V2-FOOD-COMPONENTS"] = {"status": "ACTIVE", "ids": []}
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=configs)
    assert plan["nutrition_generation_status"] == "incomplete"
    assert plan["diet_plan"]["nutrition_generation_status"] == "incomplete"
    assert plan["diet_plan"]["rotation_limited"] is True
    assert plan["nutrition_generation_missing_reasons"]
    assert all(day["diet"] == [] for day in plan["weekly_schedule"])
    assert len({id(day["diet"]) for day in plan["weekly_schedule"]}) == 7
    assert plan["diet_plan"]["nutrition_plan_validation"] == "FAIL"


def test_patient_ids_do_not_share_identical_rotated_weeks():
    cases = (("P001", None, 68), ("P002", "B", 80), ("P003", None, 75))
    plans = []
    for pid, hint, weight in cases:
        payload = _payload(pid, phenotype_hint=hint, weight=weight)
        plans.append(build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile()))
    weeks = [
        tuple(tuple(x.get("component_id") for x in meal.get("components", [])) for day in plan["weekly_schedule"] for meal in day["diet"] if meal.get("meal_type") == "breakfast")
        for plan in plans
    ]
    assert len(set(weeks)) >= 2


def test_v3_schedule_marks_recovery_days_and_balances_load():
    payload = _payload("SYN-ROT-V3")
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    days = plan["weekly_schedule"]
    assert any(day["rest_day"] and day["day_type"] == "恢复日/日常活动" for day in days)
    resistance_days = [day["day"] for day in days if day["resistance"]]
    assert resistance_days == [1, 3, 5]
    assert all(4 <= len(day["resistance"]) <= 6 for day in days if day["resistance"])
    assert sum(bool(day["aerobic"]) for day in days) == 5


def test_food_score_uses_patient_targets_and_metabolic_context():
    catalog = candidate_test_profile()["V2-FOOD-COMPONENTS"]["items"]
    candidates = [x for x in catalog if x.get("category") == "protein"]
    assert len(candidates) >= 2
    high_protein = max(candidates, key=lambda x: float(x.get("protein_g") or 0))
    low_protein = min(candidates, key=lambda x: float(x.get("protein_g") or 0))
    base = _payload("SYN-SCORE", weight=68)
    high_score, _ = food_candidate_score(high_protein, base, phenotype="A", energy_target=1500, protein_target=110, slot="lunch")
    low_score, _ = food_candidate_score(low_protein, base, phenotype="A", energy_target=1500, protein_target=110, slot="lunch")
    assert high_score > low_score

    metabolic = dict(base)
    metabolic["q43_metabolicConditions"] = ["糖尿病", "血脂异常"]
    carb_candidates = [x for x in catalog if x.get("category") == "staple"]
    high_carb = max(carb_candidates, key=lambda x: float(x.get("carbohydrate_g") or 0))
    low_carb = min(carb_candidates, key=lambda x: float(x.get("carbohydrate_g") or 0))
    high_base, _ = food_candidate_score(high_carb, base, phenotype="A", energy_target=1500, protein_target=90, carb_range=[50, 65], slot="lunch")
    high_metabolic, _ = food_candidate_score(high_carb, metabolic, phenotype="B", energy_target=1500, protein_target=90, carb_range=[50, 65], slot="lunch")
    low_metabolic, _ = food_candidate_score(low_carb, metabolic, phenotype="B", energy_target=1500, protein_target=90, carb_range=[50, 65], slot="lunch")
    assert high_metabolic < high_base
    assert low_metabolic != high_metabolic


def test_daily_energy_error_is_within_existing_closure_tolerance():
    payload = _payload("SYN-ENERGY", weight=68)
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    target = plan["energy_calculation"]["daily_energy_target_kcal"]
    total = plan["diet_plan"]["daily_energy_total"]
    assert target is not None and total is not None
    assert abs(total - target) / target <= 0.20


def test_nutrition_trace_contains_selection_rejection_and_score_components():
    payload = _payload("SYN-P1-TRACE")
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    trace = plan["nutrition_trace"]
    assert trace["selected_food_reason"]
    assert trace["rejected_food_reason"]
    required = {
        "energy_match", "protein_match", "phenotype_match", "disease_match",
        "q34_match", "q56_match", "meal_type_match", "repetition_penalty", "final_score",
    }
    selected = next(item for item in trace["selected_food_reason"] if item.get("food_score_components"))
    assert required.issubset(selected["food_score_components"])
    assert selected["reasons"]
    rejected = next(item for item in trace["rejected_food_reason"] if item.get("top_alternatives"))
    assert rejected["top_alternatives"][0]["reasons"]


def test_metabolic_disease_rules_each_change_the_same_catalog_score():
    catalog = {x["component_id"]: x for x in candidate_test_profile()["V2-FOOD-COMPONENTS"]["items"]}
    # These components carry the corresponding V2 knowledge-base cautions or
    # macro characteristics; no new medical rules are introduced in the test.
    probes = {
        "糖尿病": "C001",
        "血脂异常": "P009",
        "高尿酸": "P005",
        "高血压": "P006",
        "脂肪肝": "P009",
    }
    base = _payload("SYN-P1-DISEASE-BASE", weight=80)
    protein_catalog = [x for x in catalog.values() if x.get("category") == "protein"]
    baseline_order = [
        x["component_id"] for x in sorted(
            protein_catalog,
            key=lambda item: food_candidate_score(item, base, phenotype="B", energy_target=1500, protein_target=96, carb_range=[50, 65], fat_range=[20, 35], slot="lunch")[0],
            reverse=True,
        )
    ]
    for disease, component_id in probes.items():
        food = catalog[component_id]
        baseline, _ = food_candidate_score(food, base, phenotype="B", energy_target=1500, protein_target=96, carb_range=[50, 65], fat_range=[20, 35], slot="lunch")
        affected = dict(base)
        affected["q43_metabolicConditions"] = [disease]
        disease_score, _, components = food_candidate_score(food, affected, phenotype="B", energy_target=1500, protein_target=96, carb_range=[50, 65], fat_range=[20, 35], slot="lunch", return_components=True)
        assert disease_score < baseline, (disease, component_id, baseline, disease_score)
        assert components["disease_match"] < 0
        # The disease state must affect the ranking within the same catalog,
        # rather than only changing a value that is discarded by selection.
        disease_payload = dict(base)
        disease_payload["q43_metabolicConditions"] = [disease]
        disease_order = [
            x["component_id"] for x in sorted(
                protein_catalog,
                key=lambda item: food_candidate_score(item, disease_payload, phenotype="B", energy_target=1500, protein_target=96, carb_range=[50, 65], fat_range=[20, 35], slot="lunch")[0],
                reverse=True,
            )
        ]
        assert disease_order != baseline_order, disease


def test_multiple_metabolic_rules_stack_additively_and_keep_a_negative_distinct():
    catalog = {x["component_id"]: x for x in candidate_test_profile()["V2-FOOD-COMPONENTS"]["items"]}
    food = catalog["P009"]
    base = _payload("SYN-P1-STACK", weight=80)
    scores = {}
    disease_components = {}
    for diseases in (["糖尿病"], ["脂肪肝"], ["糖尿病", "脂肪肝"]):
        payload = dict(base)
        payload["q43_metabolicConditions"] = diseases
        score, _, components = food_candidate_score(food, payload, phenotype="B", energy_target=1500, protein_target=96, carb_range=[50, 65], fat_range=[20, 35], slot="lunch", return_components=True)
        scores[tuple(diseases)] = score
        disease_components[tuple(diseases)] = components["disease_match"]
    assert disease_components[("糖尿病", "脂肪肝")] < disease_components[("糖尿病",)]
    assert disease_components[("糖尿病", "脂肪肝")] < disease_components[("脂肪肝",)]
    assert scores[("糖尿病", "脂肪肝")] < min(scores[("糖尿病",)], scores[("脂肪肝",)])

    # The negative option is not a metabolic condition and therefore does not
    # apply disease penalties or turn an A-type patient into a positive case.
    no_metabolic = dict(base)
    no_metabolic["q43_metabolicConditions"] = ["无"]
    _, _, components = food_candidate_score(food, no_metabolic, phenotype="A", energy_target=1500, protein_target=82, slot="lunch", return_components=True)
    assert components["disease_match"] == 0
    assert assess_payload(_payload("SYN-P1-A-NONE", weight=68))["phenotype_code"] == "A"


def test_p2_closes_each_day_independently_and_exposes_daily_results():
    payload = _payload("SYN-P2-DAILY", weight=68)
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    closures = plan["nutrition_closure"]
    assert len(closures) == 7
    assert [item["day"] for item in closures] == list(range(1, 8))
    assert all({"energy_target", "energy_actual", "energy_delta_pct", "protein_target", "protein_actual", "protein_delta_pct", "closure_status", "reasons"}.issubset(item) for item in closures)
    assert all(day.get("nutrition_closure", {}).get("day") == index for index, day in enumerate(plan["weekly_schedule"], start=1))
    # Each day owns a separate diet list/object; portions are not copied from
    # Day 1 and then reused for the rest of the week.
    assert len({id(day["diet"]) for day in plan["weekly_schedule"]}) == 7
    assert len({str(day.get("actual_energy")) for day in plan["weekly_schedule"]}) > 1
    assert plan["nutrition_trace"]["meal_energy_target"]
    assert plan["nutrition_trace"]["meal_energy_actual"]
    assert plan["nutrition_trace"]["portion_adjustments"]


def test_p2_energy_and_protein_targets_change_portion_choices():
    low_payload = _payload("SYN-P2-LOW", weight=60)
    high_payload = _payload("SYN-P2-HIGH", weight=90)
    low = build_v2_plan(low_payload, assess_payload(low_payload), active_configs=candidate_test_profile())
    high = build_v2_plan(high_payload, assess_payload(high_payload), active_configs=candidate_test_profile())
    assert low["energy_calculation"]["daily_energy_target_kcal"] != high["energy_calculation"]["daily_energy_target_kcal"]
    assert low["diet_plan"]["protein_target"] != high["diet_plan"]["protein_target"]
    low_adjustments = {(item["day"], item["component_id"], item["to_scale"]) for item in low["nutrition_trace"]["portion_adjustments"]}
    high_adjustments = {(item["day"], item["component_id"], item["to_scale"]) for item in high["nutrition_trace"]["portion_adjustments"]}
    assert low_adjustments != high_adjustments
    assert low["weekly_schedule"][0]["actual_protein"] != high["weekly_schedule"][0]["actual_protein"]


def test_p2_af_synthetic_cases_each_receive_seven_day_closures():
    cases = {}
    a = _payload("SYN-P2-A", weight=68)
    cases["A"] = a
    b = _payload("SYN-P2-B", weight=80)
    b["q43_metabolicConditions"] = ["糖尿病"]
    cases["B"] = b
    c = _payload("SYN-P2-C", weight=85)
    c["q18_bodyFat"] = 36
    c["q24_skeletalMuscle"] = 17
    cases["C"] = c
    d = _payload("SYN-P2-D", weight=50)
    d["q30_intake"] = "减少25%"
    cases["D"] = d
    e = _payload("SYN-P2-E", weight=60)
    e["q28_weightChange"] = "不明原因下降"
    e["q30_intake"] = "减少50%"
    cases["E"] = e
    for expected, payload in cases.items():
        evaluation = assess_payload(payload)
        plan = build_v2_plan(payload, evaluation, active_configs=candidate_test_profile())
        assert evaluation["phenotype_code"] == expected
        assert len(plan["nutrition_closure"]) == 7
        assert all(closure["day"] == index for index, closure in enumerate(plan["nutrition_closure"], start=1))
        assert all(closure["energy_actual"] is not None and closure["protein_actual"] is not None for closure in plan["nutrition_closure"])


def test_p25_warn_days_require_nutrition_review_and_weekly_summary():
    payload = _payload("SYN-P2-REVIEW-D", weight=50)
    payload["q30_intake"] = "减少25%"
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())

    # V4 scale coordination changes the former legacy-scale outcome: closure
    # now stays within the frozen component-specific scale sets, so this day
    # may already be closed without a replacement pass.
    # V1.4 slot filtering plus V1.3 source-pending candidates can leave a
    # best-effort day; this is a real review signal, not an exact target.
    assert plan["nutrition_review_required"] is True
    review = plan["nutrition_review"]
    assert review["warn_days"] == [4, 6]
    assert [item["day"] for item in review["issues"]] == [4, 6]

    summary = plan["weekly_nutrition_summary"]
    assert summary["days_warn"] == len(review["warn_days"])
    assert summary["days_pass"] + summary["days_warn"] + summary["days_incomplete"] == 7
    assert summary["average_energy_actual"] is not None
    assert summary["average_energy_delta_pct"] is not None
    assert plan["replacement_optimization"][0]["accepted"] is False
    assert plan["nutrition_trace"]["v4_scale_coordination"]["status"] == "PASS"
    assert plan["nutrition_trace"]["v4_scale_coordination"]["invalid_legacy_scale_prevented"] == 0
    assert plan["nutrition_closure"][0]["protein_actual"] <= 65 * 1.2

    recovery_payload = _payload("SYN-P2-REVIEW-E", weight=60)
    recovery_payload["q28_weightChange"] = "不明原因下降"
    recovery_payload["q30_intake"] = "减少50%"
    recovery = build_v2_plan(recovery_payload, assess_payload(recovery_payload), active_configs=candidate_test_profile())
    # V4 E01 is intentionally structure-only: severe decline does not receive
    # an automatically prescribed single-point energy/protein target.  The
    # former assertion treated this fixture as a numerically closed plan and
    # is therefore superseded by the energy-state contract.
    assert recovery["energy_state"]["energy_target"]["status"] == "UNAVAILABLE"
    assert recovery["energy_state"]["diet_generation_mode"] == "STRUCTURE_ONLY"
    assert recovery["energy_calculation"]["daily_energy_target_kcal"] is None
    assert recovery["nutrition_review_required"] is True
    assert recovery["weekly_nutrition_summary"]["days_incomplete"] == 7
    assert recovery["nutrition_review"]["incomplete_days"] == list(range(1, 8))


def test_d1_scale_coordination_is_bounded_and_traceable():
    payload = _payload("SYN-P2-REPLACEMENT-D1", weight=50)
    payload["q30_intake"] = "减少25%"
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    replacement = plan["replacement_optimization"][0]
    assert replacement["triggered"] is False
    assert replacement["accepted"] is False
    assert replacement["replacements"] == []
    assert plan["nutrition_trace"]["v4_scale_coordination"]["status"] == "PASS"
    assert replacement["candidate_attempts"] >= len(replacement["replacements"])
    assert replacement["replacement_change_count"] == 0
    assert replacement["EXECUTION_COMPLEXITY"] in {"LOW", "MODERATE", "HIGH"}
    assert all(item["reason"] in {
        "replace_protein_to_reduce_protein_density",
        "replace_staple_for_energy_closure",
        "replace_snack_for_energy_support",
    } for item in replacement["replacements"])

    catalog = {item["component_id"]: item for item in candidate_test_profile()["V2-FOOD-COMPONENTS"]["items"]}
    for meal in plan["weekly_schedule"][0]["diet"]:
        seen_categories = set()
        for component in meal.get("components", []):
            category = component.get("category")
            if category in {"staple", "protein", "snack"}:
                assert category not in seen_categories
                seen_categories.add(category)
            scale = component.get("portion_scale")
            if category == "vegetable":
                assert scale in (None, 1.0)
            else:
                assert (scale or 1.0) in _portion_options_for(catalog[component["component_id"]])


def test_well_closed_a_day_does_not_trigger_replacement():
    payload = _payload("SYN-P2-REPLACEMENT-A", weight=68)
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    assert plan["nutrition_review_required"] is False
    assert not any(item["accepted"] for item in plan["replacement_optimization"])


def test_replacement_result_is_deterministic():
    payload = _payload("SYN-P2-REPLACEMENT-DETERMINISTIC", weight=50)
    payload["q30_intake"] = "减少25%"
    first = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    second = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    assert first["replacement_optimization"] == second["replacement_optimization"]
    first_ids = [[component["component_id"] for component in meal.get("components", [])] for meal in first["weekly_schedule"][0]["diet"]]
    second_ids = [[component["component_id"] for component in meal.get("components", [])] for meal in second["weekly_schedule"][0]["diet"]]
    assert first_ids == second_ids


def test_p3a_food_catalog_basis_subcategory_and_portion_audit():
    foods = structured_catalog()["FOOD"]
    audit = food_catalog_audit(foods)
    assert len(audit) == 49
    assert all(item.get("source_text") and item.get("source_table") is not None for item in audit)
    report = food_catalog_gap_report(foods)
    assert report["total"] == 49
    assert report["explicit_portion_min_count"] == 49
    assert report["explicit_portion_max_count"] == 49
    assert report["explicit_portion_step_count"] == 49
    assert all(item.get("source_version") == "V1.7" for item in foods)
    assert all(item.get("source_basis_text") for item in foods)
    assert all(item.get("base_portion_status") == "complete" for item in foods)
    assert all("portion_multiplier_options" in item for item in foods)
    assert report["d_e_candidate_counts"]["dairy"] > 0
    assert report["d_e_candidate_counts"]["fruit"] > 0
    assert report["d_e_candidate_counts"]["nuts"] > 0
    assert report["d_e_candidate_counts"]["protein_snack"] > 0
