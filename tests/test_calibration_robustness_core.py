from copy import deepcopy

import pytest

from ctcl_itr.calibration_robustness import (
    CalibrationRobustnessError,
    build_calibration_snapshot,
)


def family_suite(calibration_id, depths, successes, *, trials=10, scope_id="scope:reference"):
    return {
        "schema_version": "0.2.7",
        "calibration_id": calibration_id,
        "calibrated_at": "2026-08-22T12:00:00+00:00",
        "measurement_contract": {
            "unit": "interaction_depth",
            "reliability_p": 0.9,
            "scope_id": scope_id,
            "assessment_method": "monotone_binomial_pava_v1",
        },
        "evidence_confidence_p": 0.9,
        "minimums": {
            "min_distinct_depths": 4,
            "min_total_trials": 40,
            "min_trials_per_depth": 10,
        },
        "subjects": {
            "autonomy": [
                {
                    "depth": depth,
                    "trials": trials,
                    "successes": success,
                    "evidence_refs": [f"evidence:{calibration_id}:autonomy:{depth}"],
                }
                for depth, success in zip(depths["autonomy"], successes["autonomy"])
            ],
            "governance": [
                {
                    "depth": depth,
                    "trials": trials,
                    "successes": success,
                    "evidence_refs": [f"evidence:{calibration_id}:governance:{depth}"],
                }
                for depth, success in zip(depths["governance"], successes["governance"])
            ],
        },
    }


def snapshot_spec():
    contract = {
        "unit": "interaction_depth",
        "reliability_p": 0.9,
        "scope_id": "scope:reference",
        "assessment_method": "monotone_binomial_pava_v1",
    }
    code = family_suite(
        "family:code",
        {"autonomy": [4, 8, 12, 16], "governance": [3, 6, 9, 12]},
        {"autonomy": [10, 10, 9, 5], "governance": [10, 10, 9, 5]},
    )
    research = family_suite(
        "family:research",
        {"autonomy": [2, 4, 6, 8], "governance": [1, 3, 5, 7]},
        {"autonomy": [10, 10, 9, 5], "governance": [10, 10, 9, 5]},
    )
    return {
        "schema_version": "0.2.8",
        "snapshot_id": "snapshot:base",
        "observed_at": "2026-08-22T12:00:00+00:00",
        "backend_id": "backend-alpha",
        "benchmark_id": "benchmark:reference",
        "benchmark_version": "1.0",
        "agent_config_id": "agent-config:stable",
        "measurement_contract": contract,
        "family_suites": {"code": code, "research": research},
    }


def test_build_snapshot_calibrates_each_family_and_preserves_context():
    spec = snapshot_spec()
    result = build_calibration_snapshot(spec)

    assert result["schema_version"] == "0.2.8"
    assert result["snapshot_id"] == "snapshot:base"
    assert result["backend_id"] == "backend-alpha"
    assert result["benchmark_id"] == "benchmark:reference"
    assert result["benchmark_version"] == "1.0"
    assert result["agent_config_id"] == "agent-config:stable"
    assert result["measurement_contract"] == spec["measurement_contract"]
    assert set(result["families"]) == {"code", "research"}
    assert result["families"]["code"]["profile"]["subjects"]["autonomy"]["horizon_depth"] == 12.0
    assert result["families"]["code"]["profile"]["subjects"]["governance"]["horizon_depth"] == 9.0
    assert result["families"]["research"]["profile"]["subjects"]["autonomy"]["horizon_depth"] == 6.0
    assert result["families"]["research"]["profile"]["subjects"]["governance"]["horizon_depth"] == 5.0
    assert result["families"]["code"]["trial_mass"] == {"autonomy": 40, "governance": 40}
    assert result["non_authoritative"] is True


def test_build_snapshot_does_not_mutate_input():
    spec = snapshot_spec()
    before = deepcopy(spec)
    build_calibration_snapshot(spec)
    assert spec == before


def test_build_snapshot_rejects_family_contract_mismatch():
    spec = snapshot_spec()
    spec["family_suites"]["research"]["measurement_contract"]["scope_id"] = "scope:other"
    with pytest.raises(CalibrationRobustnessError, match="measurement contract"):
        build_calibration_snapshot(spec)


def test_build_snapshot_rejects_empty_family_set():
    spec = snapshot_spec()
    spec["family_suites"] = {}
    with pytest.raises(CalibrationRobustnessError, match="family_suites"):
        build_calibration_snapshot(spec)


def test_build_snapshot_rejects_invalid_snapshot_version():
    spec = snapshot_spec()
    spec["schema_version"] = "0.2.7"
    with pytest.raises(CalibrationRobustnessError, match="schema_version 0.2.8"):
        build_calibration_snapshot(spec)
