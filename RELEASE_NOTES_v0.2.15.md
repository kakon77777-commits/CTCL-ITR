# CTCL-ITR v0.2.15 — External Witness Anchoring

**Date:** 2026-08-28

v0.2.2's Ledger Integrity chain proves a ledger has not been altered since its own `LedgerAnchor` was issued. It does not prove the anchor itself is genuine, because the anchor is computed and stored by the same party who controls the ledger — the project's own README says so directly: "An anchor stored under the same rewrite authority as the ledger is not a cryptographic trust root; external signing/publication is a future layer."

Confirmed empirically before this release: a reference ledger's `occurred_at` was backdated by six years, re-sealed fresh, and `ctcl-itr-integrity verify` reported `valid: true` against its own freshly self-issued anchor. `seal`/`verify` alone cannot distinguish a genuine history from a forged one.

v0.2.15 closes that gap using CTCL (Common Temporal Coordinate Layer, commoninstant.org) — ITR's own sibling project — as an external witness. CTCL Ed25519-signs every registered instant and publishes its public key at `GET /v1/pubkey`; this release registers a ledger anchor's digest as a CTCL instant and independently re-verifies the resulting signature, so a party verifying a ledger no longer has to trust whoever produced it.

## Added

- `ctcl_itr.external_witness`
  - `witness_anchor()` — registers a `LedgerAnchor`'s `final_chain_digest` as a CTCL instant (`POST /v1/instants`), returns a `WitnessRecord` (instant id, retrieve/share URLs, the Ed25519 signature, the witnessed timestamp).
  - `verify_witness()` — independently re-fetches the witnessed instant AND CTCL's current public key from CTCL itself (never trusting a locally-cached copy), confirms the digest CTCL actually witnessed matches the anchor, and verifies the Ed25519 signature using only CTCL's published key.
- CLI: `ctcl-itr-witness witness <anchor> --out <path> [--endpoint URL] [--label TEXT]`, `ctcl-itr-witness verify-witness <anchor> --witness <path> [--endpoint URL]`.
- New dependency: `cryptography>=42,<47` (Ed25519 signature verification — the standard library has no Ed25519 support).

## Verified

Unit suite (mocked HTTP, real Ed25519 sign/verify round-trips — no network access required): 8 new tests covering a genuine signature, a tampered signature, a digest mismatch, a missing instant id, an unsigned instant, and both `witness_anchor` failure paths.

Live, against production `commoninstant.org` (not mocked):

```text
$ ctcl-itr-integrity seal examples/multi_agent_branch_join.events.jsonl --chain-out ... --anchor-out ...
final_chain_digest = sha256:d842860c...

$ ctcl-itr-witness witness <anchor> --out <witness> --label ctcl-itr-live-demo-2026-08-28
instant_id = ctcl:instant:1db619af-3910-4508-9f83-bdbbfce83fc2
witnessed_rfc3339 = 2026-08-28T10:33:12.96Z
signature.key_id = ctcl-ed25519-1

$ ctcl-itr-witness verify-witness <anchor> --witness <witness>
{"valid": true, "failure": null, "key_id": "ctcl-ed25519-1", ...}

# acid test: verifying the SAME witness record against the earlier forged
# (backdated) anchor correctly fails, because CTCL only ever witnessed the
# real anchor's digest:
$ ctcl-itr-witness verify-witness <forged-anchor> --witness <witness>
{"valid": false, "failure": {"code": "digest_mismatch", ...}}
```

**Gotcha caught by testing, not review**: Python's default `urllib` User-Agent (`Python-urllib/3.x`) trips CTCL Web's Cloudflare bot filter (HTTP 403, Cloudflare error 1010) even though `/v1/instants` is CTCL's own public, documented, unauthenticated API — `curl` against the identical endpoint succeeds. Fixed by identifying honestly as `ctcl-itr/0.1 (+https://github.com/kakon77777-commits/ctcl-itr)` rather than leaving the client unidentified.

Complete repository test inventory: **206** (198 + 8).

## Not done

- `verify_witness` requires live network access to CTCL — there is no offline/cached verification path, and no `validator/validate_witness.py` was added, since every other validator in this repo is a deterministic offline check over static reference data and this feature's entire point is a live third-party round trip.
- Only CTCL (commoninstant.org) is supported as a witness source; a pluggable witness-provider interface is not built.
- No live "record an event as an agent actually runs" SDK exists yet anywhere in this project (v0.1 through this release) — every CLI tool here analyzes or validates already-written JSONL files. Witnessing an anchor after the fact is a real trust improvement, but it doesn't yet address a distributed AI organization's other half of this problem: how an agent actually emits ledger events during live operation.

## Compatibility

- No change to `TemporalEvent`, `LedgerAnchor`, or `IntegrityRecord` schemas — `witness_anchor`/`verify_witness` operate on an anchor produced by the existing, unmodified v0.2.2 `seal`/`verify` flow.
- Governance, calibration, and geometry layers unchanged.
