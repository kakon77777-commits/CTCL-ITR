import pytest
from ctcl_itr.governance import ApprovalQueue, GovernanceError, evaluate_resume_eligibility, make_approval_request, make_authority_grant, make_decision_receipt

NOW="2026-08-20T08:00:00+00:00"; LATER="2026-08-20T09:00:00+00:00"; EXPIRED="2026-08-20T07:00:00+00:00"

def request(**overrides):
    data=dict(approval_id="approval:demo-001",run_id="run:demo-001",intent_id="intent:demo-001",trigger_event_id="evt_010",requested_action="publish",target="demo://published/release",risk_class="medium",reason="external publish requires approval",options=["approve","deny"],evidence_refs=["val:2"],authority_requested={"scope":["publish"],"max_uses":1},requested_at=NOW,expires_at=LATER); data.update(overrides); return make_approval_request(**data)

def decision(req,**overrides):
    data=dict(decision_id="decision:demo-001",approval_id=req["approval_id"],run_id=req["run_id"],principal="user:neo",decision="approve",selected_option="approve",decided_at="2026-08-20T08:10:00+00:00",human_active_ms=42000,human_governance_ms=42000,reason="approved after validator pass"); data.update(overrides); return make_decision_receipt(**data)

def grant(rec,**overrides):
    data=dict(authority_ref="auth:demo-001",decision_id=rec["decision_id"],principal=rec["principal"],scope=["publish"],target="demo://published/release",issued_at="2026-08-20T08:10:01+00:00",expires_at=LATER,max_uses=1,revocable=True); data.update(overrides); return make_authority_grant(**data)

def test_queue_lifecycle_and_duplicate_rejection():
    q=ApprovalQueue(); req=request(); q.enqueue(req); assert q.pending()[0]["approval_id"]==req["approval_id"]
    with pytest.raises(GovernanceError,match="duplicate approval_id"): q.enqueue(req)
    rec=decision(req); auth=grant(rec); q.resolve(rec,auth); assert q.get_request(req["approval_id"])["status"]=="approved"; assert q.get_grant(auth["authority_ref"])["state"]=="active"

def test_denied_decision_cannot_create_authority():
    q=ApprovalQueue(); req=request(); q.enqueue(req); rec=decision(req,decision="deny",selected_option="deny")
    with pytest.raises(GovernanceError,match="authority grant requires approve or modify"): q.resolve(rec,grant(rec))
    q.resolve(rec); assert q.get_request(req["approval_id"])["status"]=="denied"

def test_expiration_and_resume_contract():
    q=ApprovalQueue(); req=request(expires_at=EXPIRED); q.enqueue(req); assert q.expire_due(NOW)==[req["approval_id"]]
    req=request(); rec=decision(req); auth=grant(rec)
    assert evaluate_resume_eligibility(req,rec,auth,action="publish",target=req["target"],at=NOW)["eligible"] is True
    assert evaluate_resume_eligibility(req,rec,auth,action="delete",target=req["target"],at=NOW)["reasons"]==["scope_mismatch"]
    assert evaluate_resume_eligibility(req,rec,auth,action="publish",target="demo://other",at=NOW)["reasons"]==["target_mismatch"]
    assert evaluate_resume_eligibility(req,rec,auth,action="publish",target=req["target"],at="2026-08-20T10:00:00+00:00")["reasons"]==["authority_expired"]

def test_consumption_revocation_and_modified_authority():
    q=ApprovalQueue(); req=request(); q.enqueue(req); rec=decision(req); auth=grant(rec); q.resolve(rec,auth)
    used=q.consume_authority(auth["authority_ref"],action="publish",target=req["target"],at=NOW); assert used["state"]=="consumed"; assert evaluate_resume_eligibility(req,rec,used,action="publish",target=req["target"],at=NOW)["reasons"]==["authority_exhausted"]
    req2=request(approval_id="approval:demo-002",authority_requested={"scope":["publish","notify"],"max_uses":2}); rec2=decision(req2,decision_id="decision:demo-002",decision="modify",selected_option="approve_publish_only"); auth2=grant(rec2,authority_ref="auth:demo-002",scope=["publish"],max_uses=2); q.enqueue(req2); q.resolve(rec2,auth2); q.revoke_authority(auth2["authority_ref"],reason="principal revoked"); assert evaluate_resume_eligibility(req2,rec2,q.get_grant(auth2["authority_ref"]),action="publish",target=req2["target"],at=NOW)["reasons"]==["authority_revoked"]
