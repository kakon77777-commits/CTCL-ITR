"""Read-only Governance Horizon and escalation signals for CTCL-ITR v0.2.6."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .governance import _parse_time


class GovernanceSignalError(ValueError):
    """Raised when a governance signal input contract is invalid."""


SEVERITY_ORDER = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

ESCALATION_BY_LEVEL = {
    "clear": "none",
    "info": "watch",
    "low": "watch",
    "medium": "review",
    "high": "priority_review",
    "critical": "urgent_human_review",
}

SIGNAL_CODES = (
    "autonomy_governance_gap",
    "effective_oversight_density_low",
    "oversight_debt_high",
    "escalation_latency_p95_high",
    "explicit_intervention_deadline_breach",
    "critical_oversight_coverage_low",
)


def default_signal_policy() -> dict[str, Any]:
    """Return the v0.2.6 reference threshold policy.

    The policy is a diagnostic measurement contract. It carries no authority.
    """

    return {
        "schema_version": "0.2.6",
        "policy_id": "policy:governance-signals:reference",
        "thresholds": {
            "max_autonomy_governance_gap": 0.0,
            "min_effective_oversight_density": 0.50,
            "max_oversight_debt": 20.0,
            "max_escalation_p95_ms": 1_800_000,
            "max_explicit_deadline_breaches": 0,
            "min_critical_oversight_coverage": 0.75,
        },
        "severities": {
            "autonomy_governance_gap": "critical",
            "effective_oversight_density_low": "high",
            "oversight_debt_high": "high",
            "escalation_latency_p95_high": "medium",
            "explicit_intervention_deadline_breach": "critical",
            "critical_oversight_coverage_low": "critical",
        },
    }


def _as_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise GovernanceSignalError(f"{label} must be numeric") from exc
    return result


def _validate_horizon(assessment: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(assessment, dict):
        raise GovernanceSignalError("horizon assessment must be an object")
    contract = assessment.get("measurement_contract")
    if not isinstance(contract, dict):
        raise GovernanceSignalError("measurement_contract is required")
    if contract.get("unit") != "interaction_depth":
        raise GovernanceSignalError("horizon unit must be interaction_depth")
    reliability = _as_float(contract.get("reliability_p"), "reliability_p")
    if not (0.0 < reliability <= 1.0):
        raise GovernanceSignalError("reliability_p must be in (0, 1]")
    for key in ("scope_id", "assessment_method"):
        if not isinstance(contract.get(key), str) or not contract[key]:
            raise GovernanceSignalError(f"measurement_contract {key} is required")
    autonomy = _as_float(assessment.get("autonomy_horizon_depth"), "autonomy_horizon_depth")
    governance = _as_float(assessment.get("governance_horizon_depth"), "governance_horizon_depth")
    if autonomy < 0 or governance < 0:
        raise GovernanceSignalError("horizon depths must be nonnegative")
    return {
        "assessment_id": assessment.get("assessment_id"),
        "assessed_at": assessment.get("assessed_at"),
        "measurement_contract": deepcopy(contract),
        "autonomy_horizon_depth": autonomy,
        "governance_horizon_depth": governance,
        "autonomy_governance_gap": autonomy - governance,
        "governance_margin": governance - autonomy,
        "evidence_refs": deepcopy(assessment.get("evidence_refs", [])),
    }


def _validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise GovernanceSignalError("signal policy must be an object")
    thresholds = policy.get("thresholds")
    severities = policy.get("severities")
    if not isinstance(thresholds, dict) or not isinstance(severities, dict):
        raise GovernanceSignalError("policy thresholds and severities are required")

    required_thresholds = {
        "max_autonomy_governance_gap",
        "min_effective_oversight_density",
        "max_oversight_debt",
        "max_escalation_p95_ms",
        "max_explicit_deadline_breaches",
        "min_critical_oversight_coverage",
    }
    missing = sorted(required_thresholds - set(thresholds))
    if missing:
        raise GovernanceSignalError(f"missing signal thresholds: {', '.join(missing)}")

    normalized = deepcopy(policy)
    normalized_thresholds = normalized["thresholds"]
    normalized_thresholds["max_autonomy_governance_gap"] = _as_float(
        thresholds["max_autonomy_governance_gap"], "max_autonomy_governance_gap"
    )
    normalized_thresholds["min_effective_oversight_density"] = _as_float(
        thresholds["min_effective_oversight_density"], "min_effective_oversight_density"
    )
    normalized_thresholds["max_oversight_debt"] = _as_float(
        thresholds["max_oversight_debt"], "max_oversight_debt"
    )
    normalized_thresholds["max_escalation_p95_ms"] = _as_float(
        thresholds["max_escalation_p95_ms"], "max_escalation_p95_ms"
    )
    normalized_thresholds["max_explicit_deadline_breaches"] = int(
        thresholds["max_explicit_deadline_breaches"]
    )
    normalized_thresholds["min_critical_oversight_coverage"] = _as_float(
        thresholds["min_critical_oversight_coverage"], "min_critical_oversight_coverage"
    )

    if normalized_thresholds["max_autonomy_governance_gap"] < 0:
        raise GovernanceSignalError("max_autonomy_governance_gap must be nonnegative")
    if normalized_thresholds["max_oversight_debt"] < 0:
        raise GovernanceSignalError("max_oversight_debt must be nonnegative")
    if normalized_thresholds["max_escalation_p95_ms"] < 0:
        raise GovernanceSignalError("max_escalation_p95_ms must be nonnegative")
    if normalized_thresholds["max_explicit_deadline_breaches"] < 0:
        raise GovernanceSignalError("max_explicit_deadline_breaches must be nonnegative")
    for key in ("min_effective_oversight_density", "min_critical_oversight_coverage"):
        if not (0.0 <= normalized_thresholds[key] <= 1.0):
            raise GovernanceSignalError(f"{key} must be in [0, 1]")

    for code in SIGNAL_CODES:
        severity = severities.get(code)
        if severity not in SEVERITY_ORDER:
            raise GovernanceSignalError(f"invalid or missing severity for {code}")
    return normalized


def _explicit_deadline_breaches(metrics_report: dict[str, Any]) -> list[str]:
    observed_at = _parse_time(metrics_report["observed_at"])
    closing_decisions = set(metrics_report.get("policy", {}).get("closing_decisions", []))
    breached: list[str] = []
    for item in metrics_report.get("intervention_timing", {}).get("items", []):
        if item.get("timing_basis") != "explicit_intervention_deadline":
            continue
        approval_id = str(item.get("approval_id", ""))
        decision = item.get("decision")
        is_closing = decision in closing_decisions
        if is_closing:
            if not bool(item.get("timely")):
                breached.append(approval_id)
            continue
        deadline_at = _parse_time(item["deadline_at"])
        if observed_at > deadline_at:
            breached.append(approval_id)
    return sorted(set(breached))


def _signal(
    *,
    code: str,
    observed: float | int | None,
    threshold: float | int,
    comparator: str,
    severity: str,
    unit: str,
    rationale: str,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    if observed is None:
        status = "not_applicable"
    elif comparator == "<=":
        status = "clear" if observed <= threshold else "breach"
    elif comparator == ">=":
        status = "clear" if observed >= threshold else "breach"
    else:  # pragma: no cover - internal programming error guard
        raise GovernanceSignalError(f"unsupported comparator: {comparator}")
    return {
        "code": code,
        "status": status,
        "severity": severity,
        "observed": observed,
        "threshold": threshold,
        "comparator": comparator,
        "unit": unit,
        "rationale": rationale,
        "evidence_ids": list(evidence_ids or []),
    }


def analyze_governance_signals(
    *,
    metrics_report: dict[str, Any],
    horizon_assessment: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Project v0.2.5 governance observations into non-authoritative signals."""

    if not isinstance(metrics_report, dict):
        raise GovernanceSignalError("metrics_report must be an object")
    if metrics_report.get("schema_version") != "0.2.5":
        raise GovernanceSignalError("metrics_report must use schema_version 0.2.5")

    horizon = _validate_horizon(deepcopy(horizon_assessment))
    signal_policy = _validate_policy(deepcopy(policy))
    thresholds = signal_policy["thresholds"]
    severities = signal_policy["severities"]

    try:
        hid = metrics_report["human_intervention_density"]["value"]
        eod = metrics_report["effective_oversight_density"]["value"]
        debt = metrics_report["oversight_debt"]["total_weight"]
        p95 = metrics_report["escalation_latency"]["p95_ms"]
        critical_coverage = metrics_report["risk_coverage"]["critical"]["weighted_coverage"]
    except (KeyError, TypeError) as exc:
        raise GovernanceSignalError("metrics_report is missing required v0.2.5 fields") from exc

    gap = horizon["autonomy_governance_gap"]
    explicit_breaches = _explicit_deadline_breaches(metrics_report)

    signals = [
        _signal(
            code="autonomy_governance_gap",
            observed=gap,
            threshold=thresholds["max_autonomy_governance_gap"],
            comparator="<=",
            severity=severities["autonomy_governance_gap"],
            unit="interaction_depth",
            rationale="Autonomy Horizon must not extend beyond the declared Governance Horizon beyond policy tolerance.",
        ),
        _signal(
            code="effective_oversight_density_low",
            observed=None if eod is None else float(eod),
            threshold=thresholds["min_effective_oversight_density"],
            comparator=">=",
            severity=severities["effective_oversight_density_low"],
            unit="ratio",
            rationale="Risk-weighted effective oversight density is below the declared governance floor.",
        ),
        _signal(
            code="oversight_debt_high",
            observed=None if debt is None else float(debt),
            threshold=thresholds["max_oversight_debt"],
            comparator="<=",
            severity=severities["oversight_debt_high"],
            unit="policy_weight",
            rationale="Outstanding governance obligations exceed the declared oversight-debt ceiling.",
        ),
        _signal(
            code="escalation_latency_p95_high",
            observed=None if p95 is None else int(p95),
            threshold=thresholds["max_escalation_p95_ms"],
            comparator="<=",
            severity=severities["escalation_latency_p95_high"],
            unit="milliseconds",
            rationale="Observed p95 human escalation latency exceeds the declared response-time ceiling.",
        ),
        _signal(
            code="explicit_intervention_deadline_breach",
            observed=len(explicit_breaches),
            threshold=thresholds["max_explicit_deadline_breaches"],
            comparator="<=",
            severity=severities["explicit_intervention_deadline_breach"],
            unit="count",
            rationale="One or more explicit intervention deadlines were missed or remained unresolved past deadline.",
            evidence_ids=explicit_breaches,
        ),
        _signal(
            code="critical_oversight_coverage_low",
            observed=None if critical_coverage is None else float(critical_coverage),
            threshold=thresholds["min_critical_oversight_coverage"],
            comparator=">=",
            severity=severities["critical_oversight_coverage_low"],
            unit="ratio",
            rationale="Critical-risk oversight coverage is below the declared minimum.",
        ),
    ]

    breached = [item for item in signals if item["status"] == "breach"]
    if breached:
        overall_level = max(breached, key=lambda item: SEVERITY_ORDER[item["severity"]])["severity"]
    else:
        overall_level = "clear"

    return {
        "schema_version": "0.2.6",
        "observed_at": metrics_report["observed_at"],
        "horizon": horizon,
        "context_metrics": {
            "human_intervention_density": hid,
            "effective_oversight_density": eod,
            "oversight_debt": debt,
            "escalation_p95_ms": p95,
            "critical_oversight_coverage": critical_coverage,
            "explicit_deadline_breaches": len(explicit_breaches),
        },
        "signals": signals,
        "signal_counts": {
            "total": len(signals),
            "breach": len(breached),
            "clear": sum(1 for item in signals if item["status"] == "clear"),
            "not_applicable": sum(1 for item in signals if item["status"] == "not_applicable"),
        },
        "overall_level": overall_level,
        "recommended_escalation": ESCALATION_BY_LEVEL[overall_level],
        "non_authoritative": True,
        "policy": deepcopy(signal_policy),
    }


def _main() -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="CTCL-ITR Governance Horizon and escalation signals")
    parser.add_argument("--metrics", required=True, help="v0.2.5 governance metrics report JSON")
    parser.add_argument("--horizon", required=True, help="GovernanceHorizonAssessment JSON")
    parser.add_argument("--policy", required=True, help="GovernanceEscalationPolicy JSON")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
        horizon = json.loads(Path(args.horizon).read_text(encoding="utf-8"))
        policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
        report = analyze_governance_signals(
            metrics_report=metrics,
            horizon_assessment=horizon,
            policy=policy,
        )
    except (OSError, json.JSONDecodeError, GovernanceSignalError, KeyError, TypeError, ValueError) as exc:
        parser.exit(2, f"governance signal error: {exc}\n")

    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    _main()
