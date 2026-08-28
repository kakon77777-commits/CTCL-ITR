# CTCL-ITR v0.2.3 — Governance Core

**Date:** 2026-08-20

v0.2.3 turns human checkpoints into explicit governance objects and bounded authority transitions while preserving the canonical ATL TemporalEvent contract.

## Added

- `ctcl_itr.governance`
  - `ApprovalRequest` builder
  - `DecisionReceipt` builder
  - `AuthorityGrant` builder
  - deterministic in-memory `ApprovalQueue`
  - request expiration
  - authority consumption and revocation
  - structured resume-eligibility evaluation
- JSON Schema Draft 2020-12 contracts
  - `approval-request.schema.json`
  - `decision-receipt.schema.json`
  - `authority-grant.schema.json`
- CLI
  - `ctcl-itr-governance-demo demo`
- committed reference governance objects
- committed 5-event ATL checkpoint handoff
- pack validation for governance linkage and scope enforcement

## Core separation

```text
ApprovalRequest != DecisionReceipt != AuthorityGrant != Run Resume
```

An `approve` decision is not itself permission to perform an arbitrary action. The runtime must evaluate the resulting authority grant against the requested action, target, expiry, revocation state, and remaining use count.

## Decision states

```text
pending -> approved | denied | modified | deferred | cancelled | expired
```

## Authority states

```text
active -> consumed | revoked | expired
```

## Resume contract

A reference run is resume-eligible only when:

1. the DecisionReceipt is `approve` or compatible `modify`;
2. an AuthorityGrant is present and linked to that decision;
3. the grant is active;
4. the grant is unexpired and unrevoked;
5. the action is in scope;
6. the target matches;
7. `uses < max_uses`.

The evaluator returns explicit rejection reasons such as `scope_mismatch`, `target_mismatch`, `authority_expired`, `authority_revoked`, and `authority_exhausted`.

## Human time

Decision receipts retain both:

```text
human_active_ms
human_governance_ms
```

so governance cost does not collapse into Agent wall-clock duration.

## Compatibility

- v0.1 TemporalEvent schema remains unchanged.
- v0.2.0 topology remains unchanged.
- v0.2.1 observability adapters remain unchanged.
- v0.2.2 ledger integrity can hash governance events exactly like other ATL events.

## Non-goals

- no Slack/Gmail/UI transport;
- no distributed approval service;
- no cryptographic proof of human identity;
- no multi-party quorum;
- no general policy engine;
- no replacement of AICL or organization-specific authorization systems.

## Next

v0.2.4 should connect governance objects to durable persistence / queue storage or introduce reusable governance-policy artifacts and escalation metrics, without mixing those concerns into the v0.2.3 semantic core.
