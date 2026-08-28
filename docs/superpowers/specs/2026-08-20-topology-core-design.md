# CTCL-ITR v0.2 Topology Core Design

## Goal

Add a dependency-free Python topology analyzer for ATL event ledgers so CTCL-ITR can compute causal work, critical depth/path, branch/join structure, and exact finite-poset width from `causal_parent_ids[]`.

## Scope

This slice implements only the topology core. OpenTelemetry export, CloudEvents delivery, hash chaining, and human approval queue are explicitly deferred to separate versions.

## Architecture

The canonical input remains ATL JSONL. `src/ctcl_itr/topology.py` parses events into immutable lightweight records, validates event identity and causal consistency, constructs an adjacency representation, and exposes a pure `analyze_events()` API. The analyzer is runtime-neutral: it does not execute agents and never mutates the ledger.

The critical-path calculation uses node-weighted longest path on a DAG. Supported weight contracts are `unit` and `machine_runtime_ms`. `unit` assigns weight 1 to every event; `machine_runtime_ms` reads `event.budget.machine_runtime_ms` and defaults missing values to 0.

Exact finite-poset width is computed with Dilworth's theorem: compute reachability, build the bipartite comparability graph, find a maximum matching, and return `|V| - |M|`. This is intentionally positioned as an analyzer for bounded traces rather than a streaming algorithm for million-node production ledgers.

## Event-schema extension

v0.2 keeps `causal_parent_ids[]` as the canonical hard happens-before relation and adds optional topology metadata:

- `branch_id: string | null`
- `parallel_group: string | null`
- `join_semantics: null | all | any | quorum | evidence_merge`
- `join_quorum: integer | null`

`join_quorum` is only meaningful when `join_semantics == quorum`. The analyzer itself derives structural joins from in-degree and does not trust metadata to determine graph correctness.

## Analysis output

`TopologyAnalysis` returns:

- `event_count`
- `edge_count`
- `roots[]`
- `leaves[]`
- `branch_nodes[]` where out-degree > 1
- `join_nodes[]` where in-degree > 1
- `work`
- `depth`
- `critical_path[]`
- `structural_parallelism = work / depth` when depth > 0
- `poset_width`
- `weight_contract`

Tie-breaking for equally long critical paths is deterministic by `(ledger_seq, event_id)`.

## Error semantics

The analyzer raises `TopologyError` for:

- duplicate `event_id`
- duplicate `ledger_seq`
- unknown causal parent
- self-parent
- cycle
- unsupported weight contract
- negative machine runtime

Storage order is not treated as causal order. A parent may appear later in JSONL storage order and still be valid as long as the final graph is acyclic; the analyzer resolves by IDs, not file position.

## CLI

`python -m ctcl_itr.topology PATH --weight unit|machine_runtime_ms --pretty`

The CLI emits JSON and returns non-zero on invalid topology.

## Reference demo

`examples/multi_agent_branch_join.events.jsonl` contains three sibling Agent branches with different machine runtimes, followed by an `all` join, validation, commit confirmation, and run success. Expected topology:

- structural branch width: 3
- one structural join
- critical branch under machine runtime: branch B
- machine-runtime work: 1850 ms
- machine-runtime depth: 1100 ms
- exact poset width: 3

## Testing

Tests are written before implementation. They cover:

1. branch/join metrics under unit weights;
2. machine-runtime work/depth and critical-path selection;
3. exact poset width for chain and independent-branch cases;
4. unknown-parent rejection;
5. cycle rejection;
6. duplicate-ID rejection;
7. deterministic critical-path tie-breaking;
8. JSONL loader and CLI-compatible analysis output.

## Compatibility

v0.1 ledgers remain valid because all schema additions are optional. No v0.1 field is renamed or semantically changed.
