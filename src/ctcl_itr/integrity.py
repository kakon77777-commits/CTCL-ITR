"""Tamper-evident sidecar integrity records for ATL JSONL ledgers."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

HASH_ALGORITHM = "sha256"
RECORD_ENCODING = "atl-jsonl-record-v1"
INTEGRITY_SCHEMA_VERSION = "0.2.2"
CHAIN_DOMAIN = b"CTCL-ITR/ATL/CHAIN/v0.2.2\0"
GENESIS_DIGEST_BYTES = b"\x00" * 32


class IntegrityError(ValueError):
    """Raised when ledger records cannot be sealed or verified."""


def _digest_text(raw: bytes) -> str:
    return f"sha256:{raw.hex()}"


def _digest_bytes(value: str) -> bytes:
    prefix = "sha256:"
    if not isinstance(value, str) or not value.startswith(prefix):
        raise IntegrityError("digest must use sha256:<hex> form")
    hex_part = value[len(prefix):]
    if len(hex_part) != 64:
        raise IntegrityError("SHA-256 digest must contain 64 hex characters")
    try:
        return bytes.fromhex(hex_part)
    except ValueError as exc:
        raise IntegrityError("invalid SHA-256 hex digest") from exc


def record_digest(record_bytes: bytes) -> str:
    """Hash exact ATL JSONL record bytes, excluding any line terminator."""
    if not isinstance(record_bytes, (bytes, bytearray)):
        raise TypeError("record_bytes must be bytes")
    return _digest_text(sha256(bytes(record_bytes)).digest())


def _parse_record(record_bytes: bytes) -> dict[str, Any]:
    try:
        event = json.loads(record_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("record is not valid UTF-8 JSON") from exc
    if not isinstance(event, dict):
        raise IntegrityError("record must contain a JSON object")
    for field in ("run_id", "ledger_seq", "event_id"):
        if field not in event:
            raise IntegrityError(f"record missing required field: {field}")
    if not isinstance(event["run_id"], str) or not event["run_id"]:
        raise IntegrityError("run_id must be a non-empty string")
    if not isinstance(event["event_id"], str) or not event["event_id"]:
        raise IntegrityError("event_id must be a non-empty string")
    if not isinstance(event["ledger_seq"], int) or event["ledger_seq"] < 1:
        raise IntegrityError("ledger_seq must be a positive integer")
    return event


def _chain_digest(previous_raw: bytes, record_digest_text: str) -> str:
    material = CHAIN_DOMAIN + previous_raw + _digest_bytes(record_digest_text)
    return _digest_text(sha256(material).digest())


def seal_records(records: list[bytes]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create one IntegrityRecord per ATL record plus a final LedgerAnchor."""
    if not records:
        raise IntegrityError("cannot seal an empty ledger")

    integrity: list[dict[str, Any]] = []
    previous_raw = GENESIS_DIGEST_BYTES
    previous_text: str | None = None
    run_id: str | None = None
    first_event_id: str | None = None
    last_event_id: str | None = None

    for index, record in enumerate(records, start=1):
        event = _parse_record(record)
        if event["ledger_seq"] != index:
            raise IntegrityError(f"ledger_seq must be contiguous from 1; got {event['ledger_seq']} at position {index}")
        if run_id is None:
            run_id = event["run_id"]
            first_event_id = event["event_id"]
        elif event["run_id"] != run_id:
            raise IntegrityError("all records in one integrity chain must share run_id")

        digest = record_digest(record)
        chain = _chain_digest(previous_raw, digest)
        integrity.append({
            "schema_version": INTEGRITY_SCHEMA_VERSION,
            "run_id": run_id,
            "ledger_seq": event["ledger_seq"],
            "event_id": event["event_id"],
            "hash_algorithm": HASH_ALGORITHM,
            "record_encoding": RECORD_ENCODING,
            "record_digest": digest,
            "previous_chain_digest": previous_text,
            "chain_digest": chain,
        })
        previous_raw = _digest_bytes(chain)
        previous_text = chain
        last_event_id = event["event_id"]

    anchor = {
        "schema_version": INTEGRITY_SCHEMA_VERSION,
        "run_id": run_id,
        "event_count": len(records),
        "first_event_id": first_event_id,
        "last_event_id": last_event_id,
        "hash_algorithm": HASH_ALGORITHM,
        "record_encoding": RECORD_ENCODING,
        "final_chain_digest": integrity[-1]["chain_digest"],
    }
    return integrity, anchor


