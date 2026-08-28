# CTCL-ITR v0.2.6 — Governance Horizon & Escalation Signals

**Date:** 2026-08-21

v0.2.6 adds a read-only signal layer above v0.2.5 governance observability. It compares externally assessed Autonomy and Governance Horizons under one explicit measurement contract and projects directional governance breaches into advisory escalation signals.

## Added

- `ctcl_itr.governance_signals`
  - `analyze_governance_signals(...)`
  - `default_signal_policy()`
  - horizon contract validation
  - Autonomy–Governance Gap
  - Governance Margin
  - explicit intervention-deadline breach detection
  - deterministic signal severity aggregation
- CLI
  - `ctcl-itr-governance-signals`
- JSON Schema Draft 2020-12 contracts
  - `governance-horizon-assessment.schema.json`
  - `governance-escalation-policy.schema.json`
  - `governance-signal-report.schema.json`
- canonical reference artifacts
  - `governance_horizon_assessment.json`
  - `governance_escalation_policy.json`
  - `governance_signal_report.json`
- dedicated signal validator and TDD regression suite.

## Horizon boundary

v0.2.6 does **not** infer Governance Horizon from p95 latency or from one governance run. Horizon values enter through an explicit assessment contract:

```text
unit = interaction_depth
reliability_p
scope_id
assessment_method
```

Derived values:

```text
Delta_AG = H_A - H_G
M_G = H_G - H_A
```

For the reference assessment:

```text
H_A = 12
H_G = 9
Delta_AG = 3
M_G = -3
```

## Signals

The reference policy evaluates six directional conditions:

1. `autonomy_governance_gap`
2. `effective_oversight_density_low`
3. `oversight_debt_high`
4. `escalation_latency_p95_high`
5. `explicit_intervention_deadline_breach`
6. `critical_oversight_coverage_low`

Human Intervention Density remains contextual and receives no default breach threshold.

## Explicit intervention deadlines

Only v0.2.5 timing entries whose `timing_basis` is `explicit_intervention_deadline` count as harm-deadline breaches. `approval_expiry_proxy` misses remain observable but are not relabeled as known harm-propagation failures.

## Authority boundary

```text
Observation != Authority
Metric != Policy Decision
Signal != Authority
Signal != Automatic Enforcement
```

`recommended_escalation` is an advisory projection only. v0.2.6 does not mutate ApprovalRequest, DecisionReceipt, AuthorityGrant, SQLite governance state, or ATL history.

## Reference policy result

```text
autonomy_governance_gap = 3.0
signal_breaches = 6
overall_level = critical
recommended_escalation = urgent_human_review
non_authoritative = true
```

## Compatibility

- TemporalEvent schema unchanged.
- Governance object schemas unchanged.
- Durable governance mutation semantics unchanged.
- v0.2.5 metrics report remains the observability input.
- v0.2.4 store, v0.2.2 integrity, v0.2.1 observability, and v0.2.0 topology remain compatible.

## Next

A natural next slice is evidence-backed Horizon calibration / repeated assessment, or signal-to-human-escalation routing with a strict separation between signal generation and authorization.
