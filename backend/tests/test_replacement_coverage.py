from app.v2_engine import (
    _optimize_day_replacements,
    _replacement_is_acceptable,
    candidate_test_profile,
)


def _empty_days():
    return [{"breakfast": {"components": []}} for _ in range(7)]


def _run_trigger(energy_delta, protein_delta):
    baseline = {
        "day": 1,
        "energy_actual": 1000,
        "protein_actual": 60,
        "energy_delta_pct": energy_delta,
        "protein_delta_pct": protein_delta,
    }
    _, _, _, trace = _optimize_day_replacements(
        0,
        _empty_days(),
        [],
        {},
        phenotype="D",
        goal={},
        energy_target=1500,
        protein_target=60,
        carb_range=None,
        fat_range=None,
        meal_distribution=None,
        base_day_meals=_empty_days()[0],
        baseline_closure=baseline,
    )
    return trace


def test_energy_deficit_triggers_even_when_protein_is_high_or_adequate():
    assert _run_trigger(-25, 10)["triggered"] is True
    assert _run_trigger(-25, 25)["triggered"] is True


def test_protein_high_triggers_even_when_energy_is_within_tolerance():
    trace = _run_trigger(-5, 25)
    assert trace["triggered"] is True
    assert "蛋白" in trace["reason"]


def test_protein_deficit_triggers_and_closed_day_does_not():
    assert _run_trigger(-5, -25)["triggered"] is True
    assert _run_trigger(5, 5)["triggered"] is False


def test_replacement_cannot_create_new_warn_metric():
    before = {"energy_delta_pct": -25, "protein_delta_pct": 0}
    after_new_protein_warn = {"energy_delta_pct": -5, "protein_delta_pct": 25}
    assert _replacement_is_acceptable(before, after_new_protein_warn) is False


def test_replacement_accepts_two_warns_to_two_passes():
    before = {"energy_delta_pct": -25, "protein_delta_pct": -25}
    after = {"energy_delta_pct": -5, "protein_delta_pct": 5}
    assert _replacement_is_acceptable(before, after) is True


def test_candidate_profile_still_exposes_v17_food_boundaries():
    items = candidate_test_profile()["V2-FOOD-COMPONENTS"]["items"]
    assert items
    assert all(item.get("portion_min") is not None for item in items)
    assert all(item.get("portion_max") is not None for item in items)
    assert all(item.get("portion_step") is not None for item in items)
