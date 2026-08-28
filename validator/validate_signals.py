#!/usr/bin/env python3
from pathlib import Path
import json
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ctcl_itr.governance_signals import analyze_governance_signals


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    pairs = [
        ("schemas/governance-horizon-assessment.schema.json", "examples/governance_horizon_assessment.json"),
        ("schemas/governance-escalation-policy.schema.json", "examples/governance_escalation_policy.json"),
        ("schemas/governance-signal-report.schema.json", "examples/governance_signal_report.json"),
    ]
    for schema_path, example_path in pairs:
        schema = load(schema_path)
        instance = load(example_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(instance)

    metrics = load("examples/governance_metrics_report.json")
    horizon = load("examples/governance_horizon_assessment.json")
    policy = load("examples/governance_escalation_policy.json")
    stored = load("examples/governance_signal_report.json")
    regenerated = analyze_governance_signals(
        metrics_report=metrics,
        horizon_assessment=horizon,
        policy=policy,
    )
    assert regenerated == stored
    assert stored["horizon"]["autonomy_governance_gap"] == 3.0
    assert stored["horizon"]["governance_margin"] == -3.0
    assert stored["signal_counts"]["breach"] == 6
    assert stored["overall_level"] == "critical"
    assert stored["recommended_escalation"] == "urgent_human_review"
    assert stored["non_authoritative"] is True

    print("ITR/ATL v0.2.6 governance horizon & escalation signals: PASS")
    print("autonomy_horizon=12.0")
    print("governance_horizon=9.0")
    print("autonomy_governance_gap=3.0")
    print("governance_margin=-3.0")
    print("signal_breaches=6")
    print("overall_level=critical")
    print("recommended_escalation=urgent_human_review")
    print("non_authoritative=True")


if __name__ == "__main__":
    main()
