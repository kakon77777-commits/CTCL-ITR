from copy import deepcopy
import json
from pathlib import Path

import pytest

from ctcl_itr.calibration_joint_surface import (
    CalibrationJointSurfaceError,
    analyze_joint_uncertainty_surface,
)
from ctcl_itr.calibration_mixture_sensitivity import analyze_reference_mixture_sensitivity

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def surface_spec(**overrides):
    spec = {
        "schema_version": "0.2.11",
        "surface_id": "surface:test",
        "generated_at": "2026-08-23T03:45:00+08:00",
        "method": "joint_empirical_binomial_simplex_surface_v1",
        "resampling": {
            "method": "stratified_empirical_binomial_sha256_v1",
            "seed": "joint-surface-test-seed",
            "replicates": 32,
            "interval_p": 0.90,
            "minimum_supported_fraction": 0.50,
        },
        "mixture_grid": {
            "method": "simplex_grid_reference_mixture_v1",
            "grid_step": 0.1,
            "minimum_family_weight": 0.1,
            "max_grid_points": 1000,
        },
    }
    spec.update(overrides)
    return spec


def inputs():
    return (
        load("calibration_snapshot_base.json"),
        load("calibration_snapshot_current.json"),
        load("calibration_comparison_spec.json"),
    )


def test_joint_surface_is_deterministic_and_does_not_mutate_inputs():
    base, current, comparison = inputs()
    spec = surface_spec()
    originals = deepcopy((base, current, comparison, spec))

    first = analyze_joint_uncertainty_surface(base, current, comparison, spec)
    second = analyze_joint_uncertainty_surface(base, current, comparison, spec)

    assert first == second
    assert (base, current, comparison, spec) == originals
    assert first["conditioning"]["same_resampled_outcomes_reused_across_mixture_cells"] is True
    assert first["conditioning"]["reference_mixture_varied"] is True
    assert first["conditioning"]["mixture_weights_resampled"] is False
    assert first["non_authoritative"] is True


def test_point_surface_matches_v0210_mixture_scan():
    base, current, comparison = inputs()
    report = analyze_joint_uncertainty_surface(base, current, comparison, surface_spec())
    old = analyze_reference_mixture_sensitivity(
        base,
        current,
        comparison,
        load("calibration_mixture_sensitivity_spec.json"),
    )

    for subject in ("autonomy", "governance"):
        cells = report["subjects"][subject]["cells"]
        old_cells = old["subjects"][subject]["mixture_scan"]
        assert len(cells) == len(old_cells) == 9
        for new, previous in zip(cells, old_cells):
            assert new["reference_family_weights"] == previous["reference_family_weights"]
            assert new["point_estimate"]["support_status"] == previous["support_status"]
            assert new["point_estimate"]["composition_adjusted_delta"] == previous["composition_adjusted_delta"]


def test_reference_surface_exposes_mixture_dependent_sign_stability_and_support():
    base, current, comparison = inputs()
    report = analyze_joint_uncertainty_surface(base, current, comparison, surface_spec())

    autonomy = report["subjects"]["autonomy"]
    cells = autonomy["cells"]
    classes = [cell["resampling"]["band_sign_class"] for cell in cells]

    assert "crosses_zero" in classes
    assert "positive_band" in classes
    assert "unsupported" in classes
    assert autonomy["surface_summary"]["sign_sensitive_to_mixture"] is True
    assert autonomy["surface_summary"]["resampling_supported_cells"] < len(cells)
    assert autonomy["surface_summary"]["band_sign_class_counts"]["unsupported"] > 0


def test_every_cell_reports_same_replicate_budget_and_supported_rate():
    base, current, comparison = inputs()
    report = analyze_joint_uncertainty_surface(base, current, comparison, surface_spec())
    for subject in ("autonomy", "governance"):
        for cell in report["subjects"][subject]["cells"]:
            resampling = cell["resampling"]
            assert resampling["total_replicates"] == 32
            assert 0 <= resampling["supported_replicates"] <= 32
            assert resampling["supported_fraction"] == pytest.approx(
                resampling["supported_replicates"] / 32
            )
            shares = resampling["sign_shares"]
            if shares is not None:
                assert sum(shares.values()) == pytest.approx(1.0)


def test_different_seed_changes_surface_resampling_but_not_point_estimates():
    base, current, comparison = inputs()
    first = analyze_joint_uncertainty_surface(base, current, comparison, surface_spec())
    changed = surface_spec()
    changed["resampling"]["seed"] = "different-joint-seed"
    second = analyze_joint_uncertainty_surface(base, current, comparison, changed)

    first_cells = first["subjects"]["autonomy"]["cells"]
    second_cells = second["subjects"]["autonomy"]["cells"]
    assert [c["point_estimate"] for c in first_cells] == [c["point_estimate"] for c in second_cells]
    assert [c["resampling"] for c in first_cells] != [c["resampling"] for c in second_cells]


def test_invalid_surface_contracts_are_rejected():
    base, current, comparison = inputs()

    bad = surface_spec(method="other")
    with pytest.raises(CalibrationJointSurfaceError, match="method"):
        analyze_joint_uncertainty_surface(base, current, comparison, bad)

    bad = surface_spec()
    bad["resampling"]["replicates"] = 0
    with pytest.raises(CalibrationJointSurfaceError, match="replicates"):
        analyze_joint_uncertainty_surface(base, current, comparison, bad)

    bad = surface_spec()
    bad["mixture_grid"]["grid_step"] = 0.3
    with pytest.raises(CalibrationJointSurfaceError, match="grid_step"):
        analyze_joint_uncertainty_surface(base, current, comparison, bad)


def test_joint_surface_requires_raw_snapshot_evidence_not_only_built_profiles():
    base, current, comparison = inputs()
    from ctcl_itr.calibration_robustness import build_calibration_snapshot

    with pytest.raises(CalibrationJointSurfaceError, match="family_suites"):
        analyze_joint_uncertainty_surface(
            build_calibration_snapshot(base),
            build_calibration_snapshot(current),
            comparison,
            surface_spec(),
        )
