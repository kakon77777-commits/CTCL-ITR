# CTCL-ITR v0.2.2 — Ledger Integrity

**Date:** 2026-08-20

v0.2.2 adds a tamper-evident integrity layer for ATL JSONL ledgers while leaving TemporalEvent semantics unchanged.

## Added

- `ctcl_itr.integrity`
  - exact JSONL record-byte SHA-256 digests
  - domain-separated linear hash chaining
  - first-failure integrity diagnostics
  - strict nonblank JSONL reader
  - trusted final ledger anchor
  - JSONL seal / verify APIs
- CLI entry point
  - `ctcl-itr-integrity seal`
  - `ctcl-itr-integrity verify`
- JSON Schema Draft 2020-12 contracts
  - `integrity-record.schema.json`
  - `ledger-anchor.schema.json`
- committed reference integrity sidecar + anchor for the 12-event multi-agent ledger
- pack validator regeneration and attack checks

## Integrity profile

```text
hash_algorithm = sha256
record_encoding = atl-jsonl-record-v1
```

The reference profile hashes exact record bytes excluding the JSONL line terminator. It intentionally does not claim RFC 8785 JCS conformance.

Chain construction:

```text
record_digest = SHA256(record_bytes)
chain_digest = SHA256(
  "CTCL-ITR/ATL/CHAIN/v0.2.2\\0"
  || previous_chain_digest
  || record_digest
)
```

The genesis previous digest is 32 zero bytes.

## Threat model

Detected by the reference verifier:

- event-record byte mutation;
- event reordering;
- interior deletion/insertion relative to the stored sidecar;
- sidecar identity/link/digest tampering;
- suffix truncation when the original trusted anchor is provided.

A linear hash chain alone cannot prove that a suffix was not removed if both the ledger and sidecar are truncated consistently. `LedgerAnchor.event_count` and `LedgerAnchor.final_chain_digest` close that gap only when the expected anchor comes from a trust boundary not silently rewritten with the ledger.

v0.2.2 does **not** claim adversarial immutability if an attacker can rewrite ledger, sidecar, and trusted anchor together. Signed/external anchors and Merkle inclusion/consistency proofs are future work.

## Standards / design references

- SHA-256 from the Secure Hash Standard family.
- RFC 8785 illustrates invariant JSON canonicalization for hashing/signing; this release uses byte-level immutable record hashing instead.
- RFC 9162 Certificate Transparency demonstrates a stronger Merkle-based append-only log with inclusion/consistency proofs; CTCL-ITR v0.2.2 deliberately remains a simpler linear chain.

## Compatibility

- v0.1 TemporalEvent contract remains valid.
- v0.2.0 topology analysis remains unchanged.
- v0.2.1 CloudEvents / OpenTelemetry projections remain unchanged.
- integrity metadata is a sidecar and does not alter canonical event payloads.

## Next

v0.2.3: governance slice — human approval queue and checkpoint decision receipts.
