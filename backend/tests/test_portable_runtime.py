from __future__ import annotations


def test_runtime_generation_does_not_require_legacy_v17_outputs(tmp_path, monkeypatch):
    """Current generation must remain usable when the historical outputs file is absent."""
    from app import v2_knowledge
    from app.v2_engine import candidate_test_profile

    missing_legacy = tmp_path / "outputs" / "p3b_food_mdt_review" / "FOOD知识库_V1.7_MDT确认正式版.xlsx"
    monkeypatch.setattr(v2_knowledge, "OFFICIAL_FOOD_WORKBOOK", missing_legacy)

    profile = candidate_test_profile()

    assert profile["FOOD_SELECTION_METADATA"]["role"] == "FOOD_SELECTION_METADATA"
    assert profile["FOOD_SELECTION_METADATA"]["version"] == "V1.4"
    assert profile["V2-FOOD-COMPONENTS"]["selection_source"]["manifest_registered"] is True
    assert not missing_legacy.exists()


def test_legacy_v17_loader_is_explicit_and_not_import_side_effect(tmp_path, monkeypatch):
    """The legacy parser may fail closed when explicitly called, never on import."""
    from app import v2_knowledge

    missing_legacy = tmp_path / "missing-v17.xlsx"
    monkeypatch.setattr(v2_knowledge, "OFFICIAL_FOOD_WORKBOOK", missing_legacy)

    assert v2_knowledge.FOOD_COMPONENTS_V2 == []
    try:
        v2_knowledge.structured_catalog()
    except FileNotFoundError:
        pass
    else:  # pragma: no cover
        raise AssertionError("legacy V1.7 loader unexpectedly succeeded")
