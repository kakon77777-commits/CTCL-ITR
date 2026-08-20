"""SQLite-backed durable governance queue for CTCL-ITR v0.2.4."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from .governance import GovernanceError, _parse_time, demo_payload, evaluate_resume_eligibility


SCHEMA_SQL = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS governance_approval_requests (
  approval_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  status TEXT NOT NULL,
  requested_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  state_version INTEGER NOT NULL DEFAULT 1,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS governance_decision_receipts (
  decision_id TEXT PRIMARY KEY,
  approval_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (approval_id) REFERENCES governance_approval_requests(approval_id)
);

CREATE TABLE IF NOT EXISTS governance_authority_grants (
  authority_ref TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  principal TEXT NOT NULL,
  state TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  uses INTEGER NOT NULL,
  max_uses INTEGER NOT NULL,
  state_version INTEGER NOT NULL DEFAULT 1,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (decision_id) REFERENCES governance_decision_receipts(decision_id)
);

CREATE TABLE IF NOT EXISTS governance_mutations (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  mutation_type TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_governance_request_status
ON governance_approval_requests(status, requested_at, approval_id);

CREATE INDEX IF NOT EXISTS idx_governance_receipt_approval
ON governance_decision_receipts(approval_id);

CREATE INDEX IF NOT EXISTS idx_governance_grant_decision
ON governance_authority_grants(decision_id);

CREATE TRIGGER IF NOT EXISTS governance_mutations_no_update
BEFORE UPDATE ON governance_mutations
BEGIN
  SELECT RAISE(ABORT, 'governance mutation journal is append-only');
END;

CREATE TRIGGER IF NOT EXISTS governance_mutations_no_delete
BEFORE DELETE ON governance_mutations
BEGIN
  SELECT RAISE(ABORT, 'governance mutation journal is append-only');
END;
"""


