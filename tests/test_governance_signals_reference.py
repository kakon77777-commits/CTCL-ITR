import json
from pathlib import Path

import jsonschema

from ctcl_itr.governance_signals import analyze_governance_signals

ROOT = Path(__file__).resolve().parents[1]


def _load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_governance_signal_schemas_are_valid_and_examples_conform():
    pairs = [
        ("schemas/governance-horizon-assessment.schema.json", "examples/governance_horizon_assessment.json"),
        ("schemas/governance-escalation-policy.schema.json", "examples/governance_escalation_policy.json"),
        ("schemas/governance-signal-report.schema.json", "examples/governance_signal_report.json"),
    ]
    for schema_path, example_path in pairs:
        schema = _load(schema_path); instance = _load(example_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(instance)


def test_reference_signal_report_is_exact_regeneration():
    metrics = _load("examples/governance_metrics_report.json")
    horizon = _load("examples/governance_horizon_assessment.json")
    policy = _load("examples/governance_escalation_policy.json")
    stored = _load("examples/governance_signal_report.json")
    regenerated = analyze_governance_signals(metrics_report=metrics,horizon_assessment=horizon,policy=policy)
    assert regenerated == stored
    assert stored["horizon"]["autonomy_governance_gap"] == 3.0
    assert stored["horizon"]["governance_margin"] == -3.0
    assert stored["signal_counts"] == {"total":6,"breach":6,"clear":0,"not_applicable":0}
    assert stored["overall_level"] == "critical"
    assert stored["recommended_escalation"] == "urgent_human_review"
    assert stored["non_authoritative"] is True
