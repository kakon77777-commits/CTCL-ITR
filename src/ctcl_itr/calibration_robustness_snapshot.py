"""Task-family calibration snapshot construction for CTCL-ITR v0.2.8."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .horizon_calibration import calibrate_horizon_suite
from .calibration_robustness_common import (
    CalibrationRobustnessError,
    _parse_time,
    _required_string,
    _validate_contract,
)

def build_calibration_snapshot(snapshot_spec: dict[str, Any]) -> dict[str, Any]:
    """Calibrate each task family under one shared v0.2.7 measurement contract."""

    if not isinstance(snapshot_spec, dict):
        raise CalibrationRobustnessError("snapshot spec must be an object")
    source = deepcopy(snapshot_spec)
    if source.get("schema_version") != "0.2.8":
        raise CalibrationRobustnessError("snapshot spec must use schema_version 0.2.8")

    snapshot_id = _required_string(source.get("snapshot_id"), "snapshot_id")
    observed_at = _parse_time(source.get("observed_at"), "observed_at")
    backend_id = _required_string(source.get("backend_id"), "backend_id")
    benchmark_id = _required_string(source.get("benchmark_id"), "benchmark_id")
    benchmark_version = _required_string(source.get("benchmark_version"), "benchmark_version")
    agent_config_id = _required_string(source.get("agent_config_id"), "agent_config_id")
    contract = _validate_contract(source.get("measurement_contract"))

    family_suites = source.get("family_suites")
    if not isinstance(family_suites, dict) or not family_suites:
        raise CalibrationRobustnessError("family_suites must be a non-empty object")

    families: dict[str, Any] = {}
    for family_id in sorted(family_suites):
        _required_string(family_id, "task-family id")
        suite = family_suites[family_id]
        if not isinstance(suite, dict):
            raise CalibrationRobustnessError(f"family suite {family_id} must be an object")
        if suite.get("measurement_contract") != contract:
            raise CalibrationRobustnessError(
                f"family suite {family_id} measurement contract does not match snapshot measurement contract"
            )
        profile = calibrate_horizon_suite(suite)
        families[family_id] = {
            "family_id": family_id,
            "calibration_id": profile["calibration_id"],
            "profile": profile,
            "trial_mass": {
                subject: profile["subjects"][subject]["total_trials"]
                for subject in ("autonomy", "governance")
            },
        }

    return {
        "schema_version": "0.2.8",
        "snapshot_id": snapshot_id,
        "observed_at": observed_at,
        "backend_id": backend_id,
        "benchmark_id": benchmark_id,
        "benchmark_version": benchmark_version,
        "agent_config_id": agent_config_id,
        "measurement_contract": contract,
        "families": families,
        "non_authoritative": True,
    }

