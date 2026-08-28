from pathlib import Path

import pytest

from ctcl_itr.governance import GovernanceError, make_approval_request, make_authority_grant, make_decision_receipt
from ctcl_itr.governance_store import SQLiteApprovalQueue

NOW = "2026-08-20T08:00:00+00:00"
LATER = "2026-08-20T09:00:00+00:00"


def request(**overrides):
    data = dict(
        approval_id="approval:durable-001",
        run_id="run:durable-001",
        intent_id="intent:durable-001",
        trigger_event_id="evt_durable_001",
        requested_action="publish",
        target="demo://published/release",
        risk_class="medium",
        reason="external publish requires approval",
        options=["approve", "deny"],
        evidence_refs=["val:durable"],
        authority_requested={"scope": ["publish"], "max_uses": 2},
        requested_at=NOW,
        expires_at=LATER,
    )
    data.update(overrides)
    return make_approval_request(**data)


def decision(req, **overrides):
    data = dict(
        decision_id="decision:durable-001",
        approval_id=req["approval_id"],
        run_id=req["run_id"],
        principal="user:neo",
        decision="approve",
        selected_option="approve",
        decided_at="2026-08-20T08:10:00+00:00",
        human_active_ms=42000,
        human_governance_ms=42000,
        reason="approved after review",
    )
    data.update(overrides)
    return make_decision_receipt(**data)


def grant(rec, **overrides):
    data = dict(
        authority_ref="auth:durable-001",
        decision_id=rec["decision_id"],
        principal=rec["principal"],
        scope=["publish"],
        target="demo://published/release",
        issued_at="2026-08-20T08:10:01+00:00",
        expires_at=LATER,
        max_uses=2,
        revocable=True,
    )
    data.update(overrides)
    return make_authority_grant(**data)


def test_pending_request_survives_reopen(tmp_path: Path):
    db = tmp_path / "governance.sqlite3"
    q = SQLiteApprovalQueue(db)
    req = request()
    q.enqueue(req)
    q.close()

    q2 = SQLiteApprovalQueue(db)
    assert [item["approval_id"] for item in q2.pending()] == [req["approval_id"]]
    assert q2.get_request(req["approval_id"])["status"] == "pending"
    q2.close()


def test_resolved_receipt_and_grant_survive_reopen(tmp_path: Path):
    db = tmp_path / "governance.sqlite3"
    req = request()
    rec = decision(req)
    auth = grant(rec)
    q = SQLiteApprovalQueue(db)
    q.enqueue(req)
    q.resolve(rec, auth)
    q.close()

    q2 = SQLiteApprovalQueue(db)
    assert q2.get_request(req["approval_id"])["status"] == "approved"
    assert q2.get_receipt(rec["decision_id"]) == rec
    assert q2.get_grant(auth["authority_ref"])["state"] == "active"
    q2.close()


def test_resolve_is_atomic_when_grant_is_invalid(tmp_path: Path):
    db = tmp_path / "governance.sqlite3"
    req = request()
    rec = decision(req)
    bad_grant = grant(rec, decision_id="decision:wrong")
    q = SQLiteApprovalQueue(db)
    q.enqueue(req)
    with pytest.raises(GovernanceError, match="authority decision mismatch"):
        q.resolve(rec, bad_grant)
    assert q.get_request(req["approval_id"])["status"] == "pending"
    with pytest.raises(GovernanceError, match="unknown decision_id"):
        q.get_receipt(rec["decision_id"])
    q.close()


def test_duplicate_approval_remains_rejected_after_reopen(tmp_path: Path):
    db = tmp_path / "governance.sqlite3"
    req = request()
    q = SQLiteApprovalQueue(db)
    q.enqueue(req)
    q.close()
    q2 = SQLiteApprovalQueue(db)
    with pytest.raises(GovernanceError, match="duplicate approval_id"):
        q2.enqueue(req)
    q2.close()


