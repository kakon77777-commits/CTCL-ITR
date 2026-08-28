# CTCL-ITR

**CTCL Interaction-Time Runtime & Agent Temporal Ledger**

A causal, temporal, auditable runtime ledger for long-horizon and multi-agent AI systems.

## Status

**v0.2.15 — External Witness Anchoring / Engineering Contract**

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
│   ├── whitepaper/
│   └── superpowers/{specs,plans}/
├── schemas/
│   ├── temporal-event.schema.json
│   ├── governance-*.schema.json
│   ├── horizon-calibration-suite.schema.json
│   ├── horizon-evidence-profile.schema.json
│   ├── calibration-snapshot.schema.json
│   ├── calibration-comparison-spec.schema.json
│   └── calibration-robustness-report.schema.json
├── examples/
│   ├── multi_agent_branch_join.*
│   ├── governance_*.json
│   ├── horizon_calibration_{suite,profile}.json
│   ├── calibration_snapshot_{base,current}.json
│   ├── calibration_comparison_spec.json
│   └── calibration_robustness_report.json
├── sql/
│   ├── sqlite_schema.sql
│   └── governance_store.sql
├── src/ctcl_itr/
│   ├── topology.py
│   ├── integrity.py
│   ├── governance.py
│   ├── governance_store.py
│   ├── governance_metrics.py
│   ├── governance_signals.py
│   ├── horizon_calibration.py
│   ├── calibration_robustness.py
│   ├── external_witness.py
│   └── interop/
├── tests/
├── validator/
│   ├── validate_pack.py
│   ├── validate_metrics.py
│   ├── validate_signals.py
│   ├── validate_calibration.py
│   └── validate_robustness.py
├── pyproject.toml
├── RELEASE_NOTES_v0.2.8.md
├── VALIDATION_v0.2.8.json
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
python validator/validate_metrics.py
python validator/validate_signals.py
python validator/validate_calibration.py
python validator/validate_robustness.py
python validator/validate_uncertainty.py
python validator/validate_mixture_sensitivity.py
python validator/validate_joint_surface.py
python validator/validate_surface_geometry.py
python validator/validate_geometry_drift.py
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


## v0.2.5 — Governance Observability & Oversight Metrics

v0.2.5 adds a read-only governance diagnostics layer above ATL checkpoint events and durable governance state.

It computes:

```text
Human Intervention Density
Effective Oversight Density
Escalation Latency (mean / p50 / p95 / max)
Intervention Timing
Oversight Debt
Human Governance Time
Risk-Class Oversight Coverage
```

Reference CLI:

```bash
ctcl-itr-governance-metrics --scenario examples/governance_metrics_scenario.json --pretty
```

The metrics layer preserves:

```text
Observation != Authority
Metric != Policy Decision
```

Human Intervention Density is descriptive rather than an optimization target: fewer human interventions are not automatically better governance.

## v0.2.6 — Governance Horizon & Escalation Signals

v0.2.6 turns directional governance metrics into deterministic, non-authoritative escalation signals while keeping horizon measurement explicit.

```text
GovernanceMetricsReport v0.2.5
        +
GovernanceHorizonAssessment
        +
GovernanceEscalationPolicy
        |
        v
GovernanceSignalReport
```

The horizon assessment keeps Autonomy Horizon and Governance Horizon under one measurement contract:

```text
H_A = Autonomy Horizon
H_G = Governance Horizon
Delta_AG = H_A - H_G
M_G = H_G - H_A
```

Reference CLI:

```bash
ctcl-itr-governance-signals   --metrics examples/governance_metrics_report.json   --horizon examples/governance_horizon_assessment.json   --policy examples/governance_escalation_policy.json   --pretty
```

The reference policy signals only directional quantities: Autonomy–Governance Gap, Effective Oversight Density, Oversight Debt, p95 escalation latency, explicit intervention-deadline breaches, and critical-risk oversight coverage. Human Intervention Density remains context, not a pass/fail threshold.

Core boundary:

```text
Signal != Authority
Signal != Automatic Enforcement
```

The aggregate `recommended_escalation` field is advisory only. It does not grant, revoke, suspend, resume, or commit actions.


