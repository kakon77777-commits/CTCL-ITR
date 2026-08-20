import json
from copy import deepcopy
from pathlib import Path

import pytest

from ctcl_itr.integrity import record_digest, seal_records, verify_records


def _record(event_id: str, seq: int, value: str) -> bytes:
    event = {
        "schema_version": "0.1",
        "event_id": event_id,
        "ledger_seq": seq,
        "event_type": "action.completed",
        "source": "/itr/test",
        "subject": f"run/test/{event_id}",
        "occurred_at": f"2026-08-20T00:00:{seq:02d}+08:00",
        "recorded_at": f"2026-08-20T00:00:{seq:02d}+08:00",
        "run_id": "run:test",
        "causal_parent_ids": [] if seq == 1 else [f"evt_{seq-1:03d}"],
        "actor": {"actor_id": "agent:test", "actor_type": "agent"},
        "data": {"value": value},
    }
    return json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def test_record_digest_is_stable_for_identical_record_bytes():
    record = _record("evt_001", 1, "alpha")
    assert record_digest(record) == record_digest(record)
    assert record_digest(record).startswith("sha256:")
    assert len(record_digest(record)) == len("sha256:") + 64


def test_seal_and_verify_valid_records():
    records = [
        _record("evt_001", 1, "alpha"),
        _record("evt_002", 2, "beta"),
        _record("evt_003", 3, "gamma"),
    ]
    integrity, anchor = seal_records(records)

    assert len(integrity) == 3
    assert integrity[0]["previous_chain_digest"] is None
    assert integrity[1]["previous_chain_digest"] == integrity[0]["chain_digest"]
    assert anchor["event_count"] == 3
    assert anchor["final_chain_digest"] == integrity[-1]["chain_digest"]

    report = verify_records(records, integrity, anchor)
    assert report["valid"] is True
    assert report["checked_records"] == 3
    assert report["anchor_checked"] is True
    assert report["failure"] is None


def _sealed_three():
    records = [
        _record("evt_001", 1, "alpha"),
        _record("evt_002", 2, "beta"),
        _record("evt_003", 3, "gamma"),
    ]
    integrity, anchor = seal_records(records)
    return records, integrity, anchor


def test_verify_reports_record_digest_mismatch_at_first_tampered_record():
    records, integrity, anchor = _sealed_three()
    tampered = records.copy()
    tampered[1] = tampered[1].replace(b'"beta"', b'"BETA"')

    report = verify_records(tampered, integrity, anchor)

    assert report["valid"] is False
    assert report["failure"]["code"] == "record_digest_mismatch"
    assert report["failure"]["ledger_seq"] == 2
    assert report["failure"]["event_id"] == "evt_002"
    assert report["checked_records"] == 1


def test_verify_rejects_reordered_event_records():
    records, integrity, anchor = _sealed_three()
    reordered = [records[1], records[0], records[2]]

    report = verify_records(reordered, integrity, anchor)

    assert report["valid"] is False
    assert report["failure"]["code"] == "ledger_seq_mismatch"
    assert report["failure"]["ledger_seq"] == 2
    assert report["checked_records"] == 0


def test_verify_rejects_interior_deletion_even_if_matching_sidecar_line_is_deleted():
    records, integrity, anchor = _sealed_three()
    shortened_records = [records[0], records[2]]
    shortened_integrity = [integrity[0], integrity[2]]

    report = verify_records(shortened_records, shortened_integrity, None)

    assert report["valid"] is False
    assert report["failure"]["code"] == "ledger_seq_mismatch"
    assert report["checked_records"] == 1


def test_suffix_truncation_needs_original_anchor_to_be_detected():
    records, integrity, anchor = _sealed_three()
    truncated_records = records[:2]
    truncated_integrity = integrity[:2]

    internal_report = verify_records(truncated_records, truncated_integrity, None)
    anchored_report = verify_records(truncated_records, truncated_integrity, anchor)

    assert internal_report["valid"] is True
    assert internal_report["anchor_checked"] is False
    assert anchored_report["valid"] is False
    assert anchored_report["failure"]["code"] == "anchor_event_count_mismatch"


