"""Read-only integrity checks for the frozen ZXY Week 1 V4 assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


ASSET_ROOT = Path(__file__).resolve().parents[1] / "knowledge" / "zxy_week1"
MANIFEST_PATH = ASSET_ROOT / "manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _asset_path(entry: dict) -> Path:
    return ASSET_ROOT / Path(entry["relative_path"])


def test_zxy_week1_manifest_lists_existing_assets():
    manifest = _manifest()
    assets = manifest["assets"]
    assert len(assets) == 10
    assert all(_asset_path(entry).is_file() for entry in assets)


def test_zxy_week1_manifest_versions_match_filenames_and_top_level_versions():
    manifest = _manifest()
    expected = {
        "01_ZXY_MASTER_AGENT_KNOWLEDGE_BASE_FINAL_V4_2_5.md": ("V4.2.5", "CLINICAL_MASTER"),
        "02_ZXY_NUTRITION_COMPONENT_LIBRARY_FINAL_V4_2_4.md": ("V4.2.4", "NUTRITION_GENERATION_RULES"),
        "03_ZXY_EXERCISE_PULMONARY_REHAB_LIBRARY_FINAL_V4_2_1.md": ("V4.2.1", "EXERCISE_PULMONARY_RULES"),
        "ZXY_第一周方案统一输出与医生端展示规范_V1.2.md": ("V1.2", "UI_OUTPUT_CONTRACT"),
        "ZXY_回归测试与后端验收规范_V1.0.md": ("V1.0", "ENGINEERING_TEST_CONTRACT"),
        "ZXY_基础食材层_Ingredient_Master_MDT定稿版_V1.4.xlsx": ("V1.4", "MDT_INGREDIENT_MASTER"),
        "ZXY_FOOD_49组件_份量执行化_MDT定稿版_V1.4.xlsx": ("V1.4", "MDT_STANDARD_COMPONENT_EXECUTION"),
        "ZXY_Ingredient_Nutrition_Provenance_MDT_V1.4.json": ("V1.4", "MDT_NUTRITION_SOURCE_PROVENANCE"),
        "ZXY_FOOD_Selection_Metadata_MDT_FINAL_V1.4.json": ("V1.4", "FOOD_SELECTION_METADATA"),
        "ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx": ("V1.0", "FUNCTIONAL_ACTIVITY_ACTION_LIBRARY"),
    }
    for entry in manifest["assets"]:
        filename = Path(entry["relative_path"]).name
        assert filename in expected
        assert (entry["version"], entry["role"]) == expected[filename]
    assert manifest["master_rule_version"] == "V4.2.5"
    assert manifest["nutrition_rule_version"] == "V4.2.4"
    assert manifest["exercise_pulmonary_rule_version"] == "V4.2.1"
    assert manifest["ui_contract_version"] == "V1.2"
    assert manifest["engineering_test_contract_version"] == "V1.0"
    assert manifest["ingredient_master_version"] == "V1.4"
    assert manifest["food_component_execution_version"] == "V1.4"


def test_zxy_week1_manifest_sha256_matches_current_assets():
    for entry in _manifest()["assets"]:
        digest = hashlib.sha256(_asset_path(entry).read_bytes()).hexdigest()
        assert digest == entry["sha256"]


def test_zxy_week1_has_one_active_master_nutrition_and_exercise_rule_asset():
    active = [entry for entry in _manifest()["assets"] if entry["active"]]
    for role in ("CLINICAL_MASTER", "NUTRITION_GENERATION_RULES", "EXERCISE_PULMONARY_RULES"):
        assert sum(entry["role"] == role for entry in active) == 1


def test_zxy_week1_contracts_are_not_marked_as_clinical_knowledge():
    roles = {entry["role"] for entry in _manifest()["assets"]}
    assert "UI_OUTPUT_CONTRACT" in roles
    assert "ENGINEERING_TEST_CONTRACT" in roles
    assert "UI_OUTPUT_CONTRACT" not in {"CLINICAL_MASTER", "NUTRITION_GENERATION_RULES", "EXERCISE_PULMONARY_RULES"}
    assert "ENGINEERING_TEST_CONTRACT" not in {"CLINICAL_MASTER", "NUTRITION_GENERATION_RULES", "EXERCISE_PULMONARY_RULES"}


def test_zxy_week1_excel_assets_are_readable_xlsx_packages():
    xlsx_entries = [entry for entry in _manifest()["assets"] if entry["relative_path"].endswith(".xlsx")]
    assert len(xlsx_entries) == 3
    for entry in xlsx_entries:
        with zipfile.ZipFile(_asset_path(entry), "r") as workbook:
            names = set(workbook.namelist())
            assert "[Content_Types].xml" in names
            assert "xl/workbook.xml" in names


def test_zxy_week1_assets_do_not_depend_on_outputs_directory():
    for entry in _manifest()["assets"]:
        assert not entry["relative_path"].lower().startswith("outputs/")
        assert "outputs" not in str(_asset_path(entry)).lower()
