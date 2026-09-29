"""Acceptance checks for the MDT-approved ZXY Week1 V1.3 data assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

from app.v4_food_data import ASSET_ROOT, _read_xlsx_sheet, load_v4_food_data
from app.v4_food_materializer import materialize_standard_component, validate_execution_amount


MANIFEST = ASSET_ROOT / "manifest.json"
DATA = ASSET_ROOT / "data"
V12_INGREDIENT_SHA256 = "50aca8714a6d55179c60da32070f4be7a5010efc0712e13d2cf010905193818f"
V12_FOOD_SHA256 = "6b5fd88e7b586939cd89aabb4e0366089001f111f02f8f0f7e7acc1d8ec6e198"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v12_and_v13_assets_remain_immutable_and_v14_is_active():
    assert _sha256(DATA / "ZXY_基础食材层_Ingredient_Master_MDT定稿版_V1.2.xlsx") == V12_INGREDIENT_SHA256
    assert _sha256(DATA / "ZXY_FOOD_49组件_份量执行化_MDT定稿版_V1.2.xlsx") == V12_FOOD_SHA256
    manifest = _manifest()
    active = {entry["role"]: entry for entry in manifest["assets"] if entry["active"]}
    assert _sha256(DATA / "ZXY_基础食材层_Ingredient_Master_MDT定稿版_V1.3.xlsx") == "e0db11c4e146350a11771e4492d7995a2d99e82636221c7c5a5f0876d1a45150"
    assert _sha256(DATA / "ZXY_FOOD_49组件_份量执行化_MDT定稿版_V1.3.xlsx") == "05fc4cb4bb8b8c970383cb3d82ffa25fe1645182468d22934aaf1c521c63b983"
    assert active["MDT_INGREDIENT_MASTER"]["version"] == "V1.4"
    assert active["MDT_STANDARD_COMPONENT_EXECUTION"]["version"] == "V1.4"
    assert active["MDT_INGREDIENT_MASTER"]["relative_path"].endswith("V1.4.xlsx")
    assert active["MDT_STANDARD_COMPONENT_EXECUTION"]["relative_path"].endswith("V1.4.xlsx")


def test_v13_hashes_match_manifest_and_runtime_sources():
    runtime = load_v4_food_data()
    manifest = _manifest()
    active = {entry["role"]: entry for entry in manifest["assets"] if entry["active"]}
    for role, path in (("MDT_INGREDIENT_MASTER", runtime.ingredient_source), ("MDT_STANDARD_COMPONENT_EXECUTION", runtime.food_source)):
        assert _sha256(path) == active[role]["sha256"]
        assert path.name.endswith("V1.4.xlsx")


def test_ingredient_master_v14_approved_weight_basis_and_pending_states():
    runtime = load_v4_food_data()
    yogurt = runtime.ingredient("ING022")
    assert (yogurt.unit, yogurt.min_amount, yogurt.max_amount, yogurt.step) == ("g", 100.0, 200.0, 50.0)
    assert yogurt.weight_basis == "package_net_weight"
    assert yogurt.nutrition_basis == "per_100g"
    assert yogurt.nutrition_source == "PRODUCT_LABEL_CONFIRMED"
    assert yogurt.final_decision == "ACTIVE_FOR_EXACT"
    assert yogurt.execution_eligible is True
    assert yogurt.exact_nutrition_eligible is True
    assert yogurt.nutrition_source_pending is False
    assert runtime.ingredient("ING020").step == 10.0
    assert runtime.ingredient("ING027").weight_basis == "hydrated_edible_weight"
    assert runtime.ingredient("ING027").exact_nutrition_eligible is False
    assert runtime.ingredient("ING047").weight_basis == "edible_kernel_weight"
    assert runtime.ingredient("ING019").weight_basis == "whole_unit + edible_weight"


def test_yogurt_components_are_g_150g_and_pending_not_unit_mismatch():
    runtime = load_v4_food_data()
    for component_id in ("S002", "S005", "S010"):
        component = runtime.component(component_id)
        mapping = next(item for item in component.mappings_by_scale[1.0] if item.ingredient_id == "ING022")
        assert mapping.algorithmic_amount == 150.0
        assert mapping.executable_amount == 150.0
        assert mapping.unit == "g"
        result = materialize_standard_component(component_id, 1.0, runtime=runtime)
        assert result["execution_materialization_status"] == "PASS"
        assert result["standard_component_materialization"]["exact_nutrition_eligible"] is True
        assert result["standard_component_materialization"]["nutrition_source_pending"] is False
        assert not any("UNIT_MISMATCH" in str(value) for value in result.values())


def test_tofu_step_is_ten_grams_and_original_executable_values_are_stable():
    runtime = load_v4_food_data()
    expected = {
        ("P008", 0.5): 80.0,
        ("P008", 0.75): 110.0,
        ("P008", 1.0): 150.0,
        ("P008", 1.25): 190.0,
        ("P013", 0.75): 80.0,
        ("P013", 1.0): 100.0,
        ("P013", 1.25): 130.0,
        ("P014", 1.0): 100.0,
    }
    tofu = runtime.ingredient("ING020")
    assert tofu.step == 10.0
    for (component_id, scale), executable in expected.items():
        mapping = next(item for item in runtime.component(component_id).mappings_by_scale[scale] if item.ingredient_id == "ING020")
        assert mapping.executable_amount == executable
        assert validate_execution_amount(tofu, mapping.executable_amount)


def test_all_approved_weight_basis_changes_are_present_on_mapped_items():
    runtime = load_v4_food_data()
    expected = {"ING027": "hydrated_edible_weight", "ING047": "edible_kernel_weight", "ING019": "whole_unit + edible_weight"}
    for ingredient_id, basis in expected.items():
        assert runtime.ingredient(ingredient_id).weight_basis == basis


def test_all_49_components_have_resolved_legal_execution_mappings():
    runtime = load_v4_food_data()
    assert len(runtime.components) == 49
    missing = []
    out_of_bounds = []
    off_grid = []
    unit_mismatch = []
    for component in runtime.components.values():
        for scale in component.allowed_scales:
            for mapping in component.mappings_by_scale[scale]:
                ingredient = runtime.ingredient(mapping.ingredient_id)
                if not mapping.ingredient_id:
                    missing.append(component.component_id)
                if mapping.unit != ingredient.unit:
                    unit_mismatch.append((component.component_id, mapping.ingredient_id))
                if not (ingredient.min_amount <= mapping.executable_amount <= ingredient.max_amount):
                    out_of_bounds.append((component.component_id, mapping.ingredient_id))
                if not validate_execution_amount(ingredient, mapping.executable_amount):
                    off_grid.append((component.component_id, mapping.ingredient_id, mapping.executable_amount))
    assert missing == []
    assert unit_mismatch == []
    assert out_of_bounds == []
    assert off_grid == []


def test_pending_sources_remain_executable_but_are_not_exact_nutrition_sources():
    runtime = load_v4_food_data()
    pending = [ingredient for ingredient in runtime.ingredients.values() if ingredient.nutrition_source_pending]
    assert pending
    assert all(ingredient.execution_eligible for ingredient in pending)
    assert all(not ingredient.exact_nutrition_eligible for ingredient in pending)
    assert all(ingredient.requires_clinician_review for ingredient in pending)


def test_no_automatic_g_ml_conversion_is_present_in_yogurt_mappings():
    runtime = load_v4_food_data()
    for component_id in ("S002", "S005", "S010"):
        mapping = next(item for item in runtime.component(component_id).mappings_by_scale[1.0] if item.ingredient_id == "ING022")
        assert mapping.unit == "g"
        assert mapping.algorithmic_amount == mapping.executable_amount == 150.0


def test_yogurt_formula_cells_keep_numeric_cached_execution_values():
    path = DATA / "ZXY_FOOD_49组件_份量执行化_MDT定稿版_V1.3.xlsx"
    rows = _read_xlsx_sheet(path, "份量执行映射_候选")
    targets = set()
    for row_number, row in enumerate(rows, start=1):
        if len(row) > 13 and str(row[0]) in {"S002", "S005", "S010"} and float(row[3]) == 1.0 and row[4] == "无糖酸奶":
            targets.add(row_number)
    assert len(targets) == 3
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        worksheet = ET.fromstring(archive.read("xl/worksheets/sheet6.xml"))
        values = {}
        for cell in worksheet.findall(".//a:c", ns):
            ref = cell.attrib.get("r", "")
            if ref.startswith("N") and int(ref[1:]) in targets:
                formula = cell.find("a:f", ns)
                cached = cell.find("a:v", ns)
                values[int(ref[1:])] = (formula.text if formula is not None else None, cached.text if cached is not None else None)
        assert set(values) == targets
        assert all(formula and cached and float(cached) == 150.0 for formula, cached in values.values())
        raw_xml = b"".join(archive.read(name) for name in archive.namelist() if name.startswith("xl/worksheets/") and name.endswith(".xml"))
        for token in (b"#VALUE!", b"#REF!", b"#N/A", b"#DIV/0!"):
            assert token not in raw_xml


def test_manifest_keeps_clinical_rule_hashes_unchanged():
    manifest = _manifest()
    expected = {
        "CLINICAL_MASTER": "548a279a19d5239b7e87564b0003e52e97f6275c873bff01ebb54b6843f9e460",
        "NUTRITION_GENERATION_RULES": "f77f8a742a364f1367b3418f3cafe8ffdd589433b1dfe4c2807a968b3102badc",
        "EXERCISE_PULMONARY_RULES": "f552fe6a6ebb3ef83d09b8e8d6574469b94de16244374e067cfa2a119dfe43bf",
        "UI_OUTPUT_CONTRACT": "0adddf996028258712b6f5d6ab53bbab812d414252f418f9720010c05cdf9964",
        "ENGINEERING_TEST_CONTRACT": "ae9a9958f937254f5ea6fd55bf18745031d2e39f5d7ab5b344b1ed0ee6830b22",
    }
    active = {entry["role"]: entry for entry in manifest["assets"] if entry["active"]}
    assert {role: active[role]["sha256"] for role in expected} == expected
