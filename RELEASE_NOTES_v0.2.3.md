# CTCL-ITR v0.2.3 — Governance Core

**Date:** 2026-08-20

v0.2.3 turns human checkpoints into explicit governance objects and bounded authority transitions while preserving the canonical ATL TemporalEvent contract.

## Core separation

```text
ApprovalRequest != DecisionReceipt != AuthorityGrant != Run Resume
```

An approval decision is not itself arbitrary execution authority. The runtime must evaluate the resulting grant against action, target, expiry, revocation state, and remaining uses.

## Added

- `ApprovalRequest`, `DecisionReceipt`, `AuthorityGrant`
- deterministic in-memory `ApprovalQueue`
- request expiration, grant consumption, revocation
- structured resume-eligibility diagnostics
- JSON Schema Draft 2020-12 contracts
- `ctcl-itr-governance-demo` reference CLI
- 5-event checkpoint handoff example

## Compatibility

TemporalEvent remains unchanged; topology, observability, and integrity semantics remain compatible.