def test_verify_rejects_sidecar_chain_link_tampering():
    records, integrity, anchor = _sealed_three()
    tampered_integrity = deepcopy(integrity)
    tampered_integrity[1]["previous_chain_digest"] = "sha256:" + "0" * 64

    report = verify_records(records, tampered_integrity, anchor)

    assert report["valid"] is False
    assert report["failure"]["code"] == "previous_chain_digest_mismatch"
    assert report["failure"]["ledger_seq"] == 2


def _write_records(path: Path, records: list[bytes]) -> None:
    path.write_bytes(b"\n".join(records) + b"\n")


def test_jsonl_seal_verify_and_schemas(tmp_path):
    import jsonschema
    from ctcl_itr.integrity import seal_jsonl, verify_jsonl

    records = [_record("evt_001", 1, "alpha"), _record("evt_002", 2, "beta")]
    events_path = tmp_path / "events.jsonl"
    chain_path = tmp_path / "events.integrity.jsonl"
    anchor_path = tmp_path / "events.anchor.json"
    _write_records(events_path, records)

    seal_jsonl(events_path, chain_path, anchor_path)
    report = verify_jsonl(events_path, chain_path, anchor_path)

    assert report["valid"] is True
    chain = [json.loads(line) for line in chain_path.read_text(encoding="utf-8").splitlines()]
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parents[1]
    integrity_schema = json.loads((root / "schemas" / "integrity-record.schema.json").read_text(encoding="utf-8"))
    anchor_schema = json.loads((root / "schemas" / "ledger-anchor.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(integrity_schema)
    for item in chain:
        validator.validate(item)
    jsonschema.Draft202012Validator(anchor_schema).validate(anchor)


def test_jsonl_reader_rejects_blank_records(tmp_path):
    from ctcl_itr.integrity import IntegrityError, seal_jsonl

    events_path = tmp_path / "events.jsonl"
    events_path.write_bytes(_record("evt_001", 1, "alpha") + b"\n\n")

    with pytest.raises(IntegrityError, match="blank"):
        seal_jsonl(events_path, tmp_path / "chain.jsonl", tmp_path / "anchor.json")


def test_integrity_cli_seal_and_verify_exit_codes(tmp_path):
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    records = [_record("evt_001", 1, "alpha"), _record("evt_002", 2, "beta")]
    events_path = tmp_path / "events.jsonl"
    chain_path = tmp_path / "events.integrity.jsonl"
    anchor_path = tmp_path / "events.anchor.json"
    _write_records(events_path, records)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")

    sealed = subprocess.run(
        [sys.executable, "-m", "ctcl_itr.integrity", "seal", str(events_path), "--chain-out", str(chain_path), "--anchor-out", str(anchor_path)],
        cwd=root, env=env, capture_output=True, text=True,
    )
    assert sealed.returncode == 0, sealed.stderr
    assert "RuntimeWarning" not in sealed.stderr

    verified = subprocess.run(
        [sys.executable, "-m", "ctcl_itr.integrity", "verify", str(events_path), "--chain", str(chain_path), "--anchor", str(anchor_path)],
        cwd=root, env=env, capture_output=True, text=True,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["valid"] is True

    tampered = events_path.read_bytes().replace(b'"beta"', b'"BETA"')
    events_path.write_bytes(tampered)
    failed = subprocess.run(
        [sys.executable, "-m", "ctcl_itr.integrity", "verify", str(events_path), "--chain", str(chain_path), "--anchor", str(anchor_path)],
        cwd=root, env=env, capture_output=True, text=True,
    )
    assert failed.returncode == 1
    payload = json.loads(failed.stdout)
    assert payload["valid"] is False
    assert payload["failure"]["code"] == "record_digest_mismatch"
