# CTCL-ITR v0.2.1 — Observability Adapters

**Date:** 2026-08-20

v0.2.1 adds two dependency-light interoperability projections while keeping the ATL event ledger canonical.

## Added

- `ctcl_itr.interop.cloudevents`
  - CloudEvents `specversion = 1.0`
  - required `id`, `source`, `type`
  - optional `subject`, `time`, `datacontenttype`, `dataschema`
  - full ATL TemporalEvent under `data`
  - lossless reference round-trip
  - identity mismatch rejection
- `ctcl_itr.interop.opentelemetry`
  - deterministic trace/span identifiers when ATL trace IDs are absent
  - `plan`, `invoke_agent`, `execute_tool` GenAI operation mapping
  - GenAI token-usage attribute mapping
  - ATL runtime and topology attributes under `itr.*`
  - single causal parent -> parent span
  - multi-parent Join -> no privileged parent + span links to every causal parent
- CLI entry points
  - `ctcl-itr-cloudevents`
  - `ctcl-itr-otel`
- reference exports for the 12-event multi-agent branch/join ledger
- pack validator checks for stale exports, CloudEvents round-trip, and Join link preservation

## Architectural boundary

The new adapters are projections, not authorities:

```text
ATL Event Ledger = canonical causal semantics
CloudEvents      = event transport envelope
OpenTelemetry    = observability projection
```

v0.2.1 deliberately does **not** add an OpenTelemetry SDK dependency, OTLP exporter, CloudEvents HTTP binding, or network transport.

## Multi-parent rationale

OpenTelemetry spans have zero or one parent and may contain links to other causally related spans. For scatter/gather aggregation, the OpenTelemetry specification explicitly supports using Links for multiple initiating operations. CTCL-ITR therefore does not arbitrarily select one ATL Join parent as canonical.

## Standards baseline checked for this release

- CloudEvents core specification 1.0 semantics (`id`, `source`, `specversion`, `type` required).
- CloudEvents JSON event format.
- OpenTelemetry Trace API / Links semantics.
- OpenTelemetry GenAI agent and framework span conventions (Development status as of this release), including `invoke_agent`, `plan`, and `execute_tool`.
- Current GenAI usage attributes such as `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`.

## Next

v0.2.2 will focus on ledger integrity: append-only hash chaining and integrity verification, without mixing in the human approval queue.