## v0.2.7 — Horizon Calibration & Evidence Profiles

v0.2.7 derives the v0.2.6 Autonomy / Governance Horizon assessment from repeated evidence instead of requiring manually entered depths.

```text
Repeated trials by interaction depth
        |
        v
empirical binomial reliability
        |
        v
non-increasing PAVA calibration
        |
        v
H_A / H_G at declared reliability p
        |
        v
GovernanceHorizonAssessment v0.2.6
```

Reference CLI:

```bash
ctcl-itr-horizon-calibrate --suite examples/horizon_calibration_suite.json --pretty
```

The reference method `monotone_binomial_pava_v1` reports Wilson evidence intervals at each observed depth, enforces the expected non-increasing reliability relationship, and refuses to extrapolate a Horizon when the target reliability is not bracketed by observed evidence.

Reference evidence reproduces the earlier example from repeated trials:

```text
reliability_p = 0.90
autonomy_trials = 80
governance_trials = 80
H_A = 12
H_G = 9
Delta_AG = 3
```

Core boundary:

```text
Calibration != Authority
Evidence Profile != Policy Decision
Calibrated Horizon != Automatic Enforcement
```


## v0.2.8 — Calibration Robustness, Drift & Task-Family Profiles

v0.2.8 compares evidence-backed v0.2.7 calibration snapshots without flattening task-family composition into one unexplained headline number.

```text
Family repeated trials
  -> v0.2.7 calibrated family curves
  -> CalibrationSnapshot
  -> observed trial-mass mixture
  -> fixed reference mixture
  -> drift / composition diagnostics
```

Reference CLI:

```bash
ctcl-itr-calibration-robustness   --base examples/calibration_snapshot_base.json   --current examples/calibration_snapshot_current.json   --spec examples/calibration_comparison_spec.json   --pretty
```

The canonical scenario shifts evaluation composition from 80% `code` / 20% `research` to 20% `code` / 80% `research`. Both families improve, but the observed-mixture Horizon falls while the fixed 50/50 reference-mixture Horizon rises:

```text
autonomy:  observed delta = -0.6000; adjusted delta = +0.8471
governance: observed delta = -0.4000; adjusted delta = +0.8923
composition TV = 0.6
```

Core boundary:

```text
Observed Horizon Delta != Capability Delta
Composition-Adjusted Delta != Backend-Causal Effect
Calibration Robustness Report != Authority
```

Every family curve is used only inside its observed support; no task-family mixture extrapolation is allowed.



## v0.2.9 — Calibration Uncertainty, Resampling & Drift Bands

v0.2.9 adds deterministic outcome-sampling uncertainty above v0.2.8 without changing its point-estimate semantics. It preserves task-family composition and trial counts, resamples success counts with `stratified_empirical_binomial_sha256_v1`, reruns v0.2.7/v0.2.8, and reports percentile resampling bands, supported-replicate rates, unsupported-reason counts, and empirical sign shares.

```text
Point estimate != uncertainty band
Bootstrap sign share != posterior probability
Conditional sampling uncertainty != composition uncertainty
Uncertainty report != authority
```

Reference CLI:

```bash
ctcl-itr-calibration-uncertainty --base examples/calibration_snapshot_base.json --current examples/calibration_snapshot_current.json --comparison examples/calibration_comparison_spec.json --uncertainty examples/calibration_uncertainty_spec.json --pretty
```

The reference uses 256 deterministic replicates and a 90% percentile resampling band. Composition weights are held fixed; v0.2.8 remains responsible for composition-standardized point estimates.


## v0.2.10 — Reference-Mixture Sensitivity & Uncertainty Decomposition

v0.2.10 varies the fixed task-family reference mixture from v0.2.8 while keeping v0.2.9 outcome-sampling uncertainty fixed as a separate axis. It enumerates a bounded positive simplex grid, reuses the existing no-extrapolation comparison engine at every grid point, and reports supported-grid fraction, drift sensitivity range, sign stability, and unsupported reasons.

```text
Sampling uncertainty != reference-mixture sensitivity
Uncertainty axes != additive total uncertainty
Sensitivity report != authority
```

Reference CLI:

