from copy import deepcopy

import pytest

from calibration_robustness_fixtures import comparison_spec, snapshot_spec
from ctcl_itr.calibration_robustness import (
    CalibrationRobustnessError,
    build_calibration_snapshot,
    compare_calibration_snapshots,
)


def report():
    return compare_calibration_snapshots(
        build_calibration_snapshot(snapshot_spec(current=False)),
        build_calibration_snapshot(snapshot_spec(current=True)),
        comparison_spec(),
    )


def test_comparison_separates_observed_mixture_from_fixed_reference_drift():
    result = report()
    autonomy = result["subjects"]["autonomy"]
    governance = result["subjects"]["governance"]

    assert autonomy["observed_family_weights"]["base"] == pytest.approx({"code": 0.8, "research": 0.2})
    assert autonomy["observed_family_weights"]["current"] == pytest.approx({"code": 0.2, "research": 0.8})
    assert autonomy["composition_total_variation"] == pytest.approx(0.6)
    assert autonomy["observed_mix_delta"] < 0
    assert autonomy["composition_adjusted_delta"] > 0
    assert autonomy["composition_residual"] == pytest.approx(
        autonomy["observed_mix_delta"] - autonomy["composition_adjusted_delta"]
    )

    assert governance["observed_mix_delta"] < 0
    assert governance["composition_adjusted_delta"] > 0
    assert governance["composition_total_variation"] == pytest.approx(0.6)


def test_comparison_reports_positive_within_family_deltas_despite_observed_decline():
    result = report()
    for subject in ("autonomy", "governance"):
        family_deltas = result["subjects"][subject]["family_horizon_deltas"]
        assert family_deltas["code"]["delta"] > 0
        assert family_deltas["research"]["delta"] > 0
        assert result["subjects"][subject]["family_direction_agreement"] == pytest.approx(1.0)
        assert result["subjects"][subject]["supported_family_fraction"] == pytest.approx(1.0)
        assert result["subjects"][subject]["max_abs_family_delta"] > 0


def test_comparison_labels_context_and_elapsed_time_without_causal_claim():
    result = report()
    context = result["context_diagnostics"]
    assert context == {
        "backend_changed": True,
        "benchmark_version_changed": False,
        "agent_config_changed": False,
        "family_set_changed": False,
        "comparison_kind": "cross_backend",
    }
    assert result["elapsed_seconds"] == pytest.approx(86400.0)
    assert result["subjects"]["autonomy"]["composition_adjusted_delta_per_day"] == pytest.approx(
        result["subjects"]["autonomy"]["composition_adjusted_delta"]
    )
    assert result["non_authoritative"] is True
    assert result["attribution_boundary"] == "composition_standardization_only"


def test_mixture_refuses_to_extrapolate_when_family_supports_do_not_overlap():
    base = build_calibration_snapshot(snapshot_spec(current=False, disjoint_support=True))
    current = build_calibration_snapshot(snapshot_spec(current=True, disjoint_support=True))
    result = compare_calibration_snapshots(base, current, comparison_spec())

    for subject in ("autonomy", "governance"):
        assert result["subjects"][subject]["support_status"] == "unsupported"
        assert "no_common_depth_support" in result["subjects"][subject]["support_reasons"]
        assert result["subjects"][subject]["composition_adjusted_delta"] is None


def test_comparison_rejects_measurement_contract_mismatch():
    base = build_calibration_snapshot(snapshot_spec(current=False))
    current_spec = snapshot_spec(current=True)
    current_spec["measurement_contract"]["reliability_p"] = 0.8
    for suite in current_spec["family_suites"].values():
        suite["measurement_contract"]["reliability_p"] = 0.8
    current = build_calibration_snapshot(current_spec)

    with pytest.raises(CalibrationRobustnessError, match="measurement contracts"):
        compare_calibration_snapshots(base, current, comparison_spec())


def test_comparison_does_not_mutate_inputs():
    base = build_calibration_snapshot(snapshot_spec(current=False))
    current = build_calibration_snapshot(snapshot_spec(current=True))
    spec = comparison_spec()
    before = (deepcopy(base), deepcopy(current), deepcopy(spec))
    compare_calibration_snapshots(base, current, spec)
    assert (base, current, spec) == before
