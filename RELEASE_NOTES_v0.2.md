# CTCL-ITR v0.2.0 — Topology Core

**Date:** 2026-08-20

v0.2.0 turns ATL's existing multi-parent causal field into an executable topology-analysis layer.

## Added

- dependency-free Python package `ctcl_itr`
- causal DAG validation
- branch-node and join-node detection
- node-weighted Interaction Work
- weighted Critical Depth / Span
- deterministic Critical Path reconstruction
- Structural Parallelism `Work / Depth`
- exact finite-poset width via Dilworth's theorem
- `unit` and `machine_runtime_ms` weight contracts
- `ctcl-itr-topology` CLI / `python -m ctcl_itr.topology`
- 12-event multi-agent branch/join reference ledger
- optional `branch_id`, `parallel_group`, `join_semantics`, `join_quorum` event fields
- v0.2 validation coverage while preserving v0.1 event compatibility

## Reference multi-agent result

For `examples/multi_agent_branch_join.events.jsonl` with `machine_runtime_ms` weights:

```text
work = 1850 ms
depth = 1100 ms
poset_width = 3
branch_nodes = [evt_004]
join_nodes = [evt_008]
critical branch includes evt_006 (Agent B)
```

This demonstrates the central distinction:

```text
Total Work != Critical Depth
```

## Compatibility

Existing v0.1 ledgers remain valid. v0.2 only widens the accepted `schema_version` set and adds optional topology metadata.

## Deferred

The following remain separate follow-up slices rather than being mixed into the topology core:

- OpenTelemetry exporter
- CloudEvents adapter
- event hash chain
- human approval queue
