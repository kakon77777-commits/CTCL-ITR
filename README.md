# CTCL-ITR

**CTCL Interaction-Time Runtime & Agent Temporal Ledger**

A causal, temporal, auditable runtime ledger for long-horizon and multi-agent AI systems.

## Status

**v0.2.4 — Durable Governance Store / Engineering Contract**

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
│   ├── demo_run.summary.json
│   ├── multi_agent_branch_join.events.jsonl
│   ├── multi_agent_branch_join.cloudevents.jsonl
│   ├── multi_agent_branch_join.otel_spans.json
│   ├── multi_agent_branch_join.integrity.jsonl
│   └── multi_agent_branch_join.anchor.json
├── sql/
│   ├── sqlite_schema.sql
│   └── governance_store.sql
├── src/
│   └── ctcl_itr/
│       ├── __init__.py
│       ├── topology.py
│       ├── integrity.py
│       ├── governance.py
│       ├── governance_store.py
│       └── interop/
│           ├── cloudevents.py
│           └── opentelemetry.py
├── tests/
│   ├── test_topology.py
│   ├── test_cloudevents_adapter.py
│   ├── test_opentelemetry_projection.py
│   ├── test_interop_cli.py
│   ├── test_integrity.py
│   ├── test_governance.py
│   ├── test_durable_governance.py
│   └── test_pack_validation.py
├── validator/
│   └── validate_pack.py
├── pyproject.toml
├── requirements.txt
├── RELEASE_NOTES_v0.2.md
├── RELEASE_NOTES_v0.2.1.md
├── RELEASE_NOTES_v0.2.2.md
├── RELEASE_NOTES_v0.2.3.md
├── RELEASE_NOTES_v0.2.4.md
├── VALIDATION.json
├── VALIDATION_v0.2.json
├── VALIDATION_v0.2.1.json
├── VALIDATION_v0.2.2.json
├── VALIDATION_v0.2.3.json
├── VALIDATION_v0.2.4.json
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
ITR/ATL v0.2.4 durable governance store: PASS
ITR/ATL v0.2.3 governance core pack: PASS
ITR/ATL v0.2.2 ledger integrity pack: PASS
ITR/ATL v0.2.1 observability pack: PASS
legacy_events=18
multi_agent_events=12
cloudevents_roundtrip=12
otel_spans=12
join_links=3
integrity_records=12
governance_events=5
governance_resume_eligible=True
governance_scope_block=scope_mismatch
durable_restart_recovered=True
durable_atomic_resolve=True
durable_authority_uses=2
anchor_checked=True
tamper_detection=record_digest_mismatch
truncation_detection=anchor_event_count_mismatch
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


## v0.2.1 — Observability Adapters

v0.2.1 makes canonical ATL events projectable into existing observability and event infrastructure without changing ATL causality.

### CloudEvents 1.0

Each ATL event can be wrapped losslessly as a CloudEvents 1.0 JSON envelope:

```bash
PYTHONPATH=src python -m ctcl_itr.interop.cloudevents examples/multi_agent_branch_join.events.jsonl
```

The complete ATL event remains under `data`, so the reference adapter supports exact ATL round-trip. `id`, `source`, `specversion`, and `type` are emitted as CloudEvents context attributes; the envelope also carries `subject`, `time`, `datacontenttype`, and the canonical ATL `dataschema`.

### OpenTelemetry-style span projection

```bash
PYTHONPATH=src python -m ctcl_itr.interop.opentelemetry examples/multi_agent_branch_join.events.jsonl --pretty
```

The projection uses current GenAI operation names where applicable:

- `plan`
- `invoke_agent`
- `execute_tool`

It maps ATL token budgets to `gen_ai.usage.*` attributes when available. This is a deterministic intermediate projection, **not** an OTLP wire payload and not an OpenTelemetry SDK dependency.

### Multi-parent Join preservation

ATL `causal_parent_ids[]` remains canonical. A single causal parent becomes the projected `parent_span_id`; a Join with multiple causal parents has no privileged parent and emits all causal parents as span `links[]`.

This preserves the distinction:

```text
ATL causal DAG != observability span tree
```

Reference exports are committed under `examples/` and regenerated by the pack validator.

## v0.2.2 — Ledger Integrity

v0.2.2 adds a tamper-evident sidecar chain without changing the canonical TemporalEvent schema.

