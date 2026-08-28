# CTCL-ITR v0.2.4 — Durable Governance Store

**Date:** 2026-08-20

v0.2.4 makes the v0.2.3 governance semantics restart-safe with a SQLite reference store.

## Added

- `ctcl_itr.governance_store.SQLiteApprovalQueue`
  - persistent ApprovalRequest queue;
  - persistent DecisionReceipt storage;
  - persistent AuthorityGrant state;
  - restart-safe use counters, revocation, and expiration;
  - deterministic pending-order query;
  - context-manager / explicit close support.
- transaction safety
  - multi-object `resolve()` uses one transaction;
  - invalid grant aborts request status + receipt + grant together;
  - authority consume/revoke uses `BEGIN IMMEDIATE` reference locking;
  - expired-authority state is committed before the rejection is returned.
- durability metadata
  - per-object `state_version` in SQLite;
  - append-only `governance_mutations` journal;
  - SQLite triggers reject journal UPDATE/DELETE.
- SQLite reference profile
  - foreign keys enabled;
  - WAL journal mode;
  - synchronous FULL.
- CLI
  - `ctcl-itr-governance-store demo --db <path>`;
  - `ctcl-itr-governance-store status --db <path>`.
- reference DDL
  - `sql/governance_store.sql`.

## Core boundary

```text
Governance semantics != Governance persistence
ATL canonical event history != SQLite governance state projection
```

v0.2.4 does not change ApprovalRequest, DecisionReceipt, AuthorityGrant, or TemporalEvent schemas. It changes where runtime governance state can survive.

## Recovery invariant

After closing and reopening the same database, a runtime must recover:

- pending/settled approval state;
- decision receipt;
- authority state;
- authority use count;
- revocation/expiration state;
- mutation journal.

## Transaction invariant

```text
resolve(decision, grant)
= all committed OR none committed
```

This prevents a crash/error from leaving an approval marked approved without its receipt or grant.

## Non-goals

- distributed consensus;
- multi-node leases/fencing;
- remote SQL service support;
- governance-policy metrics;
- signed decision receipts.

## Next

A natural next slice is governance observability/metrics: escalation latency, effective oversight density, intervention timing, and oversight debt, while keeping those analytics separate from the durable state machine.
