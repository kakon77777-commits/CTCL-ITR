from copy import deepcopy

import pytest

from ctcl_itr.calibration_robustness import build_calibration_snapshot
from ctcl_itr.calibration_mixture_sensitivity import (
    CalibrationMixtureSensitivityError,
    analyze_reference_mixture_sensitivity,
)
from tests.calibration_robustness_fixtures import comparison_spec, snapshot_spec


def sensitivity_spec(**overrides):
    spec = {
        "schema_version": "0.2.10",
        "sensitivity_id": "sensitivity:reference-mixture",
        "generated_at": "2026-08-23T02:50:00+00:00",
        "method": "simplex_grid_reference_mixture_v1",
        "grid_step": 0.1,
        "minimum_family_weight": 0.1,
        "max_grid_points": 1000,
    }
    spec.update(overrides)
    return spec


def built_snapshots():
    return (
        build_calibration_snapshot(snapshot_spec(current=False)),
        build_calibration_snapshot(snapshot_spec(current=True)),
    )


def test_reference_grid_is_deterministic_and_preserves_inputs():
    base, current = built_snapshots()
    comparison = comparison_spec()
    spec = sensitivity_spec()
    originals = deepcopy((base, current, comparison, spec))

    first = analyze_reference_mixture_sensitivity(base, current, comparison, spec)
    second = analyze_reference_mixture_sensitivity(base, current, comparison, spec)

    assert first == second
    assert (base, current, comparison, spec) == originals
    assert first["families"] == ["code", "research"]
    assert first["grid"]["total_points"] == 9
    assert first["grid"]["grid_step"] == 0.1


def test_supported_reference_drift_remains_positive_and_extremes_can_be_unsupported():
    base, current = built_snapshots()
    report = analyze_reference_mixture_sensitivity(
        base, current, comparison_spec(), sensitivity_spec()
    )

    for subject in ("autonomy", "governance"):
        payload = report["subjects"][subject]
        supported = [p for p in payload["mixture_scan"] if p["support_status"] == "supported"]
        unsupported = [p for p in payload["mixture_scan"] if p["support_status"] != "supported"]
        assert supported
        assert unsupported
        assert all(p["composition_adjusted_delta"] > 0 for p in supported)
        assert payload["supported_grid_points"] == len(supported)
        assert payload["total_grid_points"] == 9
        assert payload["sensitivity_range"]["span"] > 0
        assert payload["sign_shares"]["positive"] == 1.0


def test_grid_contract_rejects_non_partitioning_step_and_excessive_grid():
    base, current = built_snapshots()
    with pytest.raises(CalibrationMixtureSensitivityError, match="grid_step"):
        analyze_reference_mixture_sensitivity(
            base, current, comparison_spec(), sensitivity_spec(grid_step=0.3)
        )

    # Three families, step .05 and min .05 would yield 171 points; cap it at 10.
    base3 = deepcopy(base)
    current3 = deepcopy(current)
    base3["families"]["third"] = deepcopy(base3["families"]["research"])
    current3["families"]["third"] = deepcopy(current3["families"]["research"])
    with pytest.raises(CalibrationMixtureSensitivityError, match="max_grid_points"):
        analyze_reference_mixture_sensitivity(
            base3,
            current3,
            {
                **comparison_spec(),
                "reference_family_weights": {"code": 1/3, "research": 1/3, "third": 1/3},
            },
            sensitivity_spec(grid_step=0.05, minimum_family_weight=0.05, max_grid_points=10),
        )