```bash
ctcl-itr-mixture-sensitivity \
  --base examples/calibration_snapshot_base.json \
  --current examples/calibration_snapshot_current.json \
  --comparison examples/calibration_comparison_spec.json \
  --sensitivity examples/calibration_mixture_sensitivity_spec.json \
  --uncertainty-report examples/calibration_uncertainty_report.json --pretty
```

The canonical two-family grid evaluates nine mixtures from 10/90 through 90/10. Six are supported by the existing evidence; three extreme code-heavy mixtures are explicitly unsupported rather than extrapolated. The release reports the v0.2.9 sampling-band width and v0.2.10 mixture-sensitivity span side by side, with `axes_are_additive=false`.

## v0.2.11 — Joint Sampling × Mixture Sensitivity Surface

v0.2.11 evaluates the v0.2.9 outcome-resampling distribution across the v0.2.10 legal reference-mixture grid. One resampled evidence realization is reused across every mixture cell in a replicate, so cells are conditionally related rather than treated as independent experiments.

```bash
ctcl-itr-joint-surface \
  --base examples/calibration_snapshot_base.json \
  --current examples/calibration_snapshot_current.json \
  --comparison examples/calibration_comparison_spec.json \
  --surface examples/calibration_joint_surface_spec.json --pretty
```

The canonical 256-replicate × 9-mixture surface reports per-cell support rate, percentile band, sign shares, unsupported reasons, and band-sign class (`positive_band`, `negative_band`, `crosses_zero`, `zero_band`, `unsupported`).

```text
Surface Cell != Independent Experiment
Joint Surface != Causal Truth
Joint Uncertainty Surface != Authority
```


## v0.2.12 — Surface Geometry & Stability Boundaries

v0.2.12 treats the discrete v0.2.11 joint uncertainty surface as an evidence-supported simplex graph. It does **not** fill unsupported cells. It computes connectivity, sign-region components, support boundaries, local stability crossings, and edge-local gradients only where the source surface supplies adjacent supported evidence.

```text
Joint Surface
  -> simplex single-transfer adjacency
  -> supported graph components
  -> band-sign regions
  -> supported/unsupported boundary edges
  -> lower-band / upper-band zero-crossing estimates
  -> supported-edge local gradients
```

Reference CLI:

```bash
ctcl-itr-surface-geometry \
  --surface examples/calibration_joint_surface_report.json \
  --geometry examples/calibration_surface_geometry_spec.json \
  --pretty
```

Reference geometry per subject:

```text
supported connected components = 1
largest supported component    = 6 cells
crosses-zero component         = 5 cells
positive-band component        = 1 cell
support boundary edges         = 1
sign-class boundary edges      = 1
positive stability crossings   = 1
local gradient edges           = 5
```

The Autonomy lower-band zero crossing is locally interpolated at approximately `code=0.5528922561`; the Governance crossing lands on the observed `code=0.5` endpoint within the declared zero tolerance. No crossing is interpolated through the unsupported code-heavy region.

Core interpretation boundary:

```text
Surface Geometry != Causal Geometry
Interpolated Boundary != Observed Cell
Unsupported Region != Negative Region
Local Gradient != Global Derivative
Geometry Report != Authority
```


## v0.2.13 — Geometry Drift & Boundary Motion

v0.2.13 compares two compatible v0.2.12 geometry snapshots under one declared measurement/grid contract. It separates support-domain change, sign-region migration, component overlap events, stability-boundary displacement, support-frontier motion, and supported-edge gradient drift.

Reference frame:

```text
G0 = Geometry(base -> current)
G1 = Geometry(base -> later)
```

The baseline snapshot is held fixed so reported motion is measured against the same reference evidence.

Reference CLI:

```bash
ctcl-itr-geometry-drift \
  --base-geometry examples/calibration_surface_geometry_report.json \
  --current-geometry examples/calibration_surface_geometry_report_later.json \
  --drift examples/calibration_geometry_drift_spec.json \
  --pretty
```

Reference result:

```text
Autonomy supported cells:       6 -> 8
Governance supported cells:     6 -> 8
support Jaccard:                0.75
component split / merge:        0 / 0
persistent crosses->positive:   2 cells
new positive supported cells:   2 cells
support frontier code weight:   0.6 -> 0.8
Autonomy boundary code move:   -0.1761159465763823
Governance boundary code move: -0.14145271250362584
matched gradient edges:         5
appeared gradient edges:        2
```