def test_authority_use_count_and_exhaustion_survive_reopen(tmp_path: Path):
    db = tmp_path / "governance.sqlite3"
    req = request()
    rec = decision(req)
    auth = grant(rec, max_uses=2)
    q = SQLiteApprovalQueue(db)
    q.enqueue(req)
    q.resolve(rec, auth)
    first = q.consume_authority(auth["authority_ref"], action="publish", target=req["target"], at=NOW)
    assert first["uses"] == 1
    assert first["state"] == "active"
    q.close()

    q2 = SQLiteApprovalQueue(db)
    second = q2.consume_authority(auth["authority_ref"], action="publish", target=req["target"], at=NOW)
    assert second["uses"] == 2
    assert second["state"] == "consumed"
    q2.close()


def test_revocation_survives_reopen(tmp_path: Path):
    db = tmp_path / "governance.sqlite3"
    req = request()
    rec = decision(req)
    auth = grant(rec)
    q = SQLiteApprovalQueue(db)
    q.enqueue(req)
    q.resolve(rec, auth)
    q.revoke_authority(auth["authority_ref"], reason="principal revoked")
    q.close()

    q2 = SQLiteApprovalQueue(db)
    restored = q2.get_grant(auth["authority_ref"])
    assert restored["state"] == "revoked"
    assert restored["revocation_reason"] == "principal revoked"
    q2.close()


def test_expire_due_persists_status_and_journal(tmp_path: Path):
    db = tmp_path / "governance.sqlite3"
    req = request(expires_at="2026-08-20T07:00:00+00:00")
    q = SQLiteApprovalQueue(db)
    q.enqueue(req)
    assert q.expire_due(NOW) == [req["approval_id"]]
    before = q.journal_entries()
    assert [item["mutation_type"] for item in before][-1] == "approval.expired"
    q.close()

    q2 = SQLiteApprovalQueue(db)
    assert q2.get_request(req["approval_id"])["status"] == "expired"
    assert q2.pending() == []
    assert len(q2.journal_entries()) == len(before)
    q2.close()


def test_governance_store_cli_demo_recovers_after_reopen(tmp_path: Path):
    import json
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    db = tmp_path / "cli.sqlite3"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "ctcl_itr.governance_store", "demo", "--db", str(db)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["recovered"]["request_status"] == "approved"
    assert payload["recovered"]["authority_state"] == "active"
    assert payload["recovered"]["resume_eligible"] is True
    assert payload["counts"]["approval_requests"] == 1
    assert payload["counts"]["decision_receipts"] == 1
    assert payload["counts"]["authority_grants"] == 1
    assert payload["counts"]["mutations"] >= 4


def test_governance_store_sql_reference_exists():
    root = Path(__file__).resolve().parents[1]
    sql = (root / "sql" / "governance_store.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS governance_approval_requests" in sql
    assert "CREATE TABLE IF NOT EXISTS governance_mutations" in sql
    assert "governance_mutations_no_update" in sql


def test_mutation_journal_is_append_only(tmp_path: Path):
    import sqlite3

    db = tmp_path / "governance.sqlite3"
    q = SQLiteApprovalQueue(db)
    q.enqueue(request())
    q.close()

    conn = sqlite3.connect(db)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE governance_mutations SET mutation_type='tampered' WHERE seq=1")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM governance_mutations WHERE seq=1")
    conn.close()


def test_expired_authority_state_is_persisted_before_error(tmp_path: Path):
    db = tmp_path / "governance.sqlite3"
    req = request()
    rec = decision(req)
    auth = grant(rec, expires_at="2026-08-20T07:00:00+00:00")
    q = SQLiteApprovalQueue(db)
    q.enqueue(req)
    q.resolve(rec, auth)
    with pytest.raises(GovernanceError, match="authority expired"):
        q.consume_authority(auth["authority_ref"], action="publish", target=req["target"], at=NOW)
    q.close()

    q2 = SQLiteApprovalQueue(db)
    assert q2.get_grant(auth["authority_ref"])["state"] == "expired"
    assert q2.journal_entries()[-1]["mutation_type"] == "authority.expired"
    q2.close()
