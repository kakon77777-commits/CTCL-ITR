import base64
import hashlib
import json
from unittest.mock import patch

import pytest

from ctcl_itr.external_witness import SIGNED_FIELDS_WITH_PAYLOAD, WitnessError, verify_witness, witness_anchor


def _anchor(digest: str = "sha256:" + "ab" * 32, run_id: str = "run:demo") -> dict:
    return {
        "schema_version": "0.2.2",
        "run_id": run_id,
        "event_count": 12,
        "first_event_id": "evt_001",
        "last_event_id": "evt_012",
        "hash_algorithm": "sha256",
        "record_encoding": "atl-jsonl-record-v1",
        "final_chain_digest": digest,
    }


def _ed25519_keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    raw_public = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    jwk_x = base64.urlsafe_b64encode(raw_public).rstrip(b"=").decode("ascii")
    return private_key, {"kty": "OKP", "crv": "Ed25519", "x": jwk_x}


def _sign(private_key, instant_id: str, unix_ns: str, timescale: str) -> str:
    signed_string = "|".join([instant_id, unix_ns, timescale])
    signature = private_key.sign(signed_string.encode("utf-8"))
    return base64.b64encode(signature).decode("ascii")


def _canonical_json_for_test(value) -> str:
    # Independent reimplementation (not imported from the module under test) -
    # if this test used the module's own _canonical_json, a bug in that
    # function could never be caught by these tests.
    if value is None or not isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(_canonical_json_for_test(v) for v in value) + "]"
    keys = sorted(value.keys())
    return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + _canonical_json_for_test(value[k]) for k in keys) + "}"


def _sign_with_payload(private_key, instant_id: str, unix_ns: str, timescale: str, label, meta) -> str:
    payload_digest = hashlib.sha256(_canonical_json_for_test({"label": label, "meta": meta}).encode("utf-8")).hexdigest()
    signed_string = "|".join([instant_id, unix_ns, timescale, payload_digest])
    signature = private_key.sign(signed_string.encode("utf-8"))
    return base64.b64encode(signature).decode("ascii")


def test_witness_anchor_registers_the_digest_and_returns_a_witness_record():
    anchor = _anchor()
    ctcl_response = {
        "ok": True,
        "data": {
            "id": "ctcl:instant:abc123",
            "unix_ns": "1700000000000000000",
            "reference_timescale": "utc",
            "retrieve": "/v1/instant/ctcl:instant:abc123",
            "share": "https://commoninstant.org/i/abc123",
            "encodings": {"rfc3339": "2023-11-14T22:13:20Z"},
            "signature": {"alg": "Ed25519", "key_id": "ctcl-ed25519-1", "signed_fields": "instant_id|unix_ns|timescale", "value": "sig=="},
        },
    }
    with patch("ctcl_itr.external_witness._http_json", return_value=ctcl_response) as mocked:
        record = witness_anchor(anchor, endpoint="https://commoninstant.org")

    assert record["instant_id"] == "ctcl:instant:abc123"
    assert record["anchor_final_chain_digest"] == anchor["final_chain_digest"]
    assert record["retrieve"] == "https://commoninstant.org/v1/instant/ctcl:instant:abc123"
    assert record["signature"]["key_id"] == "ctcl-ed25519-1"
    # confirm the actual digest we care about was the one sent, not something else
    sent_body = mocked.call_args.kwargs["body"]
    assert sent_body["meta"]["ctcl_itr_witness"]["final_chain_digest"] == anchor["final_chain_digest"]


def test_witness_anchor_rejects_an_unsealed_anchor():
    with pytest.raises(WitnessError):
        witness_anchor({"run_id": "run:demo"})


def test_witness_anchor_raises_when_ctcl_refuses():
    with patch("ctcl_itr.external_witness._http_json", return_value={"ok": False, "error": {"code": "RATE_LIMITED"}}):
        with pytest.raises(WitnessError):
            witness_anchor(_anchor())


