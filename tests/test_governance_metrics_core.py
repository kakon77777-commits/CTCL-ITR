import pytest
from ctcl_itr.governance_metrics import GovernanceMetricsError, analyze_governance, default_metrics_policy
from governance_metrics_fixtures import request, scenario


def test_metrics_core_values():
    reqs,recs,grants,events,deadlines=scenario()
    r=analyze_governance(approval_requests=reqs,decision_receipts=recs,authority_grants=grants,events=events,at="2026-08-20T10:00:00+00:00",intervention_deadlines=deadlines,policy=default_metrics_policy())
    assert r["human_intervention_density"]["value"]==4/9
    assert r["effective_oversight_density"]["value"]==6/19
    assert r["escalation_latency"]=={"count":4,"mean_ms":1050000.0,"p50_ms":600000,"p95_ms":2400000,"max_ms":2400000}
    t={x["approval_id"]:x for x in r["intervention_timing"]["items"]}
    assert t["approval:h1"]["timing_basis"]=="explicit_intervention_deadline" and t["approval:h1"]["margin_ms"]==600000
    assert t["approval:l1"]["timing_basis"]=="approval_expiry_proxy" and t["approval:l1"]["margin_ms"]==-600000
    assert t["approval:h2"]["decision"]=="defer" and t["approval:h2"]["open_age_ms"]==7200000
    assert t["approval:c1"]["decision_id"] is None and t["approval:c1"]["open_age_ms"]==7200000
    d=r["oversight_debt"]; assert (d["unresolved_weight"],d["overdue_weight"],d["deferred_weight"],d["stale_authority_weight"],d["total_weight"])==(12,12,4,2,28)
    assert r["human_time"]["human_governance_ms_total"]==142000
    assert r["risk_coverage"]["critical"]["effective"]==0 and r["risk_coverage"]["high"]["effective"]==1


def test_zero_transition_denominator_is_null():
    req=request("approval:zero")
    r=analyze_governance(approval_requests=[req],decision_receipts=[],authority_grants=[],events=[{"event_type":"run.started"}],at="2026-08-20T08:10:00+00:00")
    assert r["human_intervention_density"]["value"] is None


def test_bad_deadline_rejected():
    req=request("approval:bad")
    with pytest.raises(GovernanceMetricsError,match="deadline must be after requested_at"):
        analyze_governance(approval_requests=[req],decision_receipts=[],authority_grants=[],events=[],at="2026-08-20T08:10:00+00:00",intervention_deadlines={req["approval_id"]:req["requested_at"]})
