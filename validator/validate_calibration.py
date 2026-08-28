#!/usr/bin/env python3
from pathlib import Path
import json
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctcl_itr.governance_signals import analyze_governance_signals
from ctcl_itr.horizon_calibration import calibrate_horizon_suite


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    pairs = [
        ("schemas/horizon-calibration-suite.schema.json", "examples/horizon_calibration_suite.json"),
        ("schemas/horizon-evidence-profile.schema.json", "examples/horizon_calibration_profile.json"),
    ]
    for schema_path, example_path in pairs:
        schema = load(schema_path)
        instance = load(example_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(instance)

    suite = load("examples/horizon_calibration_suite.json")
    stored = load("examples/horizon_calibration_profile.json")
    regenerated = calibrate_horizon_suite(suite)
    assert regenerated == stored

    autonomy = stored["subjects"]["autonomy"]
    governance = stored["subjects"]["governance"]
    assessment = stored["derived_assessment"]
    assert autonomy["support_status"] == "supported"
    assert governance["support_status"] == "supported"
    assert assessment["autonomy_horizon_depth"] == 12.0
    assert assessment["governance_horizon_depth"] == 9.0

    metrics = load("examples/governance_metrics_report.json")
    policy = load("examples/governance_escalation_policy.json")
    signals = analyze_governance_signals(
        metrics_report=metrics,
        horizon_assessment=assessment,
        policy=policy,
    )
    assert signals["horizon"]["autonomy_governance_gap"] == 3.0

    print("ITR/ATL v0.2.7 horizon calibration & evidence profiles: PASS")
    print("calibration_method=monotone_binomial_pava_v1")
    print(f"autonomy_horizon={assessment['autonomy_horizon_depth']}")
    print(f"governance_horizon={assessment['governance_horizon_depth']}")
    print(f"autonomy_support={autonomy['support_status']}")
    print(f"governance_support={governance['support_status']}")
    print(f"autonomy_trials={autonomy['total_trials']}")
    print(f"governance_trials={governance['total_trials']}")
    print("non_authoritative=True")


if __name__ == "__main__":
    main()