def test_verify_witness_succeeds_with_a_genuine_signature():
    private_key, public_jwk = _ed25519_keypair()
    anchor = _anchor()
    instant_id, unix_ns, timescale = "ctcl:instant:real", "1700000000000000000", "utc"
    signature_b64 = _sign(private_key, instant_id, unix_ns, timescale)

    def fake_http(url, **kwargs):
        if url.endswith("/v1/pubkey"):
            return {"ok": True, "data": {"public_jwk": public_jwk}}
        return {
            "ok": True,
            "data": {
                "id": instant_id,
                "unix_ns": unix_ns,
                "reference_timescale": timescale,
                "meta": {"ctcl_itr_witness": {"final_chain_digest": anchor["final_chain_digest"]}},
                "signature": {"signed_fields": "instant_id|unix_ns|timescale", "value": signature_b64, "key_id": "ctcl-ed25519-1"},
            },
        }

    witness = {"endpoint": "https://commoninstant.org", "instant_id": instant_id}
    with patch("ctcl_itr.external_witness._http_json", side_effect=fake_http):
        report = verify_witness(anchor, witness)

    assert report["valid"] is True
    assert report["failure"] is None
    assert report["key_id"] == "ctcl-ed25519-1"
    # the plain scheme's signature never reached label/meta - be honest about it
    assert report["meta_bound"] is False


def test_verify_witness_succeeds_with_the_payload_bound_scheme_and_reports_meta_bound():
    private_key, public_jwk = _ed25519_keypair()
    anchor = _anchor()
    instant_id, unix_ns, timescale = "ctcl:instant:real", "1700000000000000000", "utc"
    label = "ctcl-itr-anchor:run:demo"
    meta = {"ctcl_itr_witness": {"final_chain_digest": anchor["final_chain_digest"]}}
    signature_b64 = _sign_with_payload(private_key, instant_id, unix_ns, timescale, label, meta)

    def fake_http(url, **kwargs):
        if url.endswith("/v1/pubkey"):
            return {"ok": True, "data": {"public_jwk": public_jwk}}
        return {
            "ok": True,
            "data": {
                "id": instant_id, "unix_ns": unix_ns, "reference_timescale": timescale,
                "label": label, "meta": meta,
                "signature": {"signed_fields": SIGNED_FIELDS_WITH_PAYLOAD, "value": signature_b64, "key_id": "ctcl-ed25519-1"},
            },
        }

    witness = {"endpoint": "https://commoninstant.org", "instant_id": instant_id}
    with patch("ctcl_itr.external_witness._http_json", side_effect=fake_http):
        report = verify_witness(anchor, witness)

    assert report["valid"] is True
    assert report["failure"] is None
    assert report["meta_bound"] is True


def test_verify_witness_rejects_tampered_meta_under_the_payload_bound_scheme():
    # This is the exact gap that motivated SIGNED_FIELDS_WITH_PAYLOAD: under the
    # plain scheme, a signature never covered meta at all, so a party who could
    # get CTCL to sign a genuine instant could then swap the response's meta
    # (e.g. a compromised proxy, or an inconsistent read) without invalidating
    # the signature. Under the payload-bound scheme, that must now fail.
    private_key, public_jwk = _ed25519_keypair()
    anchor = _anchor()
    instant_id, unix_ns, timescale = "ctcl:instant:real", "1700000000000000000", "utc"
    label = "ctcl-itr-anchor:run:demo"
    original_meta = {"ctcl_itr_witness": {"final_chain_digest": anchor["final_chain_digest"]}}
    # signature genuinely covers the ORIGINAL meta ...
    signature_b64 = _sign_with_payload(private_key, instant_id, unix_ns, timescale, label, original_meta)
    # ... but the fetched record's meta has been swapped for a different one.
    swapped_meta = {"ctcl_itr_witness": {"final_chain_digest": "sha256:" + "ee" * 32}}

    def fake_http(url, **kwargs):
        if url.endswith("/v1/pubkey"):
            return {"ok": True, "data": {"public_jwk": public_jwk}}
        return {
            "ok": True,
            "data": {
                "id": instant_id, "unix_ns": unix_ns, "reference_timescale": timescale,
                "label": label, "meta": swapped_meta,
                "signature": {"signed_fields": SIGNED_FIELDS_WITH_PAYLOAD, "value": signature_b64, "key_id": "ctcl-ed25519-1"},
            },
        }

    witness = {"endpoint": "https://commoninstant.org", "instant_id": instant_id}
    with patch("ctcl_itr.external_witness._http_json", side_effect=fake_http):
        report = verify_witness(anchor, witness)

    # digest_mismatch fires first (swapped_meta's digest != anchor's), which is
    # itself already correct - but confirm separately that even if the digests
    # HAD matched, a meta swap invalidates the signature (test the signature
    # path directly, not just the earlier digest-comparison short-circuit).
    assert report["valid"] is False
    assert report["failure"]["code"] == "digest_mismatch"

    matching_forged_anchor = dict(anchor, final_chain_digest=swapped_meta["ctcl_itr_witness"]["final_chain_digest"])
    with patch("ctcl_itr.external_witness._http_json", side_effect=fake_http):
        report2 = verify_witness(matching_forged_anchor, witness)
    assert report2["valid"] is False
    assert report2["failure"]["code"] == "signature_invalid"


