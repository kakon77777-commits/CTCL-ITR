"""External witness anchoring for CTCL-ITR ledger anchors.

integrity.py's LedgerAnchor proves internal self-consistency: nobody has
altered this ledger since ITS OWN anchor was issued. It does not prove the
anchor itself is genuine, because the anchor is computed and stored by the
same party who controls the ledger - the project's own README says so
directly: "An anchor stored under the same rewrite authority as the ledger
is not a cryptographic trust root; external signing/publication is a future
layer." A party can backdate every timestamp in a ledger, seal it fresh, and
self-issue a passing anchor for the forged history - `seal`/`verify` alone
cannot tell the difference (confirmed empirically: see the 2026-08-28
integration notes).

This module closes that gap using CTCL (Common Temporal Coordinate Layer,
commoninstant.org) - ITR's own sibling project - as the external witness.
CTCL Ed25519-signs every registered instant and publishes its public key at
GET /v1/pubkey, so ANY independent party can verify a witness record's
signature using only that published key - never anything the ledger's own
owner controls. This is exactly the missing half for the use cases CTCL-ITR
is actually meant to serve: a distributed AI organization's shared
spacetime-stamp verification, and a step toward an AI-login gateway's
spacetime-stamp verification method - both require that a verifier NOT have
to trust the party being verified.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

WITNESS_SCHEMA_VERSION = "0.1"
DEFAULT_ENDPOINT = "https://commoninstant.org"
# CTCL's own documented signed-fields order (GET /v1/pubkey's own
# `signed_fields` string) - reconstructing this ourselves rather than
# trusting whatever a witness record claims keeps a forged claim of
# "signed_fields" from smuggling a different (unsigned) string past
# verification.
EXPECTED_SIGNED_FIELDS = "instant_id|unix_ns|timescale"


class WitnessError(ValueError):
    """Raised when an anchor cannot be witnessed, or a witness record cannot be verified."""


USER_AGENT = "ctcl-itr/" + WITNESS_SCHEMA_VERSION + " (+https://github.com/kakon77777-commits/ctcl-itr)"


def _http_json(url: str, *, body: dict[str, Any] | None = None, timeout: float = 15.0) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    # Python's default urllib User-Agent ("Python-urllib/x.y") trips CTCL Web's
    # Cloudflare bot filter (HTTP 403, Cloudflare error 1010) even though this
    # is CTCL's own public, documented, unauthenticated API - curl against the
    # identical endpoint succeeds. Identifying honestly as this tool (not
    # impersonating a browser) clears it.
    headers = {"User-Agent": USER_AGENT}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise WitnessError(f"{req.method} {url} failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise WitnessError(f"{req.method} {url} unreachable: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise WitnessError(f"{req.method} {url} did not return valid JSON") from exc


def witness_anchor(anchor: dict[str, Any], endpoint: str = DEFAULT_ENDPOINT, label: str | None = None) -> dict[str, Any]:
    """Register `anchor` as a CTCL instant, so CTCL - not whoever produced this
    ledger - Ed25519-signs the moment this exact anchor digest was presented.
    Returns a WitnessRecord meant to be stored alongside the local anchor
    (e.g. `<anchor>.witness.json`).
    """
    digest = anchor.get("final_chain_digest")
    if not digest:
        raise WitnessError("anchor is missing final_chain_digest - seal the ledger first (ctcl-itr-integrity seal)")

    endpoint = endpoint.rstrip("/")
    body = {
        "label": label or f"ctcl-itr-anchor:{anchor.get('run_id', 'unknown')}",
        "meta": {
            "ctcl_itr_witness": {
                "schema_version": WITNESS_SCHEMA_VERSION,
                "anchor_schema_version": anchor.get("schema_version"),
                "run_id": anchor.get("run_id"),
                "event_count": anchor.get("event_count"),
                "first_event_id": anchor.get("first_event_id"),
                "last_event_id": anchor.get("last_event_id"),
                "final_chain_digest": digest,
            }
        },
    }
    resp = _http_json(f"{endpoint}/v1/instants", body=body)
    if not resp.get("ok"):
        raise WitnessError(f"CTCL refused the witness registration: {resp.get('error')}")
    instant = resp["data"]
    retrieve = instant.get("retrieve", "")

    return {
        "schema_version": WITNESS_SCHEMA_VERSION,
        "endpoint": endpoint,
        "instant_id": instant["id"],
        "retrieve": f"{endpoint}{retrieve}" if retrieve.startswith("/") else retrieve,
        "share": instant.get("share"),
        "witnessed_unix_ns": instant["unix_ns"],
        "witnessed_rfc3339": (instant.get("encodings") or {}).get("rfc3339"),
        "signature": instant.get("signature"),
        "anchor_final_chain_digest": digest,
    }


def _decode_ed25519_public_key(jwk: dict[str, Any]):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519":
        raise WitnessError(f"unsupported public key type: {jwk.get('kty')}/{jwk.get('crv')}")
    x = jwk["x"]
    padded = x + "=" * (-len(x) % 4)
    raw = base64.urlsafe_b64decode(padded)
    return Ed25519PublicKey.from_public_bytes(raw)


def verify_witness(anchor: dict[str, Any], witness: dict[str, Any], endpoint: str | None = None) -> dict[str, Any]:
    """Independently re-fetch the witnessed instant AND CTCL's current public
    key from CTCL itself (never trusting the locally-cached witness record's
    own copies), then confirm: (1) the digest CTCL actually witnessed matches
    this anchor, (2) CTCL's Ed25519 signature over that instant is genuine.

    This is deliberately the check an INDEPENDENT third party would run - it
    needs nothing from whoever produced the ledger except the public anchor
    and witness record, plus network access to CTCL itself.
    """
    endpoint = (endpoint or witness.get("endpoint") or DEFAULT_ENDPOINT).rstrip("/")
    instant_id = witness.get("instant_id")
    if not instant_id:
        return {"valid": False, "failure": {"code": "missing_instant_id", "message": "witness record has no instant_id"}}

    try:
        fetched = _http_json(f"{endpoint}/v1/instant/{instant_id}")
    except WitnessError as exc:
        return {"valid": False, "failure": {"code": "fetch_failed", "message": str(exc)}}
    if not fetched.get("ok"):
        return {"valid": False, "failure": {"code": "instant_not_found", "message": str(fetched.get("error"))}}
    record = fetched["data"]

    witnessed_digest = ((record.get("meta") or {}).get("ctcl_itr_witness") or {}).get("final_chain_digest")
    if witnessed_digest != anchor.get("final_chain_digest"):
        return {
            "valid": False,
            "failure": {
                "code": "digest_mismatch",
                "message": f"CTCL witnessed final_chain_digest={witnessed_digest!r}, this anchor has {anchor.get('final_chain_digest')!r}",
            },
        }

    sig = record.get("signature")
    if not sig:
        return {"valid": False, "failure": {"code": "unsigned", "message": "the witnessed instant exists but carries no signature - this CTCL deployment has no signing key configured"}}
    if sig.get("signed_fields") != EXPECTED_SIGNED_FIELDS:
        return {"valid": False, "failure": {"code": "unsupported_signed_fields", "message": f"don't know how to reconstruct signed_fields={sig.get('signed_fields')!r}"}}

    try:
        pubkey_resp = _http_json(f"{endpoint}/v1/pubkey")
    except WitnessError as exc:
        return {"valid": False, "failure": {"code": "pubkey_fetch_failed", "message": str(exc)}}
    if not pubkey_resp.get("ok"):
        return {"valid": False, "failure": {"code": "pubkey_unavailable", "message": str(pubkey_resp.get("error"))}}
    pubkey_data = pubkey_resp["data"]

    signed_string = "|".join([record["id"], record["unix_ns"], record["reference_timescale"]])
    try:
        pubkey = _decode_ed25519_public_key(pubkey_data["public_jwk"])
        pubkey.verify(base64.b64decode(sig["value"]), signed_string.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any failure here means "not verified", report it as such
        return {"valid": False, "failure": {"code": "signature_invalid", "message": f"{type(exc).__name__}: {exc}"}}

    return {
        "valid": True,
        "instant_id": instant_id,
        "endpoint": endpoint,
        "witnessed_rfc3339": witness.get("witnessed_rfc3339"),
        "key_id": sig.get("key_id"),
        "failure": None,
    }


def _main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Witness a CTCL-ITR ledger anchor with CTCL (commoninstant.org), or independently verify an existing witness record.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    witness_parser = subparsers.add_parser("witness", help="Register a ledger anchor as a signed CTCL instant")
    witness_parser.add_argument("anchor", help="Ledger anchor JSON path (from ctcl-itr-integrity seal)")
    witness_parser.add_argument("--out", required=True, help="Output witness record JSON path")
    witness_parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help=f"CTCL deployment base URL (default: {DEFAULT_ENDPOINT})")
    witness_parser.add_argument("--label", help="Optional label for the registered instant")

    verify_parser = subparsers.add_parser("verify-witness", help="Independently verify a witness record against live CTCL data")
    verify_parser.add_argument("anchor", help="Ledger anchor JSON path")
    verify_parser.add_argument("--witness", required=True, help="Witness record JSON path (from the witness subcommand)")
    verify_parser.add_argument("--endpoint", help="Override the witness record's own endpoint")

    args = parser.parse_args(argv)
    try:
        if args.command == "witness":
            anchor = json.loads(Path(args.anchor).read_text(encoding="utf-8"))
            record = witness_anchor(anchor, endpoint=args.endpoint, label=args.label)
            Path(args.out).write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            print(json.dumps({"witnessed": True, **record}, ensure_ascii=False, sort_keys=True))
            return 0

        anchor = json.loads(Path(args.anchor).read_text(encoding="utf-8"))
        witness = json.loads(Path(args.witness).read_text(encoding="utf-8"))
        report = verify_witness(anchor, witness, endpoint=args.endpoint)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["valid"] else 1
    except (WitnessError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
