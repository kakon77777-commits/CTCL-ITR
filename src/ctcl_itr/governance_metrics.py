"""Read-only governance observability metrics for CTCL-ITR v0.2.5."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import math
from typing import Any, Iterable

from .governance import _parse_time


class GovernanceMetricsError(ValueError):
    """Raised when governance metric inputs are structurally inconsistent."""


RISK_CLASSES = ("low", "medium", "high", "critical")


def default_metrics_policy() -> dict[str, Any]:
    return {
        "risk_weights": {"low": 1.0, "medium": 2.0, "high": 4.0, "critical": 8.0},
        "debt_multipliers": {
            "unresolved": 1.0,
            "overdue": 1.0,
            "deferred": 0.5,
            "stale_authority": 1.0,
        },
        "effective_transition_types": [
            "action.completed",
            "validation.completed",
            "commit.confirmed",
            "human.checkpoint.resolved",
        ],
        "closing_decisions": ["approve", "deny", "modify", "cancel"],
    }


def _ms(delta) -> int:
    return int(round(delta.total_seconds() * 1000.0))


def _ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den


def _nearest_rank(values: list[int], quantile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(quantile * len(ordered)))
    return ordered[rank - 1]


def _unique_by(items: Iterable[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        if key not in item:
            raise GovernanceMetricsError(f"{label} missing {key}")
        value = str(item[key])
        if value in out:
            raise GovernanceMetricsError(f"duplicate {key}: {value}")
        out[value] = item
    return out


def _normalize_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    base = default_metrics_policy()
    if policy is None:
        return base
    merged = deepcopy(base)
    for key, value in policy.items():
        if key in {"risk_weights", "debt_multipliers"}:
            merged[key].update(deepcopy(value))
        else:
            merged[key] = deepcopy(value)
    for risk in RISK_CLASSES:
        if risk not in merged["risk_weights"]:
            raise GovernanceMetricsError(f"missing risk weight: {risk}")
        if float(merged["risk_weights"][risk]) < 0:
            raise GovernanceMetricsError("risk weights must be nonnegative")
    for name in ("unresolved", "overdue", "deferred", "stale_authority"):
        if name not in merged["debt_multipliers"]:
            raise GovernanceMetricsError(f"missing debt multiplier: {name}")
        if float(merged["debt_multipliers"][name]) < 0:
            raise GovernanceMetricsError("debt multipliers must be nonnegative")
    return merged


def analyze_governance(
    *,
    approval_requests: list[dict[str, Any]],
    decision_receipts: list[dict[str, Any]],
    authority_grants: list[dict[str, Any]],
    events: list[dict[str, Any]] | None,
    at: str,
    intervention_deadlines: dict[str, str] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute read-only governance observability metrics.

    The function never mutates inputs or governance state. All scalar weights are
    emitted in the returned policy so results remain measurement-contract explicit.
    """

    metric_policy = _normalize_policy(policy)
    risk_weights = {k: float(v) for k, v in metric_policy["risk_weights"].items()}
    debt_multipliers = {k: float(v) for k, v in metric_policy["debt_multipliers"].items()}
    effective_types = set(metric_policy["effective_transition_types"])
    closing_decisions = set(metric_policy["closing_decisions"])
    now = _parse_time(at)
    deadlines = intervention_deadlines or {}

    requests_by_id = _unique_by(approval_requests, "approval_id", "approval request")
    receipts_by_id = _unique_by(decision_receipts, "decision_id", "decision receipt")
    grants_by_id = _unique_by(authority_grants, "authority_ref", "authority grant")

    receipt_by_approval: dict[str, dict[str, Any]] = {}
    for receipt in decision_receipts:
        approval_id = str(receipt.get("approval_id", ""))
        if approval_id not in requests_by_id:
            raise GovernanceMetricsError(f"receipt references unknown approval_id: {approval_id}")
        if approval_id in receipt_by_approval:
            raise GovernanceMetricsError(f"multiple receipts for approval_id: {approval_id}")
        receipt_by_approval[approval_id] = receipt

    receipt_to_approval = {r["decision_id"]: r["approval_id"] for r in decision_receipts}
    for grant in authority_grants:
        decision_id = str(grant.get("decision_id", ""))
        if decision_id not in receipts_by_id:
            raise GovernanceMetricsError(f"grant references unknown decision_id: {decision_id}")

    deadline_info: dict[str, tuple[datetime, str]] = {}
    for approval_id, req in requests_by_id.items():
        requested_at = _parse_time(req["requested_at"])
        if approval_id in deadlines:
            deadline = _parse_time(deadlines[approval_id])
            basis = "explicit_intervention_deadline"
        else:
            deadline = _parse_time(req["expires_at"])
            basis = "approval_expiry_proxy"
        try:
            if deadline <= requested_at:
                raise GovernanceMetricsError(f"deadline must be after requested_at: {approval_id}")
            _ = now - requested_at
        except TypeError as exc:
            raise GovernanceMetricsError("datetime timezone-awareness mismatch") from exc
        deadline_info[approval_id] = (deadline, basis)

    # Human Intervention Density.
    event_list = list(events or [])
    effective_transition_count = sum(1 for event in event_list if event.get("event_type") in effective_types)
    human_intervention_count = sum(1 for event in event_list if event.get("event_type") == "human.checkpoint.resolved")
    hid_value = _ratio(human_intervention_count, effective_transition_count)

    timing_items: list[dict[str, Any]] = []
    latency_values: list[int] = []
    effective_ids: set[str] = set()
    closing_ids: set[str] = set()
    open_ids: set[str] = set()
    deferred_ids: set[str] = set()
    overdue_ids: set[str] = set()

    for approval_id in sorted(requests_by_id):
        req = requests_by_id[approval_id]
        requested = _parse_time(req["requested_at"])
        deadline, basis = deadline_info[approval_id]
        receipt = receipt_by_approval.get(approval_id)
        risk_class = req["risk_class"]
        if risk_class not in risk_weights:
            raise GovernanceMetricsError(f"unknown risk_class: {risk_class}")

        decision_id = None
        decision = None
        latency_ms = None
        timing_ratio = None
        margin_ms = None
        timely = False
        open_age_ms = None

        if receipt is not None:
            decision_id = receipt["decision_id"]
            decision = receipt["decision"]
            decided = _parse_time(receipt["decided_at"])
            latency_ms = _ms(decided - requested)
            latency_values.append(latency_ms)
            window_ms = _ms(deadline - requested)
            timing_ratio = latency_ms / window_ms
            margin_ms = _ms(deadline - decided)
            timely = decided <= deadline
            if decision in closing_decisions:
                closing_ids.add(approval_id)
                if timely:
                    effective_ids.add(approval_id)
            else:
                open_ids.add(approval_id)
                if decision == "defer":
                    deferred_ids.add(approval_id)
        else:
            open_ids.add(approval_id)
            open_age_ms = _ms(now - requested)

        if approval_id in open_ids and open_age_ms is None:
            open_age_ms = _ms(now - requested)
        if approval_id in open_ids and now > deadline:
            overdue_ids.add(approval_id)

        timing_items.append(
            {
                "approval_id": approval_id,
                "decision_id": decision_id,
                "decision": decision,
                "risk_class": risk_class,
                "requested_at": req["requested_at"],
                "deadline_at": deadline.isoformat(),
                "timing_basis": basis,
                "latency_ms": latency_ms,
                "timing_ratio": timing_ratio,
                "margin_ms": margin_ms,
                "timely": timely,
                "open_age_ms": open_age_ms,
            }
        )

    opportunity_weight = sum(risk_weights[requests_by_id[approval_id]["risk_class"]] for approval_id in requests_by_id)
    effective_weight = sum(risk_weights[requests_by_id[approval_id]["risk_class"]] for approval_id in effective_ids)

    # Operational Oversight Debt vector.
    unresolved_weight = sum(risk_weights[requests_by_id[approval_id]["risk_class"]] for approval_id in open_ids)
    overdue_weight = sum(risk_weights[requests_by_id[approval_id]["risk_class"]] for approval_id in overdue_ids)
    deferred_weight = sum(risk_weights[requests_by_id[approval_id]["risk_class"]] for approval_id in deferred_ids)

    stale_authority_weight = 0.0
    stale_authority_refs: list[str] = []
    for authority_ref, grant in grants_by_id.items():
        if grant.get("state") != "active":
            continue
        if now <= _parse_time(grant["expires_at"]):
            continue
        approval_id = receipt_to_approval[grant["decision_id"]]
        stale_authority_weight += risk_weights[requests_by_id[approval_id]["risk_class"]]
        stale_authority_refs.append(authority_ref)

    total_debt = (
        unresolved_weight * debt_multipliers["unresolved"]
        + overdue_weight * debt_multipliers["overdue"]
        + deferred_weight * debt_multipliers["deferred"]
        + stale_authority_weight * debt_multipliers["stale_authority"]
    )

    # Human time.
    governance_times = [int(r.get("human_governance_ms", 0)) for r in decision_receipts]
    active_times = [int(r.get("human_active_ms", 0)) for r in decision_receipts]
    human_count = len(decision_receipts)

    # Risk-class coverage.
    risk_coverage: dict[str, Any] = {}
    for risk in RISK_CLASSES:
        ids = [approval_id for approval_id, req in requests_by_id.items() if req["risk_class"] == risk]
        count = len(ids)
        effective_count = sum(1 for approval_id in ids if approval_id in effective_ids)
        closed_count = sum(1 for approval_id in ids if approval_id in closing_ids)
        open_count = sum(1 for approval_id in ids if approval_id in open_ids)
        class_weight = risk_weights[risk] * count
        class_effective_weight = risk_weights[risk] * effective_count
        risk_coverage[risk] = {
            "opportunities": count,
            "effective": effective_count,
            "closed": closed_count,
            "open": open_count,
            "opportunity_weight": class_weight,
            "effective_weight": class_effective_weight,
            "weighted_coverage": None if class_weight == 0 else class_effective_weight / class_weight,
        }

    mean_latency = None if not latency_values else sum(latency_values) / len(latency_values)
    mean_governance = None if human_count == 0 else sum(governance_times) / human_count
    mean_active = None if human_count == 0 else sum(active_times) / human_count

    return {
        "schema_version": "0.2.5",
        "observed_at": at,
        "policy": deepcopy(metric_policy),
        "human_intervention_density": {
            "value": hid_value,
            "human_intervention_count": human_intervention_count,
            "effective_transition_count": effective_transition_count,
        },
        "effective_oversight_density": {
            "value": None if opportunity_weight == 0 else effective_weight / opportunity_weight,
            "effective_weight": effective_weight,
            "opportunity_weight": opportunity_weight,
            "effective_approval_ids": sorted(effective_ids),
        },
        "escalation_latency": {
            "count": len(latency_values),
            "mean_ms": mean_latency,
            "p50_ms": _nearest_rank(latency_values, 0.50),
            "p95_ms": _nearest_rank(latency_values, 0.95),
            "max_ms": None if not latency_values else max(latency_values),
        },
        "intervention_timing": {
            "timely_count": sum(1 for item in timing_items if item["decision_id"] is not None and item["timely"]),
            "late_count": sum(1 for item in timing_items if item["decision_id"] is not None and not item["timely"]),
            "open_count": len(open_ids),
            "items": timing_items,
        },
        "oversight_debt": {
            "unresolved_weight": unresolved_weight,
            "overdue_weight": overdue_weight,
            "deferred_weight": deferred_weight,
            "stale_authority_weight": stale_authority_weight,
            "total_weight": total_debt,
            "unresolved_approval_ids": sorted(open_ids),
            "overdue_approval_ids": sorted(overdue_ids),
            "deferred_approval_ids": sorted(deferred_ids),
            "stale_authority_refs": sorted(stale_authority_refs),
        },
        "human_time": {
            "decision_count": human_count,
            "human_governance_ms_total": sum(governance_times),
            "human_governance_ms_mean": mean_governance,
            "human_active_ms_total": sum(active_times),
            "human_active_ms_mean": mean_active,
        },
        "risk_coverage": risk_coverage,
        "counts": {
            "approval_requests": len(approval_requests),
            "decision_receipts": len(decision_receipts),
            "authority_grants": len(authority_grants),
            "events": len(event_list),
            "closing_decisions": len(closing_ids),
            "open_obligations": len(open_ids),
        },
    }


