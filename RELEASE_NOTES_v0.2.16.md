# CTCL-ITR v0.2.16 — Payload-Bound Witness Verification

**Date:** 2026-08-28

Same-day follow-up to v0.2.15. An independent, cross-conversation verification run (a fresh subagent with no access to this project's own code, asked to write its own Ed25519 verification from scratch) found a real, honest gap in v0.2.15's witness scheme: CTCL's signature covered `instant_id|unix_ns|timescale` only — not `meta`, where the witnessed digest actually lives. The signature proved "CTCL attests this instant_id existed at this time," but the binding between that instant_id and the witnessed digest rested on trusting CTCL's own server/API integrity, not on the signature itself.

CTCL (commoninstant.org) closed this the same day: registered instants now additionally sign a digest of their own `label`+`meta` (`signed_fields: "instant_id|unix_ns|timescale|sha256(canonical_json(label,meta))"`), a new, separately-labelled scheme that doesn't invalidate anything signed under the old one. This release updates `verify_witness()` to recognize both schemes and report which applies.

## Changed

- `ctcl_itr.external_witness.verify_witness()` now recognizes two signed-fields schemes:
  - `instant_id|unix_ns|timescale` (pre-2026-08-28 instants) — verifies as before, and now reports `meta_bound: false`, since the signature never covered the digest.
  - `instant_id|unix_ns|timescale|sha256(canonical_json(label,meta))` (current) — independently recomputes the payload digest from the fetched record's own `label`/`meta` and verifies against it, reporting `meta_bound: true`.
  - Anything else is still refused as `unsupported_signed_fields`, unchanged.
- New `_canonical_json()` helper, matching CTCL Web's own `canonicalJson()` (`src/worker.js`) byte for byte: object keys sorted recursively, no whitespace. Necessary because `meta` is arbitrary caller-supplied JSON — an independent verifier in a different language can't rely on "whatever key order happened to survive," it needs an explicit, reproducible canonicalization.

## Verified

Live, against production `commoninstant.org` and a local `wrangler dev` instance running the updated CTCL Web signing code: registered an instant with `meta`, confirmed `signed_fields` is the new scheme, independently reconstructed the canonical payload digest and verified the Ed25519 signature (in Python, without importing this project's own signer), then confirmed `ctcl-itr-witness verify-witness` reports `meta_bound: true`. 2 new tests (payload-bound success, tampered-meta rejection under the new scheme) — 208 total.

## Compatibility

- `witness_anchor()` is unchanged — it registers exactly as before; the server itself decides which scheme to sign under.
- No breaking change to the `WitnessRecord` shape.
- Old witness records (signed under the plain scheme) still verify correctly; they now honestly report `meta_bound: false` instead of implying a protection level the signature never provided.
