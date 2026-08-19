# Part 3 — Interoperability and Metrics

This GitHub projection condenses sections 56–80 of the canonical v0.1 whitepaper. The complete canonical source is included in the downloadable release pack.

## Structural metrics

For a causal interaction graph $G_I=(V,E)$ with event weights $w(e)$:

$$
W_I=\sum_e w(e)
$$

is total interaction work, while:

$$
D_I=\max_{\pi}\sum_{e\in\pi}w(e)
$$

is interaction depth / critical-path span.

Structural parallelism is:

$$
\Pi_I=\frac{W_I}{D_I}.
$$

Human intervention density is tracked separately:

$$
\rho_H=\frac{N_{human\ checkpoints}}{N_{effective\ transitions}}.
$$

Delegation duration and delegation depth are intentionally distinct.

## Quality and completion

Run summaries can expose quality-adjusted completion:

$$
QAC=Q_{completion}Q_{verification}Q_{result}.
$$

Hard governance gates may veto nominally high soft quality.

## Privacy and observability

The ledger should prefer references, digests, redacted summaries, and typed state over unrestricted raw content.

Core rule:

$$
\text{Observability}\neq\text{Collect Everything}.
$$

Audit answers **what happened**. Authority answers **who was allowed to cause it**.

## Interoperability

CTCL-ITR is designed to coexist with:

- W3C Trace Context
- OpenTelemetry / GenAI semantic conventions
- CloudEvents
- JSON Schema Draft 2020-12

OpenTelemetry spans are observability projections. The canonical ATL graph retains `causal_parent_ids[]` because joins may have multiple causal parents.

A CloudEvents adapter may wrap an ITR `TemporalEvent` as transport data, but transport identity must not replace the canonical `event_id`.

## Runtime contracts

Minimum service interfaces:

```text
emit_event(event)
store_artifact(bytes, metadata)
load_artifact(ref)
create_checkpoint(state)
resolve_authority(ref)
validate(subject)
commit(candidate)
reconcile(commit)
```

Event stores must be append-only, preserve ledger order, reject duplicate IDs and malformed events, and never silently rewrite historical payloads.

Artifacts remain content-addressed references rather than being embedded directly into the temporal event ledger.
