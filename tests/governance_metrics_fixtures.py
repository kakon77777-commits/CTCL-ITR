from ctcl_itr.governance import make_approval_request, make_authority_grant, make_decision_receipt


def request(a, risk="medium", exp="2026-08-20T09:00:00+00:00"):
    return make_approval_request(approval_id=a, run_id=f"run:{a}", intent_id=f"intent:{a}", trigger_event_id=f"evt:{a}", requested_action="publish", target="demo://published/release", risk_class=risk, reason="metrics", options=["approve","deny","defer"], evidence_refs=["validation:test"], authority_requested={"scope":["publish"],"max_uses":2}, requested_at="2026-08-20T08:00:00+00:00", expires_at=exp)


def decision(req, did, choice="approve", at="2026-08-20T08:10:00+00:00", ms=42000):
    return make_decision_receipt(decision_id=did, approval_id=req["approval_id"], run_id=req["run_id"], principal="user:neo", decision=choice, selected_option=choice, decided_at=at, human_active_ms=ms, human_governance_ms=ms, reason="metrics review")


def grant(rec, ref, exp="2026-08-20T09:00:00+00:00"):
    return make_authority_grant(authority_ref=ref, decision_id=rec["decision_id"], principal=rec["principal"], scope=["publish"], target="demo://published/release", issued_at="2026-08-20T08:10:01+00:00", expires_at=exp, max_uses=2, revocable=True)


def scenario():
    reqs=[request("approval:m1","medium","2026-08-20T09:00:00+00:00"),request("approval:h1","high","2026-08-20T08:30:00+00:00"),request("approval:c1","critical","2026-08-20T08:20:00+00:00"),request("approval:h2","high","2026-08-20T09:00:00+00:00"),request("approval:l1","low","2026-08-20T08:30:00+00:00")]
    by={r["approval_id"]:r for r in reqs}
    receipts=[decision(by["approval:m1"],"decision:m1",at="2026-08-20T08:10:00+00:00",ms=42000),decision(by["approval:h1"],"decision:h1","deny","2026-08-20T08:05:00+00:00",20000),decision(by["approval:h2"],"decision:h2","defer","2026-08-20T08:15:00+00:00",30000),decision(by["approval:l1"],"decision:l1",at="2026-08-20T08:40:00+00:00",ms=50000)]
    rec={r["decision_id"]:r for r in receipts}
    grants=[grant(rec["decision:m1"],"auth:m1")]
    events=[{"event_type":x} for x in ["action.completed","action.completed","validation.completed","validation.completed","commit.confirmed","human.checkpoint.resolved","human.checkpoint.resolved","human.checkpoint.resolved","human.checkpoint.resolved","run.suspended"]]
    deadlines={"approval:h1":"2026-08-20T08:15:00+00:00","approval:c1":"2026-08-20T08:20:00+00:00"}
    return reqs,receipts,grants,events,deadlines
