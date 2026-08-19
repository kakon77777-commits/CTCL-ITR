# CTCL-ITR

**CTCL Interaction-Time Runtime & Agent Temporal Ledger**

A causal, temporal, auditable runtime ledger for long-horizon and multi-agent AI systems.

## Status

**v0.2.0 — Topology Core / Engineering Contract**

CTCL-ITR turns AI work from a flat `prompt → response` record into an observable execution model:

```text
Intent
→ Plan
→ Run
→ Attempt
→ Loop
→ Action
→ Observation
→ Validation
→ Completion
→ Authority
→ Commit
→ World
```

Core invariant:

```text
Intent != Plan != Execution History != Artifact != World Commit
```

CTCL-ITR does **not** require private chain-of-thought. It records observable control flow, causal parents, tools, artifacts, validation, budgets, authority, human checkpoints, recovery, and world-commit receipts.

## Repository layout

```text
CTCL-ITR/
├── docs/
│   └── whitepaper/
│       ├── README.md
│       ├── 01-foundations.md
│       ├── 02-runtime-and-ledger.md
│       ├── 03-interoperability-and-metrics.md
│       └── 04-implementation-and-roadmap.md
├── schemas/
│   ├── intent.schema.json
│   ├── run.schema.json
│   ├── temporal-event.schema.json
│   ├── checkpoint.schema.json
│   ├── commit-receipt.schema.json
│   └── run-summary.schema.json
├── examples/
│   ├── demo_intent.json
│   ├── demo_run.json
│   ├── demo_run.events.jsonl
│   ├── demo_checkpoint.json
│   ├── demo_commit_receipt.json
│   └── demo_run.summary.json
├── sql/
│   └── sqlite_schema.sql
├── src/
│   └── ctcl_itr/
│       ├── __init__.py
│       └── topology.py
├── tests/
│   ├── test_topology.py
│   └── test_pack_validation.py
├── validator/
│   └── validate_pack.py
├── pyproject.toml
├── requirements.txt
├── RELEASE_NOTES_v0.2.md
├── VALIDATION.json
├── VALIDATION_v0.2.json
├── SHA256SUMS.txt
└── README.md
```

The downloadable v0.1 release pack additionally contains the canonical monolithic whitepaper and integrity hashes. The GitHub whitepaper is split into review-friendly projections.

## What v0.1 already specifies

- append-only temporal events
- explicit multi-parent causal edges
- typed human / machine / wall-clock time
- Run / Attempt / Loop identity
- budget deltas
- artifact references and lineage
- validation records
- suspend / resume / retry / recovery semantics
- human governance checkpoints
- authority envelopes
- candidate / commit separation
- world-commit receipts
- run-level quality and completion summaries
- SQLite append-only reference storage
- JSON Schema Draft 2020-12 contracts

## Validate the reference pack

```bash
python -m pip install -r requirements.txt
python validator/validate_pack.py
```

Expected:

```text
ITR/ATL v0.2 topology pack: PASS
legacy_events=18
multi_agent_events=12
machine_work=1850.0
machine_depth=1100.0
poset_width=3
```

## v0.2.0 — Topology Core

v0.2.0 adds executable analysis for ATL causal DAGs:

- branch / join detection
- Interaction Work
- Critical Depth / Span
- deterministic Critical Path
- Structural Parallelism (`Work / Depth`)
- exact finite-poset width via Dilworth's theorem
- `unit` and `machine_runtime_ms` weight contracts

Analyze the reference multi-agent ledger:

```bash
python -m pip install -e .
ctcl-itr-topology examples/multi_agent_branch_join.events.jsonl --weight machine_runtime_ms --pretty
```

Or without installation:

```bash
PYTHONPATH=src python -m ctcl_itr.topology examples/multi_agent_branch_join.events.jsonl --weight machine_runtime_ms --pretty
```

The reference graph contains three incomparable Agent branches followed by an `all` join. Under machine-runtime weighting its expected metrics are:

```text
work = 1850 ms
depth = 1100 ms
poset_width = 3
```

The analyzer treats `causal_parent_ids[]` as canonical hard happens-before edges. Storage order remains separate from causal order.

## Relationship to CTCL

CTCL provides the broader temporal / causal framework.

CTCL-ITR is the execution-time layer that makes interaction time observable and auditable.

```text
CTCL
└── ITR — Interaction-Time Runtime
    └── ATL — Agent Temporal Ledger
```

The underlying theory series distinguishes:

1. Interaction Time
2. Intent Cycle
3. Execution Trajectory
4. Interaction Topology
5. AI Compute Economics
6. Delegated Time
7. Single-Run Quality
8. World Time & Historical Sedimentation

The v0.1 whitepaper maps these layers directly into runtime fields and event semantics. v0.2.0 makes the Interaction Topology layer executable.

## Interoperability direction

CTCL-ITR is designed to coexist with, not replace:

- ISF Execution Runtime
- Temporal Loop Runtime
- W3C Trace Context
- OpenTelemetry / GenAI semantic conventions
- CloudEvents
- JSON Schema

The canonical ATL causal graph keeps `causal_parent_ids[]` because multi-agent joins can have multiple causal parents even when an observability backend uses a single span parent.

## Roadmap

### v0.2.0 — complete in this branch
- multi-agent branch / join reference run
- critical-path and interaction-depth calculator
- exact finite-poset width analyzer

### v0.2.1 — next interoperability slice
- OpenTelemetry exporter
- CloudEvents adapter
- event hash chain
- human approval queue

### v0.3
- distributed workers and fencing
- cross-process resume
- external commit reconciliation
- PHOSPHOR timeline / DAG visualization
- autonomy-horizon and governance-horizon metrics

### v0.4
- multi-runtime federation
- ISF / WDC / CTCL / AICL adapters
- durable world-commit receipts
- historical-sedimentation aggregation

## Project principle

> AI work should be represented as a recoverable, verifiable, governable causal history — not merely as a message, token count, or elapsed duration.

---

EveMissLab / EVEMISS TECHNOLOGY CO., LTD.  
CTCL-ITR v0.2.0 — 2026
