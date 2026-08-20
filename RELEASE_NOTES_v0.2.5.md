# CTCL-ITR v0.2.5 — Governance Observability & Oversight Metrics

**Date:** 2026-08-21

v0.2.5 adds a read-only governance diagnostics layer over ATL governance events and durable ApprovalRequest / DecisionReceipt / AuthorityGrant state.

## Added

- `ctcl_itr.governance_metrics` pure analyzer
- `ctcl-itr-governance-metrics` CLI
- durable-store read APIs: `list_requests`, `list_receipts`, `list_grants`
- Human Intervention Density (HID)
- risk-weighted Effective Oversight Density (EOD)
- escalation latency summary: mean / p50 / p95 / max
- intervention timing ratio, margin, timeliness, and deadline basis
- Oversight Debt vector: unresolved / overdue / deferred / stale authority
- policy-weighted Oversight Debt total
- human active / governance time aggregation
- per-risk oversight coverage
- JSON Schema Draft 2020-12 governance metrics report contract
- committed reference scenario + canonical report
- scenario-mode and reopened-SQLite CLI analysis

## Reference result

```text
human_intervention_density = 0.4444444444444444
effective_oversight_density = 0.3157894736842105
oversight_debt = 28.0
escalation_p95_ms = 2400000
```

## Measurement boundary

Metrics do not grant authority and do not mutate governance state.

```text
Observation != Authority
Metric != Policy Decision
```

Default risk weights (`low=1`, `medium=2`, `high=4`, `critical=8`) and debt multipliers are emitted in every report. They are measurement policy, not universal truth.

An explicit `intervention_deadline_at` is preferred for Intervention Timing. If absent, `ApprovalRequest.expires_at` is used only as an `approval_expiry_proxy`; the release does not claim that approval expiry equals harm-propagation time.

## Oversight Debt

The canonical diagnostic object is a vector:

```text
unresolved_weight
overdue_weight
deferred_weight
stale_authority_weight
```

`total_weight` is a declared-policy scalar projection. This keeps diagnosis separable from weighting assumptions.

## Compatibility

- TemporalEvent schema unchanged.
- ApprovalRequest / DecisionReceipt / AuthorityGrant schemas unchanged.
- Durable governance mutation semantics unchanged.
- v0.2.2 integrity, v0.2.1 observability, and v0.2.0 topology remain compatible.

## Next

A natural next slice is v0.2.6 governance thresholding / escalation signals or Governance Horizon metrics, kept separate from authorization semantics.

## Validation

```text
67 passed in 24.85s
validator/validate_pack.py: PASS
validator/validate_metrics.py: PASS
```