The positive-stability boundary moves toward more research-heavy reference mixtures while the evidence-supported domain expands toward more code-heavy mixtures. These are separate geometric observations: the release does not collapse them into a single motion score.

Core interpretation boundary:

```text
Geometry Drift != Causal Mechanism
Boundary Motion != Capability Velocity
Support Expansion != Universal Capability Expansion
Component Split/Merge != Physical Phase Transition
Nearest Boundary Match != Persistent Boundary Identity
Gradient Drift != Global Derivative Drift
Geometry Drift Report != Authority
```

## v0.2.14 — Geometry Motion Stability & Multi-Snapshot Trajectories

v0.2.14 extends the pairwise v0.2.13 drift contract to three or more compatible geometry observations under explicit observation timestamps. Consecutive motion still delegates to v0.2.13; the new layer aggregates support reversals, boundary velocity/acceleration, component lifespan, sign-region persistence, and local-gradient trajectories.

Reference frame:

```text
G0 = Geometry(base -> current)
G1 = Geometry(base -> later)
G2 = Geometry(base -> regressed)
```

The canonical third observation deliberately reuses the current evidence profile at a later timestamp. It is a regression/reversal test fixture, not a forecast.

Reference CLI:

```bash
ctcl-itr-geometry-trajectory \
  --trajectory examples/calibration_geometry_trajectory_spec.json \
  --geometry examples/calibration_surface_geometry_report.json \
  --geometry examples/calibration_surface_geometry_report_later.json \
  --geometry examples/calibration_surface_geometry_report_regressed.json \
  --pretty
```

Reference result per subject:

```text
supported cells              = 6 -> 8 -> 6
support directions           = expansion -> contraction
support direction reversals  = 1
component lineage lifespan   = 3 observations / 2 days
support-excursion cells       = 2
gradient presence excursions = 2
positive-boundary code velocity reversals = 1
```

Positive-boundary code trajectories:

```text
Autonomy:   0.5528922561 -> 0.3767763096 -> 0.5528922561
Governance: 0.5000000000 -> 0.3585472875 -> 0.5000000000
```

Core interpretation boundary:

```text
Geometry Trajectory != Causal Mechanism
Finite-Difference Boundary Velocity != Capability Velocity
Finite-Difference Boundary Acceleration != Physical Acceleration
Support Reversal != Universal System Regression
Boundary Lineage != Persistent Boundary Identity
Component Lineage != Persistent Component Identity
Gradient Trajectory != Global Derivative Field
Trajectory Report != Authority
```

## v0.2.15 — External Witness Anchoring

v0.2.2's Ledger Integrity chain proves a ledger has not changed since its own `LedgerAnchor` was issued — it does not prove the anchor itself is genuine, since the anchor is computed and stored by the same party who controls the ledger. Confirmed empirically: a reference ledger's `occurred_at` backdated by six years, resealed fresh, still verified `valid: true` against its own self-issued anchor.

v0.2.15 closes that gap using CTCL (commoninstant.org) — this project's own sibling — as an external witness. CTCL Ed25519-signs every registered instant and publishes its public key at `GET /v1/pubkey`, so a party verifying a ledger no longer has to trust whoever produced it.

```text
LedgerAnchor (v0.2.2, self-issued)
  -> register final_chain_digest as a CTCL instant (POST /v1/instants)
  -> CTCL Ed25519-signs the moment it was presented
  -> WitnessRecord (instant_id, signature, witnessed timestamp)
  -> independent re-fetch of the instant AND CTCL's public key
  -> Ed25519 signature verification using ONLY CTCL's published key
```

Reference CLI:

```bash
ctcl-itr-integrity seal examples/multi_agent_branch_join.events.jsonl --chain-out /tmp/x.integrity.jsonl --anchor-out /tmp/x.anchor.json
ctcl-itr-witness witness /tmp/x.anchor.json --out /tmp/x.witness.json
ctcl-itr-witness verify-witness /tmp/x.anchor.json --witness /tmp/x.witness.json
```

