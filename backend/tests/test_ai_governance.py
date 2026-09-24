from app.ai_governance import ADAPTIVE_RULES, evaluate_adjustment, validate_draft


def test_numeric_unconfirmed_dose_cannot_pass_validation():
    draft = {
        "clinician_notes": {"review_required": True},
        "diet_plan": {"daily_energy_target_kcal": 1800, "mdt_confirmed": False},
        "exercise_plan": [],
        "pulmonary_prehab_plan": [],
        "safety_rules": {"safety_level": "green"},
    }
    assert "diet_plan 含未经MDT确认的数值" in validate_draft(draft, [])


def test_adaptive_rule_requires_activation_before_matching():
    rules = [{"rule_id": rule_id, "trigger": {"description": trigger}, "safety_level": level,
              "action": {"freeze": freeze, "outcome": outcome}, "reviewer_role": reviewer,
              "adjustable_fields": fields, "status": "ACTIVE" if rule_id == "ADJ-001" else "PENDING"}
             for rule_id, trigger, level, freeze, reviewer, fields, outcome in ADAPTIVE_RULES]
    matches = evaluate_adjustment({"intake_insufficient_3_days": True, "red_safety_event": True}, rules)
    assert [item["rule_id"] for item in matches] == ["ADJ-001"]
