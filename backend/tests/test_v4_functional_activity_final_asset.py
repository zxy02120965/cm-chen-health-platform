import json
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

from app.rules import assess_payload
from app.v2_engine import build_v2_plan, candidate_test_profile


ASSET = (
    Path(__file__).parents[1]
    / "knowledge"
    / "zxy_week1"
    / "data"
    / "ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx"
)
FIXTURE = Path(__file__).parent / "fixtures" / "v4_contract" / "SYN-E01.json"
NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def _cell_value(cell, shared_strings):
    kind = cell.attrib.get("t")
    if kind == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//a:t", NS))
    value = cell.find("a:v", NS)
    if value is None:
        return ""
    raw = value.text or ""
    if kind == "s":
        return shared_strings[int(raw)]
    if kind == "b":
        return raw == "1"
    if raw == "":
        return ""
    try:
        return float(raw) if "." in raw else int(raw)
    except ValueError:
        return raw


def _column_index(ref):
    letters = "".join(ch for ch in ref if ch.isalpha())
    result = 0
    for char in letters.upper():
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def _rows():
    with zipfile.ZipFile(ASSET) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in item.findall(".//a:t", NS)) for item in root.findall("a:si", NS)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
        sheet = workbook.find("a:sheets/a:sheet", NS)
        target = relmap[sheet.attrib["{" + NS["r"] + "}id"]].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        root = ET.fromstring(archive.read(target))
        output = []
        for row in root.findall(".//a:sheetData/a:row", NS):
            values = {}
            for cell in row.findall("a:c", NS):
                values[_column_index(cell.attrib["r"])] = _cell_value(cell, shared)
            output.append(values)
        return output


def _data():
    rows = _rows()
    header = rows[5]
    headers = [header[index] for index in sorted(header)]
    return [{headers[index]: row.get(index, "") for index in range(len(headers))} for row in rows[6:11]]


def test_final_asset_contract_and_review_metadata():
    assert ASSET.exists()
    data = _data()
    assert [item["action_id"] for item in data] == ["FA-V05", "FA-V18", "FA-V19", "FA-V21", "FA-INDOOR"]
    assert len({item["action_id"] for item in data}) == 5
    valid_subtypes = {"BEDSIDE_MOBILITY", "FUNCTIONAL_TRANSFER", "DAILY_ACTIVITY_MAINTENANCE"}
    for item in data:
        assert item["session_role"] == "FUNCTIONAL_ACTIVITY"
        assert item["functional_activity_subtype"] in valid_subtypes
        assert item["knowledge_status"] == "ACTIVE"
        assert item["clinical_content_status"] == "CLINICIAN_APPROVED"
        assert item["clinical_review_status"] == "APPROVED"
        assert item["review_status"] == "APPROVED"
        assert item["review_decision"] == "APPROVE"
        assert item["mdt_confirmed"] is False
        assert item["requires_clinical_review"] is False
        assert item["approval_evidence_status"] == "USER_CONFIRMED_CLINICIAN_REVIEW"
        assert item["reviewer"] == ""
        assert item["review_date"] == ""
        assert "MDT_APPROVED" not in json.dumps(item, ensure_ascii=False)
        origins = json.loads(item["parameter_origin"])
        assert origins
        assert set(origins.values()) <= {"SOURCE_SUPPORTED", "CLINICIAN_APPROVED_PROJECT_PARAMETER"}


def test_final_asset_has_complete_action_specific_execution_parameters():
    by_id = {item["action_id"]: item for item in _data()}
    required = {
        "FA-V05": ["repetitions", "sets", "frequency", "position", "execution", "stop_conditions"],
        "FA-V18": ["repetitions", "frequency", "additional_frequency", "execution", "stop_conditions"],
        "FA-V19": ["repetitions", "frequency", "optional_frequency", "execution", "stop_conditions"],
        "FA-V21": ["repetitions", "sets", "frequency", "optional_frequency", "execution", "stop_conditions"],
        "FA-INDOOR": ["duration", "frequency", "optional_frequency", "intensity", "segmentation", "execution", "stop_conditions"],
    }
    for action_id, fields in required.items():
        for field in fields:
            assert by_id[action_id][field] not in ("", None), (action_id, field)
    assert by_id["FA-INDOOR"]["duration"] == "3–10 min/次"
    assert by_id["FA-INDOOR"]["intensity"] == "舒适轻活动"


def test_runtime_remains_unintegrated_and_e01_source_unavailable():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))["assessment_payload"]
    plan = build_v2_plan(payload, assess_payload(payload), active_configs=candidate_test_profile())
    context = plan["exercise_plan_trace"]["context_snapshot"]
    assert context["functional_activity_materialization"] == {
        "status": "UNAVAILABLE",
        "reason_codes": ["FUNCTIONAL_ACTIVITY_SOURCE_UNAVAILABLE"],
    }
    assert context["formal_aerobic_eligibility"]["status"] == "DEFERRED_FOR_NUTRITION_RECOVERY"