Verified live against production `commoninstant.org`: a real anchor witnessed and independently re-verified `valid: true`; the same witness record checked against a deliberately forged (backdated) anchor correctly fails `digest_mismatch`, because CTCL only ever witnessed the real anchor's digest.

Core boundary:

```text
Internal Tamper-Evidence != External Trust
Self-Issued Anchor != Third-Party-Witnessed Anchor
Witnessed Digest Match != Live Event Recording (still no SDK for an agent to emit events in real time)
```

Not a general witness-provider interface — only CTCL is supported as a witness source in this release.

## Relationship to CTCL

CTCL provides the broader temporal / causal framework.

CTCL-ITR is the execution-time layer that makes interaction time observable and auditable.

As of v0.2.15 this is a real code dependency, not just a conceptual one: `ctcl-itr-witness` calls CTCL's live `/v1/instants`, `/v1/instant/{id}`, and `/v1/pubkey` endpoints to turn a self-issued ledger anchor into a third-party-witnessed one (see v0.2.15 above).

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

### v0.2.5 — Governance Observability & Oversight Metrics
- Human Intervention Density
- risk-weighted Effective Oversight Density
- escalation latency and intervention timing
- Oversight Debt and risk coverage

### v0.2.6 — Governance Horizon & Escalation Signals
- explicit Autonomy / Governance Horizon assessment contract
- Autonomy–Governance Gap and governance margin
- directional threshold signals
- explicit-deadline breach signal
- non-authoritative aggregate escalation projection

### v0.2.7 — Horizon Calibration & Evidence Profiles
- repeated-trial Horizon calibration suites
- Wilson evidence intervals
- monotone empirical PAVA reliability calibration
- explicit support / no-extrapolation states
- v0.2.6-compatible derived Horizon assessment

### v0.2.8 — Calibration Robustness, Drift & Task-Family Profiles
- task-family calibration snapshots
- observed vs fixed-reference mixture Horizons
- composition-adjusted drift and residual
- composition total-variation diagnostics
- per-family Horizon drift / range / direction agreement
- cross-backend and configuration-change labeling

### v0.2.9 — Calibration Uncertainty, Resampling & Drift Bands
- deterministic empirical-binomial outcome resampling
- percentile resampling bands and supported-replicate rates
- empirical sign stability
- task-family composition held fixed

### v0.2.10 — Reference-Mixture Sensitivity & Uncertainty Decomposition
- bounded simplex scan of reference task-family compositions
- supported mixture range and sign stability
- separate sampling-width / mixture-sensitivity axes
- no scalar additive total uncertainty

### v0.2.11 — Joint Sampling × Mixture Sensitivity Surface
- shared-replicate sampling across reference-mixture cells
- per-cell drift bands / sign shares / support rates
- mixture-sensitive sign-stability regions
- explicit unsupported surface regions


### v0.2.12 — Surface Geometry & Stability Boundaries
- simplex single-transfer adjacency over reference-mixture cells
- supported-region connected components
- sign-stability region components and support/sign boundaries
- supported-edge lower/upper zero-crossing interpolation
- conservative supported-edge local gradients


### v0.2.13 — Geometry Drift & Boundary Motion
- supported-domain expansion / contraction
- component overlap split / merge diagnostics
- persistent-cell sign-region migration
- descriptive stability-boundary displacement
- support-frontier motion without unsupported interpolation
- matched supported-edge gradient drift

### v0.2.14 — Geometry Motion Stability & Multi-Snapshot Trajectories
- ordered compatible geometry observations
- support expansion/contraction trajectories and reversals
- descriptive boundary velocity / finite-difference acceleration
- component overlap lineage lifespan
- sign-region persistence and support excursions
- supported-edge gradient trajectories

### v0.2.15 — External Witness Anchoring
- CTCL (commoninstant.org) as an external, Ed25519-signed witness for a v0.2.2 LedgerAnchor
- independent re-verification using only CTCL's published public key
- closes the self-issued-anchor trust gap named in v0.2.2's own docs, confirmed exploitable via a live backdating demo
- still no live event-recording SDK; only CTCL supported as a witness source

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
CTCL-ITR v0.2.14 — 2026
