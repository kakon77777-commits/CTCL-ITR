from copy import deepcopy
import json
from pathlib import Path

import pytest

from ctcl_itr.governance_signals import (
    GovernanceSignalError,
    analyze_governance_signals,
    default_signal_policy,
)

ROOT = Path(__file__).resolve().parents[1]


def _metrics():
    return json.loads((ROOT / "examples/governance_metrics_report.json").read_text(encoding="utf-8"))


def _horizon(autonomy=12.0, governance=9.0, reliability=0.90):
    return {
        "schema_version": "0.2.6",
        "assessment_id": "horizon:reference",
        "assessed_at": "2026-08-21T12:00:00+00:00",
        "measurement_contract": {
            "unit": "interaction_depth",
            "reliability_p": reliability,
            "scope_id": "reference-governance-scope",
            "assessment_method": "external_benchmark_assessment",
        },
        "autonomy_horizon_depth": autonomy,
        "governance_horizon_depth": governance,
        "evidence_refs": ["evidence:autonomy", "evidence:governance"],
    }


def _signals_by_code(report):
    return {item["code"]: item for item in report["signals"]}


def test_reference_horizon_gap_and_six_directional_breaches():
    report = analyze_governance_signals(
        metrics_report=_metrics(),
        horizon_assessment=_horizon(),
        policy=default_signal_policy(),
    )

    assert report["horizon"]["autonomy_horizon_depth"] == 12.0
    assert report["horizon"]["governance_horizon_depth"] == 9.0
    assert report["horizon"]["autonomy_governance_gap"] == 3.0
    assert report["horizon"]["governance_margin"] == -3.0

    signals = _signals_by_code(report)
    assert set(signals) == {
        "autonomy_governance_gap",
        "effective_oversight_density_low",
        "oversight_debt_high",
        "escalation_latency_p95_high",
        "explicit_intervention_deadline_breach",
        "critical_oversight_coverage_low",
    }
    assert all(item["status"] == "breach" for item in signals.values())
    assert signals["explicit_intervention_deadline_breach"]["observed"] == 1
    assert signals["critical_oversight_coverage_low"]["observed"] == 0.0
    assert report["overall_level"] == "critical"
    assert report["recommended_escalation"] == "urgent_human_review"
    assert report["non_authoritative"] is True


def test_hid_is_context_not_a_threshold_signal():
    report = analyze_governance_signals(
        metrics_report=_metrics(),
        horizon_assessment=_horizon(),
        policy=default_signal_policy(),
    )
    assert report["context_metrics"]["human_intervention_density"] == 4 / 9
    assert "human_intervention_density" not in _signals_by_code(report)


def test_explicit_deadline_breach_does_not_count_expiry_proxy_miss():
    report = analyze_governance_signals(
        metrics_report=_metrics(),
        horizon_assessment=_horizon(),
        policy=default_signal_policy(),
    )
    signal = _signals_by_code(report)["explicit_intervention_deadline_breach"]
    assert signal["observed"] == 1
    assert signal["evidence_ids"] == ["approval:c1"]


def test_clear_profile_has_no_escalation():
    metrics = _metrics()
    metrics["observed_at"] = "2026-08-20T08:10:00+00:00"
    metrics["effective_oversight_density"]["value"] = 0.90
    metrics["oversight_debt"]["total_weight"] = 2.0
    metrics["escalation_latency"]["p95_ms"] = 600000
    metrics["risk_coverage"]["critical"]["weighted_coverage"] = 1.0

    report = analyze_governance_signals(
        metrics_report=metrics,
        horizon_assessment=_horizon(autonomy=5.0, governance=8.0),
        policy=default_signal_policy(),
    )

    assert report["horizon"]["autonomy_governance_gap"] == -3.0
    assert report["horizon"]["governance_margin"] == 3.0
    assert all(item["status"] == "clear" for item in report["signals"])
    assert report["overall_level"] == "clear"
    assert report["recommended_escalation"] == "none"


def test_invalid_horizon_contract_is_rejected():
    with pytest.raises(GovernanceSignalError, match="reliability_p"):
        analyze_governance_signals(
            metrics_report=_metrics(),
            horizon_assessment=_horizon(reliability=1.1),
            policy=default_signal_policy(),
        )

    with pytest.raises(GovernanceSignalError, match="nonnegative"):
        analyze_governance_signals(
            metrics_report=_metrics(),
            horizon_assessment=_horizon(autonomy=-1.0),
            policy=default_signal_policy(),
        )

    bad_unit = _horizon()
    bad_unit["measurement_contract"]["unit"] = "milliseconds"
    with pytest.raises(GovernanceSignalError, match="interaction_depth"):
        analyze_governance_signals(
            metrics_report=_metrics(),
            horizon_assessment=bad_unit,
            policy=default_signal_policy(),
        )


def test_inputs_are_not_mutated():
    metrics = _metrics()
    horizon = _horizon()
    policy = default_signal_policy()
    originals = (deepcopy(metrics), deepcopy(horizon), deepcopy(policy))

    analyze_governance_signals(
        metrics_report=metrics,
        horizon_assessment=horizon,
        policy=policy,
    )

    assert metrics == originals[0]
    assert horizon == originals[1]
    assert policy == originals[2]
