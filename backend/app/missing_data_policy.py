"""Shared missing-data contract for every future plan-generation adapter.

This is deliberately provider-neutral: it can be passed as the system prompt
to an approved model later, but it is also used by the deterministic V1 rules
to make missing values explicit instead of guessing.
"""

GLOBAL_MISSING_DATA_RULE = """
GLOBAL MISSING DATA RULE
1. Never fill, guess, interpolate, or default an optional field to normal.
2. Distinguish an explicit none selection from null, blank, unknown, or not assessed.
3. A plan may use available core data when optional labs, body composition,
   6MWT, or liver elastography are missing, but must not produce false-precision
   disease, risk, or functional grading based on those missing values.
4. When a conclusion cannot be supported, output one of: 数据不足、未评估、
   无法依据现有资料分级、需补充检查、需MDT/专科判断。
5. Missing optional data should not block the whole plan. Pause only the
   task whose safe execution depends on that missing information.
6. Structured input/output must preserve known_data, missing_data, explicit_none,
   uncertain_items, and need_clinician_review.
""".strip()


def structured_missing_context(known_data, missing_data, explicit_none=None, uncertain_items=None, need_clinician_review=False):
    return {
        "known_data": known_data,
        "missing_data": missing_data,
        "explicit_none": explicit_none or [],
        "uncertain_items": uncertain_items or [],
        "need_clinician_review": bool(need_clinician_review),
    }