def _json_dump(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _json_load(value: str) -> dict[str, Any]:
    return json.loads(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteApprovalQueue:
    """Restart-safe SQLite projection of v0.2.3 ApprovalQueue semantics."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._conn.executescript(SCHEMA_SQL)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def __enter__(self) -> "SQLiteApprovalQueue":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
        except Exception:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")

    def _journal(self, conn: sqlite3.Connection, mutation_type: str, object_type: str, object_id: str, payload: dict[str, Any]) -> None:
        conn.execute(
            "INSERT INTO governance_mutations(mutation_type, object_type, object_id, created_at, payload_json) VALUES (?,?,?,?,?)",
            (mutation_type, object_type, object_id, _utc_now(), _json_dump(payload)),
        )

    def enqueue(self, approval_request: dict[str, Any]) -> None:
        approval_id = approval_request["approval_id"]
        payload = deepcopy(approval_request)
        try:
            with self._tx() as conn:
                conn.execute(
                    "INSERT INTO governance_approval_requests(approval_id, run_id, status, requested_at, expires_at, state_version, payload_json) VALUES (?,?,?,?,?,?,?)",
                    (
                        approval_id,
                        payload["run_id"],
                        payload.get("status", "pending"),
                        payload["requested_at"],
                        payload["expires_at"],
                        1,
                        _json_dump(payload),
                    ),
                )
                self._journal(conn, "approval.enqueued", "approval_request", approval_id, payload)
        except sqlite3.IntegrityError as exc:
            raise GovernanceError("duplicate approval_id") from exc

    def pending(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT payload_json FROM governance_approval_requests WHERE status='pending' ORDER BY requested_at, approval_id"
        ).fetchall()
        return [_json_load(row["payload_json"]) for row in rows]

    def list_requests(self, status: str | None = None) -> list[dict[str, Any]]:
        if status is None:
            rows = self._conn.execute(
                "SELECT payload_json FROM governance_approval_requests ORDER BY approval_id"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT payload_json FROM governance_approval_requests WHERE status=? ORDER BY approval_id",
                (status,),
            ).fetchall()
        return [_json_load(row["payload_json"]) for row in rows]

    def list_receipts(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT payload_json FROM governance_decision_receipts ORDER BY decision_id"
        ).fetchall()
        return [_json_load(row["payload_json"]) for row in rows]

    def list_grants(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT payload_json FROM governance_authority_grants ORDER BY authority_ref"
        ).fetchall()
        return [_json_load(row["payload_json"]) for row in rows]

    def get_request(self, approval_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT payload_json FROM governance_approval_requests WHERE approval_id=?", (approval_id,)
        ).fetchone()
        if row is None:
            raise GovernanceError("unknown approval_id")
        return _json_load(row["payload_json"])

    def get_receipt(self, decision_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT payload_json FROM governance_decision_receipts WHERE decision_id=?", (decision_id,)
        ).fetchone()
        if row is None:
            raise GovernanceError("unknown decision_id")
        return _json_load(row["payload_json"])

    def get_grant(self, authority_ref: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT payload_json FROM governance_authority_grants WHERE authority_ref=?", (authority_ref,)
        ).fetchone()
        if row is None:
            raise GovernanceError("unknown authority_ref")
        return _json_load(row["payload_json"])

    def _validate_resolve(self, req: dict[str, Any], decision_receipt: dict[str, Any], authority_grant: dict[str, Any] | None) -> str:
        if req.get("status") != "pending":
            raise GovernanceError("approval request is not pending")
        if decision_receipt["run_id"] != req["run_id"]:
            raise GovernanceError("decision run mismatch")
        if _parse_time(decision_receipt["decided_at"]) > _parse_time(req["expires_at"]):
            raise GovernanceError("approval request expired before decision")
        decision = decision_receipt["decision"]
        if authority_grant is not None and decision not in {"approve", "modify"}:
            raise GovernanceError("authority grant requires approve or modify")
        if authority_grant is not None and authority_grant["decision_id"] != decision_receipt["decision_id"]:
            raise GovernanceError("authority decision mismatch")
        return {
            "approve": "approved",
            "deny": "denied",
            "modify": "modified",
            "defer": "deferred",
            "cancel": "cancelled",
        }[decision]

    def resolve(self, decision_receipt: dict[str, Any], authority_grant: dict[str, Any] | None = None) -> None:
        approval_id = decision_receipt["approval_id"]
        with self._tx() as conn:
            row = conn.execute(
                "SELECT payload_json, state_version FROM governance_approval_requests WHERE approval_id=?", (approval_id,)
            ).fetchone()
            if row is None:
                raise GovernanceError("unknown approval_id")
            req = _json_load(row["payload_json"])
            new_status = self._validate_resolve(req, decision_receipt, authority_grant)

            if conn.execute("SELECT 1 FROM governance_decision_receipts WHERE decision_id=?", (decision_receipt["decision_id"],)).fetchone():
                raise GovernanceError("duplicate decision_id")
            if authority_grant is not None and conn.execute(
                "SELECT 1 FROM governance_authority_grants WHERE authority_ref=?", (authority_grant["authority_ref"],)
            ).fetchone():
                raise GovernanceError("duplicate authority_ref")

            req["status"] = new_status
            conn.execute(
                "UPDATE governance_approval_requests SET status=?, state_version=?, payload_json=? WHERE approval_id=?",
                (new_status, int(row["state_version"]) + 1, _json_dump(req), approval_id),
            )
            conn.execute(
                "INSERT INTO governance_decision_receipts(decision_id, approval_id, run_id, decided_at, payload_json) VALUES (?,?,?,?,?)",
                (
                    decision_receipt["decision_id"],
                    approval_id,
                    decision_receipt["run_id"],
                    decision_receipt["decided_at"],
                    _json_dump(decision_receipt),
                ),
            )
            self._journal(conn, "approval.resolved", "approval_request", approval_id, req)
            self._journal(conn, "decision.recorded", "decision_receipt", decision_receipt["decision_id"], decision_receipt)
            if authority_grant is not None:
                self._insert_grant(conn, authority_grant)

    def _insert_grant(self, conn: sqlite3.Connection, authority_grant: dict[str, Any]) -> None:
        grant = deepcopy(authority_grant)
        try:
            conn.execute(
                "INSERT INTO governance_authority_grants(authority_ref, decision_id, principal, state, expires_at, uses, max_uses, state_version, payload_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    grant["authority_ref"], grant["decision_id"], grant["principal"], grant.get("state", "active"),
                    grant["expires_at"], int(grant.get("uses", 0)), int(grant["max_uses"]), 1, _json_dump(grant),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise GovernanceError("duplicate authority_ref") from exc
        self._journal(conn, "authority.granted", "authority_grant", grant["authority_ref"], grant)

    def add_grant(self, authority_grant: dict[str, Any]) -> None:
        with self._tx() as conn:
            self._insert_grant(conn, authority_grant)

    def expire_due(self, at: str) -> list[str]:
        now = _parse_time(at)
        expired: list[str] = []
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT approval_id, payload_json, state_version FROM governance_approval_requests WHERE status='pending' ORDER BY requested_at, approval_id"
            ).fetchall()
            for row in rows:
                req = _json_load(row["payload_json"])
                if now >= _parse_time(req["expires_at"]):
                    req["status"] = "expired"
                    conn.execute(
                        "UPDATE governance_approval_requests SET status='expired', state_version=?, payload_json=? WHERE approval_id=?",
                        (int(row["state_version"]) + 1, _json_dump(req), row["approval_id"]),
                    )
                    self._journal(conn, "approval.expired", "approval_request", row["approval_id"], req)
                    expired.append(row["approval_id"])
        return expired

    def consume_authority(self, authority_ref: str, *, action: str, target: str, at: str) -> dict[str, Any]:
        expired = False
        result: dict[str, Any] | None = None
        with self._tx() as conn:
            row = conn.execute(
                "SELECT payload_json, state_version FROM governance_authority_grants WHERE authority_ref=?", (authority_ref,)
            ).fetchone()
            if row is None:
                raise GovernanceError("unknown authority_ref")
            grant = _json_load(row["payload_json"])
            if grant.get("state") != "active":
                raise GovernanceError("authority is not active")
            if _parse_time(at) > _parse_time(grant["expires_at"]):
                grant["state"] = "expired"
                conn.execute(
                    "UPDATE governance_authority_grants SET state='expired', state_version=?, payload_json=? WHERE authority_ref=?",
                    (int(row["state_version"]) + 1, _json_dump(grant), authority_ref),
                )
                self._journal(conn, "authority.expired", "authority_grant", authority_ref, grant)
                expired = True
            else:
                if action not in grant["scope"]:
                    raise GovernanceError("scope mismatch")
                if target != grant["target"]:
                    raise GovernanceError("target mismatch")
                grant["uses"] = int(grant.get("uses", 0)) + 1
                if grant["uses"] >= int(grant["max_uses"]):
                    grant["state"] = "consumed"
                conn.execute(
                    "UPDATE governance_authority_grants SET state=?, uses=?, state_version=?, payload_json=? WHERE authority_ref=?",
                    (grant["state"], grant["uses"], int(row["state_version"]) + 1, _json_dump(grant), authority_ref),
                )
                self._journal(conn, "authority.consumed", "authority_grant", authority_ref, grant)
                result = deepcopy(grant)
        if expired:
            raise GovernanceError("authority expired")
        assert result is not None
        return result

    def revoke_authority(self, authority_ref: str, *, reason: str) -> None:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT payload_json, state_version FROM governance_authority_grants WHERE authority_ref=?", (authority_ref,)
            ).fetchone()
            if row is None:
                raise GovernanceError("unknown authority_ref")
            grant = _json_load(row["payload_json"])
            if not grant.get("revocable", False):
                raise GovernanceError("authority is not revocable")
            grant["state"] = "revoked"
            grant["revocation_reason"] = reason
            conn.execute(
                "UPDATE governance_authority_grants SET state='revoked', state_version=?, payload_json=? WHERE authority_ref=?",
                (int(row["state_version"]) + 1, _json_dump(grant), authority_ref),
            )
            self._journal(conn, "authority.revoked", "authority_grant", authority_ref, grant)

    def journal_entries(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT seq, mutation_type, object_type, object_id, created_at, payload_json FROM governance_mutations ORDER BY seq"
        ).fetchall()
        return [
            {
                "seq": int(row["seq"]),
                "mutation_type": row["mutation_type"],
                "object_type": row["object_type"],
                "object_id": row["object_id"],
                "created_at": row["created_at"],
                "payload": _json_load(row["payload_json"]),
            }
            for row in rows
        ]

    def counts(self) -> dict[str, int]:
        return {
            "approval_requests": int(self._conn.execute("SELECT COUNT(*) FROM governance_approval_requests").fetchone()[0]),
            "decision_receipts": int(self._conn.execute("SELECT COUNT(*) FROM governance_decision_receipts").fetchone()[0]),
            "authority_grants": int(self._conn.execute("SELECT COUNT(*) FROM governance_authority_grants").fetchone()[0]),
            "mutations": int(self._conn.execute("SELECT COUNT(*) FROM governance_mutations").fetchone()[0]),
        }



def _demo_database(path: str | Path) -> dict[str, Any]:
    demo = demo_payload()
    approval = demo["approval_request"]
    receipt = demo["decision_receipt"]
    grant = demo["authority_grant"]

    q = SQLiteApprovalQueue(path)
    try:
        if q.counts()["approval_requests"] == 0:
            q.enqueue(approval)
            q.resolve(receipt, grant)
        counts_before = q.counts()
    finally:
        q.close()

    q2 = SQLiteApprovalQueue(path)
    try:
        restored_request = q2.get_request(approval["approval_id"])
        restored_receipt = q2.get_receipt(receipt["decision_id"])
        restored_grant = q2.get_grant(grant["authority_ref"])
        eligibility = evaluate_resume_eligibility(
            restored_request,
            restored_receipt,
            restored_grant,
            action="publish",
            target=restored_request["target"],
            at="2026-08-20T08:11:00+00:00",
        )
        return {
            "database": str(Path(path)),
            "counts": q2.counts(),
            "counts_before_restart": counts_before,
            "recovered": {
                "request_status": restored_request["status"],
                "decision": restored_receipt["decision"],
                "authority_state": restored_grant["state"],
                "resume_eligible": eligibility["eligible"],
            },
        }
    finally:
        q2.close()


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CTCL-ITR durable governance store")
    sub = parser.add_subparsers(dest="command", required=True)

    demo_parser = sub.add_parser("demo", help="persist and recover the reference governance handoff")
    demo_parser.add_argument("--db", required=True)
    demo_parser.add_argument("--pretty", action="store_true")

    status_parser = sub.add_parser("status", help="report durable governance object counts")
    status_parser.add_argument("--db", required=True)
    status_parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args()
    if args.command == "demo":
        payload = _demo_database(args.db)
    else:
        q = SQLiteApprovalQueue(args.db)
        try:
            payload = {"database": str(Path(args.db)), "counts": q.counts()}
        finally:
            q.close()
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    _main()
