from copy import deepcopy
import json
from pathlib import Path

import pytest

from ctcl_itr.governance_signals import analyze_governance_signals
from ctcl_itr.horizon_calibration import (
    HorizonCalibrationError,
    calibrate_horizon_suite,
)

ROOT = Path(__file__).resolve().parents[1]


def _series(depths, successes, trials=20, prefix="e"):
    return [
        {
            "depth": depth,
            "trials": trials,
            "successes": success,
            "evidence_refs": [f"{prefix}:{depth}"],
        }
        for depth, success in zip(depths, successes)
    ]


def _suite():
    return {
        "schema_version": "0.2.7",
        "calibration_id": "calibration:reference",
        "calibrated_at": "2026-08-22T00:00:00+00:00",
        "measurement_contract": {
            "unit": "interaction_depth",
            "reliability_p": 0.90,
            "scope_id": "reference-governance-scope",
            "assessment_method": "monotone_binomial_pava_v1",
        },
        "evidence_confidence_p": 0.90,
        "minimums": {
            "min_distinct_depths": 4,
            "min_total_trials": 80,
            "min_trials_per_depth": 20,
        },
        "subjects": {
            "autonomy": _series([4, 8, 12, 16], [20, 19, 18, 10], prefix="a"),
            "governance": _series([3, 6, 9, 12], [20, 19, 18, 10], prefix="g"),
        },
    }


def test_suite_generates_v026_assessment_from_supported_profiles():
    report = calibrate_horizon_suite(_suite())
    assessment = report["derived_assessment"]
    assert report["subjects"]["autonomy"]["horizon_depth"] == pytest.approx(12.0)
    assert report["subjects"]["governance"]["horizon_depth"] == pytest.approx(9.0)
    assert assessment["schema_version"] == "0.2.6"
    assert assessment["autonomy_horizon_depth"] == pytest.approx(12.0)
    assert assessment["governance_horizon_depth"] == pytest.approx(9.0)
    assert assessment["measurement_contract"] == _suite()["measurement_contract"]
    assert assessment["evidence_refs"] == sorted(
        [f"a:{d}" for d in [4, 8, 12, 16]] + [f"g:{d}" for d in [3, 6, 9, 12]]
    )
    assert report["non_authoritative"] is True


def test_generated_assessment_is_consumable_by_v026_signal_engine():
    calibrated = calibrate_horizon_suite(_suite())
    metrics = json.loads((ROOT / "examples/governance_metrics_report.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "examples/governance_escalation_policy.json").read_text(encoding="utf-8"))
    signals = analyze_governance_signals(
        metrics_report=metrics,
        horizon_assessment=calibrated["derived_assessment"],
        policy=policy,
    )
    assert signals["horizon"]["autonomy_horizon_depth"] == pytest.approx(12.0)
    assert signals["horizon"]["governance_horizon_depth"] == pytest.approx(9.0)
    assert signals["horizon"]["autonomy_governance_gap"] == pytest.approx(3.0)


def test_suite_with_unsupported_subject_emits_no_derived_assessment():
    suite = _suite()
    suite["subjects"]["governance"] = _series([3, 6, 9, 12], [20, 20, 20, 20], prefix="g")
    report = calibrate_horizon_suite(suite)
    assert report["subjects"]["governance"]["support_status"] == "target_not_bracketed_high"
    assert report["derived_assessment"] is None


def test_suite_contract_is_strict_and_input_is_not_mutated():
    suite = _suite()
    original = deepcopy(suite)
    report = calibrate_horizon_suite(suite)
    assert suite == original
    assert report["measurement_contract"]["unit"] == "interaction_depth"

    bad = _suite()
    bad["measurement_contract"]["unit"] = "milliseconds"
    with pytest.raises(HorizonCalibrationError):
        calibrate_horizon_suite(bad)

    bad_method = _suite()
    bad_method["measurement_contract"]["assessment_method"] = "manual"
    with pytest.raises(HorizonCalibrationError):
        calibrate_horizon_suite(bad_method)
