# CTCL-ITR

**CTCL Interaction-Time Runtime & Agent Temporal Ledger**

A causal, temporal, auditable runtime ledger for long-horizon and multi-agent AI systems.

## Status

**v0.1 — Engineering Contract / Reference Pack**

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
│       └── Interaction-Time_Runtime_and_Agent_Temporal_Ledger_v0.1.md
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
├── validator/
│   └── validate_pack.py
├── requirements.txt
├── VALIDATION.json
└── README.md
```

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
ITR/ATL v0.1 example pack: PASS
events=18
```

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

The v0.1 whitepaper maps these layers directly into runtime fields and event semantics.

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

### v0.2
- multi-agent branch / join reference run
- critical-path and interaction-depth calculator
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
CTCL-ITR v0.1 — 2026
