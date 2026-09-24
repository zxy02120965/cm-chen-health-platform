"""Structured Plan Content Contract shared by rules and future AI adapters.

The contract deliberately permits ``null``/empty arrays and carries
``mdt_confirmed`` flags.  It is a transport shape, not a source of clinical
thresholds or doses.  Published content is the only input to plan-task
materialisation.
"""

PLAN_CONTENT_CONTRACT_VERSION = "2.1"
PLAN_CONTENT_KEYS = (
    "management_period", "stage_goals", "diet_plan", "exercise_plan",
    "pulmonary_prehab_plan", "monitoring_plan", "safety_rules",
    "clinician_notes", "missing_data", "mdt_pending_items", "goal_source",
    "clinician_goal_q56", "phenotype", "surgery_window", "safety_level",
    "energy_calculation", "body_composition_targets", "weekly_schedule",
    "daily_record_requirements", "weekly_review", "next_week_adjustment",
    "generator_type", "rule_version", "knowledge_versions", "config_versions",
    "validation_result",
)


def contract_missing_keys(content: dict) -> list[str]:
    """Return required top-level keys absent from a plan payload."""
    return [key for key in PLAN_CONTENT_KEYS if key not in (content or {})]