def _load_jsonl_events(path: str) -> list[dict[str, Any]]:
    import json
    from pathlib import Path

    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _main() -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="CTCL-ITR governance observability metrics")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--scenario", help="scenario JSON containing governance objects and optional events")
    source.add_argument("--db", help="durable governance SQLite database")
    parser.add_argument("--events", help="optional ATL/minimal event JSONL for DB mode")
    parser.add_argument("--deadlines", help="optional JSON object mapping approval_id to intervention deadline")
    parser.add_argument("--at", help="observation timestamp; required for DB mode, overrides scenario observed_at")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        if args.scenario:
            scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
            report = analyze_governance(
                approval_requests=scenario["approval_requests"],
                decision_receipts=scenario["decision_receipts"],
                authority_grants=scenario["authority_grants"],
                events=scenario.get("events", []),
                at=args.at or scenario["observed_at"],
                intervention_deadlines=scenario.get("intervention_deadlines", {}),
                policy=scenario.get("policy"),
            )
        else:
            if not args.at:
                parser.error("--at is required with --db")
            from .governance_store import SQLiteApprovalQueue

            store = SQLiteApprovalQueue(args.db)
            try:
                approval_requests = store.list_requests()
                decision_receipts = store.list_receipts()
                authority_grants = store.list_grants()
            finally:
                store.close()
            events = _load_jsonl_events(args.events) if args.events else []
            deadlines = {}
            if args.deadlines:
                deadlines = json.loads(Path(args.deadlines).read_text(encoding="utf-8"))
            report = analyze_governance(
                approval_requests=approval_requests,
                decision_receipts=decision_receipts,
                authority_grants=authority_grants,
                events=events,
                at=args.at,
                intervention_deadlines=deadlines,
            )
    except (OSError, KeyError, json.JSONDecodeError, GovernanceMetricsError, ValueError) as exc:
        parser.exit(2, f"governance metrics error: {exc}\n")

    if args.pretty:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    _main()
