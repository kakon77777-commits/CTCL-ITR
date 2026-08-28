from datetime import datetime, timezone

import pytest

from ctcl_itr.governance import (
    ApprovalQueue,
    GovernanceError,
    evaluate_resume_eligibility,
    make_approval_request,
    make_authority_grant,
    make_decision_receipt,
)

NOW = "2026-08-20T08:00:00+00:00"
LATER = "2026-08-20T09:00:00+00:00"
EXPIRED = "2026-08-20T07:00:00+00:00"


def request(**overrides):
    data = dict(
        approval_id="approval:demo-001",
        run_id="run:demo-001",
        intent_id="intent:demo-001",
        trigger_event_id="evt_010",
        requested_action="publish",
        target="demo://published/release",
        risk_class="medium",
        reason="external publish requires approval",
        options=["approve", "deny"],
        evidence_refs=["val:2"],
        authority_requested={"scope": ["publish"], "max_uses": 1},
        requested_at=NOW,
        expires_at=LATER,
    )
    data.update(overrides)
    return make_approval_request(**data)


def decision(req, **overrides):
    data = dict(
        decision_id="decision:demo-001",
        approval_id=req["approval_id"],
        run_id=req["run_id"],
        principal="user:neo",
        decision="approve",
        selected_option="approve",
        decided_at="2026-08-20T08:10:00+00:00",
        human_active_ms=42000,
        human_governance_ms=42000,
        reason="approved after validator pass",
    )
    data.update(overrides)
    return make_decision_receipt(**data)


def grant(rec, **overrides):
    data = dict(
        authority_ref="auth:demo-001",
        decision_id=rec["decision_id"],
        principal=rec["principal"],
        scope=["publish"],
        target="demo://published/release",
        issued_at="2026-08-20T08:10:01+00:00",
        expires_at=LATER,
        max_uses=1,
        revocable=True,
    )
    data.update(overrides)
    return make_authority_grant(**data)


def test_queue_enqueues_and_lists_pending_requests():
    q = ApprovalQueue()
    req = request()
    q.enqueue(req)
    assert [x["approval_id"] for x in q.pending()] == [req["approval_id"]]
    assert q.get_request(req["approval_id"])["status"] == "pending"


def test_queue_rejects_duplicate_approval_id():
    q = ApprovalQueue()
    req = request()
    q.enqueue(req)
    with pytest.raises(GovernanceError, match="duplicate approval_id"):
        q.enqueue(req)


def test_queue_resolve_approve_records_receipt_and_grant():
    q = ApprovalQueue()
    req = request()
    q.enqueue(req)
    rec = decision(req)
    authority = grant(rec)
    q.resolve(rec, authority)
    assert q.get_request(req["approval_id"])["status"] == "approved"
    assert q.get_receipt(rec["decision_id"]) == rec
    assert q.get_grant(authority["authority_ref"])["state"] == "active"
    assert q.pending() == []


def test_denied_decision_cannot_create_authority():
    q = ApprovalQueue()
    req = request()
    q.enqueue(req)
    rec = decision(req, decision="deny", selected_option="deny")
    with pytest.raises(GovernanceError, match="authority grant requires approve or modify"):
        q.resolve(rec, grant(rec))
    q.resolve(rec)
    assert q.get_request(req["approval_id"])["status"] == "denied"


def test_expire_due_requests_marks_pending_request_expired():
    q = ApprovalQueue()
    req = request(expires_at=EXPIRED)
    q.enqueue(req)
    expired = q.expire_due(NOW)
    assert expired == [req["approval_id"]]
    assert q.get_request(req["approval_id"])["status"] == "expired"


def test_resume_eligibility_allows_active_matching_grant():
    req = request()
    rec = decision(req)
    authority = grant(rec)
    report = evaluate_resume_eligibility(req, rec, authority, action="publish", target=req["target"], at=NOW)
    assert report == {"eligible": True, "reasons": [], "authority_ref": authority["authority_ref"], "remaining_uses": 1}


def test_resume_eligibility_rejects_scope_target_expiry_and_denial():
    req = request()
    rec = decision(req)
    authority = grant(rec)

    assert evaluate_resume_eligibility(req, rec, authority, action="delete", target=req["target"], at=NOW)["reasons"] == ["scope_mismatch"]
    assert evaluate_resume_eligibility(req, rec, authority, action="publish", target="demo://other", at=NOW)["reasons"] == ["target_mismatch"]
    assert evaluate_resume_eligibility(req, rec, authority, action="publish", target=req["target"], at="2026-08-20T10:00:00+00:00")["reasons"] == ["authority_expired"]

    denied = decision(req, decision="deny", selected_option="deny")
    denied_report = evaluate_resume_eligibility(req, denied, None, action="publish", target=req["target"], at=NOW)
    assert denied_report["eligible"] is False
    assert denied_report["reasons"] == ["decision_not_authorizing", "authority_missing"]


def test_authority_consume_and_revoke_block_future_resume():
    q = ApprovalQueue()
    req = request()
    q.enqueue(req)
    rec = decision(req)
    authority = grant(rec)
    q.resolve(rec, authority)

    used = q.consume_authority(authority["authority_ref"], action="publish", target=req["target"], at=NOW)
    assert used["state"] == "consumed"
    exhausted = evaluate_resume_eligibility(req, rec, used, action="publish", target=req["target"], at=NOW)
    assert exhausted["reasons"] == ["authority_exhausted"]

    authority2 = grant(rec, authority_ref="auth:demo-002", max_uses=2)
    q.add_grant(authority2)
    q.revoke_authority(authority2["authority_ref"], reason="principal revoked")
    revoked = q.get_grant(authority2["authority_ref"])
    assert revoked["state"] == "revoked"
    report = evaluate_resume_eligibility(req, rec, revoked, action="publish", target=req["target"], at=NOW)
    assert report["reasons"] == ["authority_revoked"]


def test_modified_decision_can_issue_narrowed_authority():
    req = request(authority_requested={"scope": ["publish", "notify"], "max_uses": 2})
    rec = decision(req, decision="modify", selected_option="approve_publish_only")
    authority = grant(rec, scope=["publish"], max_uses=1)
    q = ApprovalQueue()
    q.enqueue(req)
    q.resolve(rec, authority)
    assert q.get_request(req["approval_id"])["status"] == "modified"
    assert q.get_grant(authority["authority_ref"])["scope"] == ["publish"]
