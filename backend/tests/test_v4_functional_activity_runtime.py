import json
from pathlib import Path

import pytest

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile
from app.v4_functional_activity_data import (
    FunctionalActivityDataError,
    _load_runtime,
    get_functional_activity_asset_provenance,
    load_functional_activity_data,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "v4_contract"


def _e_payload():
    return json.loads((FIXTURE_DIR / "SYN-E01.json").read_text(encoding="utf-8"))["assessment_payload"]


def test_final_loader_is_manifest_bound_and_provenance_complete():
    load_functional_activity_data.cache_clear()
    runtime = load_functional_activity_data()
    provenance = get_functional_activity_asset_provenance()
    assert len(runtime.actions) == 5
    assert set(runtime.actions) == {"FA-V05", "FA-V18", "FA-V19", "FA-V21", "FA-INDOOR"}
    assert all(action.session_role == "FUNCTIONAL_ACTIVITY" for action in runtime.actions.values())
    assert provenance.role == "FUNCTIONAL_ACTIVITY_ACTION_LIBRARY"
    assert provenance.version == "V1.0"
    assert provenance.relative_path.endswith("ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx")
    assert len(provenance.sha256) == 64
    assert all(action.source_asset == provenance.relative_path for action in runtime.actions.values())
    assert all(action.source_asset_version == provenance.version for action in runtime.actions.values())
    assert all(action.knowledge_status == "ACTIVE" for action in runtime.actions.values())
    assert all(action.clinical_review_status == "APPROVED" for action in runtime.actions.values())
    assert all(action.mdt_confirmed is False for action in runtime.actions.values())
    assert all(action.to_runtime_action()["reviewer"] is None for action in runtime.actions.values())
    assert all(action.to_runtime_action()["review_date"] is None for action in runtime.actions.values())


def test_loader_rejects_non_functional_role(monkeypatch):
    import app.v4_functional_activity_data as module

    valid = module._read_xlsx_sheet(
        module.ASSET_ROOT / "data" / "ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx",
        "Functional_Activity_Final",
    )
    broken = [list(row) for row in valid]
    broken[6][2] = "FORMAL_AEROBIC"
    monkeypatch.setattr(module, "_read_xlsx_sheet", lambda *_args: broken)
    with pytest.raises(FunctionalActivityDataError, match="invalid session_role"):
        _load_runtime()


def test_loader_rejects_duplicate_action_id(monkeypatch):
    import app.v4_functional_activity_data as module

    valid = module._read_xlsx_sheet(
        module.ASSET_ROOT / "data" / "ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx",
        "Functional_Activity_Final",
    )
    broken = [list(row) for row in valid]
    broken[7][0] = broken[6][0]
    monkeypatch.setattr(module, "_read_xlsx_sheet", lambda *_args: broken)
    with pytest.raises(FunctionalActivityDataError, match="duplicate functional activity action_id"):
        _load_runtime()


def test_deferred_e_materializes_metadata_selected_functional_action():
    load_functional_activity_data.cache_clear()
    payload = _e_payload()
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    trace = plan["exercise_plan_trace"]
    context = trace["context_snapshot"]
    materialization = context["functional_activity_materialization"]
    assert context["formal_aerobic_eligibility"]["status"] == "DEFERRED_FOR_NUTRITION_RECOVERY"
    assert materialization["status"] == "MATERIALIZED"
    assert materialization["selected_action_ids"] == ["FA-INDOOR"]
    assert "FUNCTIONAL_ACTIVITY_SOURCE_UNAVAILABLE" not in materialization["reason_codes"]
    assert trace["weekly_schedule_derived"]["formal_aerobic_days_actual"] == 0
    assert trace["weekly_schedule_derived"]["functional_activity_days_actual"] > 0
    assert context["e_formal_aerobic_validation"]["functional_activity_preserved_when_safe"] is True
    assert context["e_formal_aerobic_validation"]["status"] == "PASS"
    assert trace["schedule_consistency_validation"]["status"] == "PASS"
    assert trace["trace_materialization_status"] == "FULL"
    actions = [
        action
        for day in trace["daily_schedule"]
        for session in day["sessions"]
        if session["session_role"] == "FUNCTIONAL_ACTIVITY"
        for action in session["actions"]
    ]
    assert actions
    assert all(action["session_role"] == "FUNCTIONAL_ACTIVITY" for action in actions)
    assert all(action["functional_activity_subtype"] == "DAILY_ACTIVITY_MAINTENANCE" for action in actions)
    assert all(action["source_asset"].endswith("ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx") for action in actions)
    assert all(action["knowledge_status"] == "ACTIVE" for action in actions)
    assert all(action["dose_status"] == "PROVISIONAL" for action in actions)
    assert all(action["mdt_confirmed"] is False for action in actions)


def test_non_e_plans_do_not_consume_functional_activity_asset():
    for fixture_id in ("SYN-A01", "SYN-B01", "SYN-C01", "SYN-D01", "SYN-F01"):
        payload = json.loads((FIXTURE_DIR / f"{fixture_id}.json").read_text(encoding="utf-8"))["assessment_payload"]
        plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
        context = plan["exercise_plan_trace"]["context_snapshot"]
        assert "functional_activity_materialization" not in context
        assert all(
            session["session_role"] != "FUNCTIONAL_ACTIVITY"
            for day in plan["exercise_plan_trace"]["daily_schedule"]
            for session in day["sessions"]
        )