```text
ATL JSONL record bytes
  -> SHA-256 record digest
  -> previous-chain binding
  -> IntegrityRecord JSONL
  -> LedgerAnchor
```

Seal a ledger:

```bash
ctcl-itr-integrity seal examples/multi_agent_branch_join.events.jsonl \
  --chain-out /tmp/multi.integrity.jsonl \
  --anchor-out /tmp/multi.anchor.json
```

Verify it:

```bash
ctcl-itr-integrity verify examples/multi_agent_branch_join.events.jsonl \
  --chain /tmp/multi.integrity.jsonl \
  --anchor /tmp/multi.anchor.json
```

The reference profile hashes the exact nonblank JSONL record bytes, excluding the line terminator, under the profile name `atl-jsonl-record-v1`. It does **not** claim RFC 8785 JSON canonicalization.

The chain detects record mutation, reordering, interior deletion, and sidecar link tampering. A trusted `LedgerAnchor` binds the final chain head and event count, which is what makes suffix truncation detectable. An anchor stored under the same rewrite authority as the ledger is not a cryptographic trust root; external signing/publication is a future layer.

## v0.2.3 — Governance Core

v0.2.3 makes human checkpoints explicit runtime objects rather than treating an approval click as the governance model.

```text
ApprovalRequest
  -> DecisionReceipt
  -> AuthorityGrant
  -> Resume Eligibility
  -> authority.checked
  -> run.resumed
```

The three objects remain distinct:

```text
Human decision != authority grant != runtime resume
```

`ApprovalRequest` carries the trigger, decision-ready context, evidence references, requested authority, risk class, and expiry. `DecisionReceipt` records the principal, decision, selected option, reason, and human active/governance time. `AuthorityGrant` narrows the resulting scope, target, expiry, revocability, and maximum use count.

Reference CLI:

```bash
ctcl-itr-governance-demo demo --pretty
```

The reference `ApprovalQueue` is deterministic and in-memory; it defines semantics for pending, approved, denied, modified, deferred, cancelled, and expired requests, plus authority consumption and revocation. It is not a distributed workflow queue.

A suspended run is resume-eligible only when the decision authorizes the action and an active bounded grant matches the action and target, remains unexpired/unrevoked, and still has remaining uses.

## v0.2.4 — Durable Governance Store

v0.2.4 adds `SQLiteApprovalQueue`, a restart-safe reference implementation of the v0.2.3 governance queue semantics. Canonical `ApprovalRequest`, `DecisionReceipt`, and `AuthorityGrant` JSON objects remain unchanged.

```text
ApprovalRequest / DecisionReceipt / AuthorityGrant
        |
        v
SQLite durable state + state_version
        |
        +--> restart recovery
        +--> atomic resolve / consume / revoke
        +--> append-only governance mutation journal
```

The reference profile enables SQLite foreign keys, WAL journaling, and `synchronous=FULL`. Multi-object `resolve()` and authority read-modify-write operations use `BEGIN IMMEDIATE`.

```bash
ctcl-itr-governance-store demo --db /tmp/ctcl-governance.sqlite3 --pretty
ctcl-itr-governance-store status --db /tmp/ctcl-governance.sqlite3 --pretty
```

The store is an operational durability layer, not the canonical ATL event history. Its `governance_mutations` table is append-only reference evidence and does not replace the v0.2.2 integrity chain. Distributed leases/fencing and multi-node consensus remain future work.

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

### v0.2.0 — Topology Core
- multi-agent branch / join reference run
- critical-path and interaction-depth calculator
- exact finite-poset width analyzer

### v0.2.1 — Observability Adapters
- lossless CloudEvents 1.0 JSON envelope
- deterministic OpenTelemetry-style span projection
- GenAI operation / usage attribute mapping
- multi-parent Join -> span Links

### v0.2.2 — Ledger Integrity
- sidecar SHA-256 event-record hash chain
- trusted ledger anchor
- mutation / reorder / deletion / anchored truncation detection
- integrity CLI and JSON Schemas

### v0.2.3 — Governance Core
- human approval queue semantics
- checkpoint decision receipts
- bounded authority grants
- resume eligibility / revocation / expiry

### v0.2.4 — Durable Governance Store
- SQLite-backed restart-safe approval queue
- transactional decision/grant persistence
- durable authority use/revocation/expiration
- append-only governance mutation journal

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
CTCL-ITR v0.2.4 — 2026