def _failure_report(
    *,
    code: str,
    message: str,
    event_count: int,
    checked_records: int,
    anchor_checked: bool,
    head_digest: str | None,
    ledger_seq: int | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "valid": False,
        "event_count": event_count,
        "checked_records": checked_records,
        "anchor_checked": anchor_checked,
        "head_digest": head_digest,
        "failure": {
            "code": code,
            "ledger_seq": ledger_seq,
            "event_id": event_id,
            "message": message,
        },
    }


def verify_records(
    records: list[bytes],
    integrity_records: list[dict[str, Any]],
    anchor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify ATL record bytes against a sidecar chain and optional trusted anchor."""
    anchor_checked = anchor is not None
    if len(records) != len(integrity_records):
        return _failure_report(
            code="sidecar_count_mismatch",
            message="ledger and integrity sidecar contain different record counts",
            event_count=len(records),
            checked_records=0,
            anchor_checked=anchor_checked,
            head_digest=None,
        )
    if not records:
        return _failure_report(
            code="empty_ledger",
            message="cannot verify an empty ledger",
            event_count=0,
            checked_records=0,
            anchor_checked=anchor_checked,
            head_digest=None,
        )

    previous_raw = GENESIS_DIGEST_BYTES
    previous_text: str | None = None
    run_id: str | None = None
    first_event_id: str | None = None
    last_event_id: str | None = None
    head_digest: str | None = None

    for position, (record, sidecar) in enumerate(zip(records, integrity_records), start=1):
        try:
            event = _parse_record(record)
        except IntegrityError as exc:
            return _failure_report(
                code="invalid_record",
                message=str(exc),
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
            )

        seq = event["ledger_seq"]
        event_id = event["event_id"]
        if seq != position:
            return _failure_report(
                code="ledger_seq_mismatch",
                message=f"expected ledger_seq {position}, got {seq}",
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
                ledger_seq=seq,
                event_id=event_id,
            )
        if run_id is None:
            run_id = event["run_id"]
            first_event_id = event_id
        elif event["run_id"] != run_id:
            return _failure_report(
                code="run_id_mismatch",
                message="all records in one chain must share run_id",
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
                ledger_seq=seq,
                event_id=event_id,
            )

        if not isinstance(sidecar, dict):
            return _failure_report(
                code="invalid_integrity_record",
                message="integrity record must be a JSON object",
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
                ledger_seq=seq,
                event_id=event_id,
            )
        if sidecar.get("ledger_seq") != seq or sidecar.get("event_id") != event_id or sidecar.get("run_id") != run_id:
            return _failure_report(
                code="integrity_identity_mismatch",
                message="integrity record identity does not match ATL record",
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
                ledger_seq=seq,
                event_id=event_id,
            )
        if sidecar.get("hash_algorithm") != HASH_ALGORITHM or sidecar.get("record_encoding") != RECORD_ENCODING:
            return _failure_report(
                code="integrity_profile_mismatch",
                message="unsupported integrity hash algorithm or record encoding",
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
                ledger_seq=seq,
                event_id=event_id,
            )

        digest = record_digest(record)
        if sidecar.get("record_digest") != digest:
            return _failure_report(
                code="record_digest_mismatch",
                message="ATL record bytes do not match recorded SHA-256 digest",
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
                ledger_seq=seq,
                event_id=event_id,
            )
        if sidecar.get("previous_chain_digest") != previous_text:
            return _failure_report(
                code="previous_chain_digest_mismatch",
                message="integrity chain does not point to the previous chain digest",
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
                ledger_seq=seq,
                event_id=event_id,
            )

        expected_chain = _chain_digest(previous_raw, digest)
        if sidecar.get("chain_digest") != expected_chain:
            return _failure_report(
                code="chain_digest_mismatch",
                message="integrity chain digest does not match recomputed value",
                event_count=len(records),
                checked_records=position - 1,
                anchor_checked=anchor_checked,
                head_digest=head_digest,
                ledger_seq=seq,
                event_id=event_id,
            )

        previous_text = expected_chain
        previous_raw = _digest_bytes(expected_chain)
        head_digest = expected_chain
        last_event_id = event_id

    if anchor is not None:
        if anchor.get("event_count") != len(records):
            return _failure_report(
                code="anchor_event_count_mismatch",
                message=f"anchor expects {anchor.get('event_count')} events, ledger has {len(records)}",
                event_count=len(records),
                checked_records=len(records),
                anchor_checked=True,
                head_digest=head_digest,
                ledger_seq=len(records),
                event_id=last_event_id,
            )
        if anchor.get("run_id") != run_id or anchor.get("first_event_id") != first_event_id or anchor.get("last_event_id") != last_event_id:
            return _failure_report(
                code="anchor_identity_mismatch",
                message="anchor run or endpoint event identity does not match ledger",
                event_count=len(records),
                checked_records=len(records),
                anchor_checked=True,
                head_digest=head_digest,
                ledger_seq=len(records),
                event_id=last_event_id,
            )
        if anchor.get("hash_algorithm") != HASH_ALGORITHM or anchor.get("record_encoding") != RECORD_ENCODING:
            return _failure_report(
                code="anchor_profile_mismatch",
                message="anchor uses unsupported hash algorithm or record encoding",
                event_count=len(records),
                checked_records=len(records),
                anchor_checked=True,
                head_digest=head_digest,
                ledger_seq=len(records),
                event_id=last_event_id,
            )
        if anchor.get("final_chain_digest") != head_digest:
            return _failure_report(
                code="anchor_head_mismatch",
                message="anchor final chain digest does not match ledger head",
                event_count=len(records),
                checked_records=len(records),
                anchor_checked=True,
                head_digest=head_digest,
                ledger_seq=len(records),
                event_id=last_event_id,
            )

    return {
        "valid": True,
        "event_count": len(records),
        "checked_records": len(records),
        "anchor_checked": anchor_checked,
        "head_digest": head_digest,
        "failure": None,
    }


def read_jsonl_record_bytes(path: str | "Path") -> list[bytes]:
    """Read ATL JSONL as exact record bytes, excluding LF/CRLF separators."""
    from pathlib import Path

    data = Path(path).read_bytes()
    parts = data.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    records: list[bytes] = []
    for index, raw in enumerate(parts, start=1):
        if raw.endswith(b"\r"):
            raw = raw[:-1]
        if not raw or raw.strip() == b"":
            raise IntegrityError(f"blank JSONL record at line {index}")
        records.append(raw)
    if not records:
        raise IntegrityError("ledger JSONL contains no records")
    return records


def _read_integrity_jsonl(path: str | "Path") -> list[dict[str, Any]]:
    records = read_jsonl_record_bytes(path)
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(records, start=1):
        try:
            item = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntegrityError(f"invalid integrity JSON at line {index}") from exc
        if not isinstance(item, dict):
            raise IntegrityError(f"integrity record at line {index} must be an object")
        result.append(item)
    return result


def _write_jsonl(path: str | "Path", objects: list[dict[str, Any]]) -> None:
    from pathlib import Path

    payload = b"\n".join(
        json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        for item in objects
    ) + b"\n"
    Path(path).write_bytes(payload)


def seal_jsonl(
    path: str | "Path",
    chain_out: str | "Path",
    anchor_out: str | "Path",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = read_jsonl_record_bytes(path)
    integrity, anchor = seal_records(records)
    _write_jsonl(chain_out, integrity)
    from pathlib import Path
    Path(anchor_out).write_text(
        json.dumps(anchor, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return integrity, anchor


def verify_jsonl(
    path: str | "Path",
    chain_path: str | "Path",
    anchor_path: str | "Path" | None = None,
) -> dict[str, Any]:
    from pathlib import Path

    records = read_jsonl_record_bytes(path)
    integrity = _read_integrity_jsonl(chain_path)
    anchor = None
    if anchor_path is not None:
        try:
            anchor = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise IntegrityError("anchor is not valid JSON") from exc
        if not isinstance(anchor, dict):
            raise IntegrityError("anchor must be a JSON object")
    return verify_records(records, integrity, anchor)


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Seal or verify CTCL-ITR ATL JSONL integrity chains.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seal_parser = subparsers.add_parser("seal", help="Create integrity sidecar and ledger anchor")
    seal_parser.add_argument("path", help="ATL event JSONL path")
    seal_parser.add_argument("--chain-out", required=True, help="Output integrity JSONL path")
    seal_parser.add_argument("--anchor-out", required=True, help="Output ledger anchor JSON path")

    verify_parser = subparsers.add_parser("verify", help="Verify ATL event JSONL against integrity metadata")
    verify_parser.add_argument("path", help="ATL event JSONL path")
    verify_parser.add_argument("--chain", required=True, help="Integrity JSONL path")
    verify_parser.add_argument("--anchor", help="Optional trusted ledger anchor JSON path")

    args = parser.parse_args(argv)
    try:
        if args.command == "seal":
            integrity, anchor = seal_jsonl(args.path, args.chain_out, args.anchor_out)
            print(json.dumps({
                "sealed": True,
                "event_count": len(integrity),
                "final_chain_digest": anchor["final_chain_digest"],
                "chain_path": args.chain_out,
                "anchor_path": args.anchor_out,
            }, ensure_ascii=False, sort_keys=True))
            return 0
        report = verify_jsonl(args.path, args.chain, args.anchor)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["valid"] else 1
    except (IntegrityError, OSError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
