# CTCL-ITR v0.2.6 — Governance Horizon & Escalation Signals

**Date:** 2026-08-21

v0.2.6 adds a read-only signal layer above v0.2.5 governance observability. It compares externally assessed Autonomy and Governance Horizons under one explicit measurement contract and projects directional governance breaches into advisory escalation signals.

## Added

- `ctcl_itr.governance_signals`
- `ctcl-itr-governance-signals` CLI
- explicit Governance Horizon assessment contract
- Autonomy–Governance Gap and Governance Margin
- six directional governance signals
- explicit intervention-deadline breach detection
- Draft 2020-12 Horizon/policy/report schemas
- canonical reference assessment/policy/report
- dedicated validator and TDD regression suite

## Core boundary

```text
Observation != Authority
Metric != Policy Decision
Signal != Authority
Signal != Automatic Enforcement
```

Horizon values are independent assessment inputs under one declared measurement contract; v0.2.6 does not infer Governance Horizon from one p95 latency.

## Reference result

```text
H_A = 12
H_G = 9
Delta_AG = 3
M_G = -3
signal_breaches = 6
overall_level = critical
recommended_escalation = urgent_human_review
non_authoritative = true
```
