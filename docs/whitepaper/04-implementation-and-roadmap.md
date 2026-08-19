# Part 4 — Implementation and Roadmap

This GitHub projection condenses sections 81–100 of the canonical v0.1 whitepaper. The complete canonical source is included in the downloadable release pack.

## Core service contracts

Authority resolver:

```text
check(principal, action, target, context)
→ allow | deny | step_up | expired
```

Commit adapter:

```text
propose(candidate)
authorize(authority)
execute(execution_key)
confirm(external_state)
compensate(reason)
```

Every authority decision and commit state transition should emit a ledger event.

## Replay and schema evolution

Replaying the same ledger without re-executing external effects should produce the same state projection. Divergent replay is a projection bug.

Every canonical object carries `schema_version`. Core schemas use `additionalProperties: false`; vendor-specific additions belong under an `extensions` namespace.

## Security profile

The ledger should defend against:

- path traversal
- duplicate or spoofed event IDs
- authority substitution
- artifact tampering
- replay attacks
- secret leakage
- cross-run contamination

Run state is isolated. Content-addressed artifacts may be reused globally, while provenance observations remain run-relative.

## Reference acceptance tests

v0.1 requires at least:

1. Draft 2020-12 schemas load successfully.
2. Example intent, run, checkpoint, commit receipt, and run summary validate.
3. Every JSONL event validates.
4. Event IDs are unique.
5. Ledger sequence is monotonic.
6. Causal parents resolve.
7. Human approval precedes external commit.
8. Validation pass precedes run success.
9. Commit confirmation precedes run success.
10. SQLite event rows reject UPDATE and DELETE.

## MVP stack

The first implementation only needs:

```text
SQLite
+ JSON / JSONL
+ JSON Schema
+ Python validator
```

The goal is to prove semantics before scaling infrastructure.

## Roadmap

### v0.2
- multi-agent branch / join demo
- critical-path calculator
- OpenTelemetry exporter
- CloudEvents adapter
- event hash chain
- human approval queue

### v0.3
- distributed workers and fencing
- cross-process resume
- external commit reconciliation
- PHOSPHOR timeline / DAG UI
- autonomy-horizon and governance-horizon metrics

### v0.4
- multi-runtime federation
- ISF / WDC / CTCL / AICL adapters
- durable world-commit receipts
- historical-sedimentation aggregation

## Mapping to the eight-paper theory series

```text
01 Interaction Time        → typed events / causality
02 Intent Cycle            → intent identity / version
03 Execution Trajectory    → run / attempt / loop / action
04 Interaction Topology    → causal parents / depth
05 Compute Economics       → budget ledger
06 Delegated Time          → human checkpoints / authority
07 Single-Run Quality      → quality / completion / validation
08 World Time              → commit receipts / world confirmation
```

## Minimum irreducible core

Even if advanced features are removed, CTCL-ITR v0.1 must retain:

```text
append-only event
causal parent
typed time
run identity
artifact reference
validation
budget
human checkpoint
authority
commit receipt
```

> Agent time becomes useful infrastructure only when it can be reconstructed, verified, governed, and connected to real-world effects.