def test_verify_witness_rejects_a_tampered_signature():
    private_key, public_jwk = _ed25519_keypair()
    anchor = _anchor()
    instant_id, unix_ns, timescale = "ctcl:instant:real", "1700000000000000000", "utc"
    # sign a DIFFERENT message than what verify_witness will reconstruct -
    # simulates a signature that doesn't actually cover this instant.
    signature_b64 = _sign(private_key, instant_id, "9999999999999999999", timescale)

    def fake_http(url, **kwargs):
        if url.endswith("/v1/pubkey"):
            return {"ok": True, "data": {"public_jwk": public_jwk}}
        return {
            "ok": True,
            "data": {
                "id": instant_id,
                "unix_ns": unix_ns,
                "reference_timescale": timescale,
                "meta": {"ctcl_itr_witness": {"final_chain_digest": anchor["final_chain_digest"]}},
                "signature": {"signed_fields": "instant_id|unix_ns|timescale", "value": signature_b64, "key_id": "ctcl-ed25519-1"},
            },
        }

    witness = {"endpoint": "https://commoninstant.org", "instant_id": instant_id}
    with patch("ctcl_itr.external_witness._http_json", side_effect=fake_http):
        report = verify_witness(anchor, witness)

    assert report["valid"] is False
    assert report["failure"]["code"] == "signature_invalid"


def test_verify_witness_rejects_a_digest_mismatch():
    anchor = _anchor(digest="sha256:" + "ab" * 32)

    def fake_http(url, **kwargs):
        return {
            "ok": True,
            "data": {
                "id": "ctcl:instant:real",
                "unix_ns": "1700000000000000000",
                "reference_timescale": "utc",
                "meta": {"ctcl_itr_witness": {"final_chain_digest": "sha256:" + "cd" * 32}},
                "signature": {"signed_fields": "instant_id|unix_ns|timescale", "value": "sig==", "key_id": "ctcl-ed25519-1"},
            },
        }

    witness = {"endpoint": "https://commoninstant.org", "instant_id": "ctcl:instant:real"}
    with patch("ctcl_itr.external_witness._http_json", side_effect=fake_http):
        report = verify_witness(anchor, witness)

    assert report["valid"] is False
    assert report["failure"]["code"] == "digest_mismatch"


def test_verify_witness_requires_an_instant_id():
    report = verify_witness(_anchor(), {"endpoint": "https://commoninstant.org"})
    assert report["valid"] is False
    assert report["failure"]["code"] == "missing_instant_id"


def test_verify_witness_reports_an_unsigned_instant_honestly():
    def fake_http(url, **kwargs):
        return {
            "ok": True,
            "data": {
                "id": "ctcl:instant:real",
                "unix_ns": "1700000000000000000",
                "reference_timescale": "utc",
                "meta": {"ctcl_itr_witness": {"final_chain_digest": _anchor()["final_chain_digest"]}},
                "signature": None,
            },
        }

    witness = {"endpoint": "https://commoninstant.org", "instant_id": "ctcl:instant:real"}
    with patch("ctcl_itr.external_witness._http_json", side_effect=fake_http):
        report = verify_witness(_anchor(), witness)

    assert report["valid"] is False
    assert report["failure"]["code"] == "unsigned"
