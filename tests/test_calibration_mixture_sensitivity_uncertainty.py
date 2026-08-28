from copy import deepcopy
import json

import pytest

from ctcl_itr.calibration_robustness import build_calibration_snapshot
from ctcl_itr.calibration_mixture_sensitivity import (
    CalibrationMixtureSensitivityError,
    analyze_reference_mixture_sensitivity,
)
from tests.calibration_robustness_fixtures import comparison_spec, snapshot_spec


def sensitivity_spec():
    return {
        "schema_version": "0.2.10",
        "sensitivity_id": "sensitivity:reference-mixture",
        "generated_at": "2026-08-23T02:50:00+00:00",
        "method": "simplex_grid_reference_mixture_v1",
        "grid_step": 0.1,
        "minimum_family_weight": 0.1,
        "max_grid_points": 1000,
    }


def inputs():
    return (
        build_calibration_snapshot(snapshot_spec(current=False)),
        build_calibration_snapshot(snapshot_spec(current=True)),
        comparison_spec(),
        sensitivity_spec(),
        json.load(open("examples/calibration_uncertainty_report.json", encoding="utf-8")),
    )


def test_sampling_and_mixture_choice_are_reported_as_separate_axes():
    base, current, comparison, sensitivity, uncertainty = inputs()
    report = analyze_reference_mixture_sensitivity(
        base, current, comparison, sensitivity, uncertainty
    )

    assert "total_uncertainty" not in report
    assert report["uncertainty_decomposition"] == "separate_axes_not_additive"

    for subject in ("autonomy", "governance"):
        axes = report["subjects"][subject]["uncertainty_axes"]
        source_band = uncertainty["subjects"][subject]["bands"]["composition_adjusted_delta"]
        expected_width = source_band["band"]["upper"] - source_band["band"]["lower"]
        assert axes["sampling_uncertainty_at_reference"]["band"] == source_band["band"]
        assert axes["sampling_band_width_at_reference"] == pytest.approx(expected_width)
        assert axes["reference_mixture_sensitivity_span"] == pytest.approx(
            report["subjects"][subject]["sensitivity_range"]["span"]
        )
        assert axes["mixture_to_sampling_width_ratio"] == pytest.approx(
            axes["reference_mixture_sensitivity_span"] / axes["sampling_band_width_at_reference"]
        )
        assert axes["larger_reported_axis"] == "sampling"


def test_uncertainty_identity_mismatch_is_rejected():
    base, current, comparison, sensitivity, uncertainty = inputs()
    bad = deepcopy(uncertainty)
    bad["comparison_id"] = "comparison:other"
    with pytest.raises(CalibrationMixtureSensitivityError, match="comparison_id"):
        analyze_reference_mixture_sensitivity(base, current, comparison, sensitivity, bad)

    bad = deepcopy(uncertainty)
    bad["point_estimate_context"]["reference_family_weights"] = {"code": 0.4, "research": 0.6}
    with pytest.raises(CalibrationMixtureSensitivityError, match="reference_family_weights"):
        analyze_reference_mixture_sensitivity(base, current, comparison, sensitivity, bad)
