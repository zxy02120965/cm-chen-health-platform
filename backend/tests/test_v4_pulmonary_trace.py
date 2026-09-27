import json
import hashlib
from pathlib import Path

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "v4_contract"


def _plan(fixture_id="A01", *, symptoms=None, pulmonary_inputs=None):
    fixture = json.loads((FIXTURE_DIR / f"SYN-{fixture_id}.json").read_text(encoding="utf-8"))
    payload = dict(fixture["assessment_payload"])
    if symptoms is not None:
        payload["q12_respiratorySymptoms"] = symptoms
    evaluation = assess_payload(payload)
    return build_v2_plan(
        payload,
        evaluation,
        active_configs=candidate_test_profile(),
        pulmonary_clinician_inputs=pulmonary_inputs,
    )


def test_canonical_root_and_provenance_are_full_for_a_to_f():
    for fixture_id in ("A01", "B01", "C01", "D01", "E01", "F01"):
        trace = _plan(fixture_id)["pulmonary_rehab_trace"]
        assert trace["schema_version"] == "PULMONARY_TRACE_V4_2"
        assert trace["trace_materialization_status"] == "FULL"
        assert trace["pulmonary_trace_full"] is True
        assert trace["pulmonary_dose_status"] == "PROVISIONAL"
        assert "clinician_or_guidance" not in trace["p06_gate"]
        assert "clinician_ordered" not in trace["p06_gate"]
        assert "opep_clinician_order_or_guidance" in trace["context_snapshot"]
        assert [day["day"] for day in trace["daily_schedule"]] == list(range(1, 8))
        assert trace["trace_validation"]["status"] == "PASS"
        assert trace["source_provenance"]["source_version"] == "V2.0"
        source_path = Path(__file__).resolve().parents[2] / trace["source_provenance"]["source_path"]
        assert trace["source_provenance"]["sha256"] == hashlib.sha256(source_path.read_bytes()).hexdigest()
        assert trace["source_provenance"]["knowledge_status"] == "DRAFT"
        assert trace["source_provenance"]["mdt_confirmed"] is False
        assert all(action["dose_status"] == "PROVISIONAL" for day in trace["daily_schedule"] for action in day["actions"])


def test_p05_skill_learning_gate_is_explicit_without_sputum():
    trace = _plan("A01")["pulmonary_rehab_trace"]
    gate = trace["p05_gate"]
    assert gate == {
        "selected": True,
        "mode": "SKILL_LEARNING",
        "skill_learning": True,
        "clinical_need_for_clearance": False,
        "reason": "preoperative_skill_rehearsal",
        "sputum_or_clearance_need": False,
        "dose_source_available": True,
    }
    assert [a["pulmonary_mode"] for a in trace["daily_schedule"][0]["actions"] if a["action_id"] == "P05"] == ["EDUCATION"]


def test_p05_clearance_mode_is_not_mixed_with_skill_learning():
    plan = _plan("A01", symptoms=["咳痰"])
    trace = plan["pulmonary_rehab_trace"]
    gate = trace["p05_gate"]
    assert gate["mode"] == "AIRWAY_CLEARANCE"
    assert gate["skill_learning"] is False
    assert gate["clinical_need_for_clearance"] is True
    assert gate["reason"] == "sputum_or_clearance_need"
    p05_modes = {a.get("pulmonary_mode") for day in trace["daily_schedule"] for a in day["actions"] if a["action_id"] == "P05"}
    assert p05_modes == {"AIRWAY_CLEARANCE"}


def test_p06_requires_need_device_and_guidance():
    not_needed = _plan("A01", symptoms=["无"], pulmonary_inputs={"p06_device_available": True, "p06_clinician_ordered": True})
    gate = not_needed["pulmonary_rehab_trace"]["p06_gate"]
    assert gate == {"sputum_or_clearance_need": False, "device_available": True, "clinician_order_or_guidance": True, "eligible": False}
    assert "P06" not in not_needed["pulmonary_rehab_trace"]["selected_action_ids"]
    assert not_needed["pulmonary_rehab_trace"]["blocked_actions"] == [{"action_id": "P06", "dose_status": "UNAVAILABLE", "reason": "P06_THREE_PART_GATE_NOT_SATISFIED"}]

    missing_device = _plan("A01", symptoms=["咳痰"], pulmonary_inputs={"p06_device_available": False, "p06_clinician_ordered": True})
    assert missing_device["pulmonary_rehab_trace"]["p06_gate"]["eligible"] is False

    missing_order = _plan("A01", symptoms=["咳痰"], pulmonary_inputs={"p06_device_available": True, "p06_clinician_ordered": False})
    assert missing_order["pulmonary_rehab_trace"]["p06_gate"]["eligible"] is False

    eligible = _plan("A01", symptoms=["咳痰"], pulmonary_inputs={"p06_device_available": True, "p06_clinician_ordered": True})
    trace = eligible["pulmonary_rehab_trace"]
    assert trace["p06_gate"]["eligible"] is True
    assert "clinician_or_guidance" not in trace["p06_gate"]
    assert "clinician_ordered" not in trace["p06_gate"]
    assert trace["p06_gate"]["clinician_order_or_guidance"] is True
    assert "P06" in trace["selected_action_ids"]
    assert all(action["dose_status"] == "UNAVAILABLE" for day in trace["daily_schedule"] for action in day["actions"] if action["action_id"] == "P06")


def test_patient_projection_and_artifact_return_come_from_root():
    plan = _plan("F01")
    trace = plan["pulmonary_rehab_trace"]
    projected = {(item["pulmonary_id"], item.get("pulmonary_mode")) for item in plan["pulmonary_prehab_plan"]}
    canonical = {(item["pulmonary_id"], item.get("pulmonary_mode")) for day in trace["daily_schedule"] for item in day["actions"]}
    assert projected <= canonical
    assert plan["artifact_return"]["pulmonary_trace"] == {
        "present": True,
        "materialization": "FULL",
        "schema_version": "PULMONARY_TRACE_V4_2",
        "days_materialized": 7,
    }
