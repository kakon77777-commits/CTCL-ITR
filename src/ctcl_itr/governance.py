"""CTCL-ITR v0.2.3 reference governance semantics."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any


class GovernanceError(ValueError):
    pass


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise GovernanceError(f"invalid datetime: {value}") from exc


def make_approval_request(**kwargs: Any) -> dict[str, Any]:
    required = ["approval_id", "run_id", "intent_id", "trigger_event_id", "requested_action", "target", "risk_class", "reason", "options", "evidence_refs", "authority_requested", "requested_at", "expires_at"]
    for key in required:
        if key not in kwargs:
            raise GovernanceError(f"missing {key}")
    if kwargs["risk_class"] not in {"low", "medium", "high", "critical"}:
        raise GovernanceError("invalid risk_class")
    if not kwargs["options"]:
        raise GovernanceError("options must not be empty")
    _parse_time(kwargs["requested_at"])
    _parse_time(kwargs["expires_at"])
    return {"schema_version": "0.2.3", **deepcopy(kwargs), "status": "pending"}


def make_decision_receipt(**kwargs: Any) -> dict[str, Any]:
    required = ["decision_id", "approval_id", "run_id", "principal", "decision", "selected_option", "decided_at", "human_active_ms", "human_governance_ms"]
    for key in required:
        if key not in kwargs:
            raise GovernanceError(f"missing {key}")
    if kwargs["decision"] not in {"approve", "deny", "modify", "defer", "cancel"}:
        raise GovernanceError("invalid decision")
    if kwargs["human_active_ms"] < 0 or kwargs["human_governance_ms"] < 0:
        raise GovernanceError("human time must be nonnegative")
    _parse_time(kwargs["decided_at"])
    return {"schema_version": "0.2.3", **deepcopy(kwargs)}


def make_authority_grant(**kwargs: Any) -> dict[str, Any]:
    required = ["authority_ref", "decision_id", "principal", "scope", "target", "issued_at", "expires_at", "max_uses", "revocable"]
    for key in required:
        if key not in kwargs:
            raise GovernanceError(f"missing {key}")
    if not kwargs["scope"]:
        raise GovernanceError("scope must not be empty")
    if int(kwargs["max_uses"]) < 1:
        raise GovernanceError("max_uses must be >= 1")
    _parse_time(kwargs["issued_at"])
    _parse_time(kwargs["expires_at"])
    return {"schema_version": "0.2.3", **deepcopy(kwargs), "uses": 0, "state": "active", "revocation_reason": None}


def evaluate_resume_eligibility(approval_request: dict[str, Any], decision_receipt: dict[str, Any] | None, authority_grant: dict[str, Any] | None, *, action: str, target: str, at: str) -> dict[str, Any]:
    reasons: list[str] = []
    now = _parse_time(at)
    if decision_receipt is None or decision_receipt.get("decision") not in {"approve", "modify"}:
        reasons.append("decision_not_authorizing")
    if authority_grant is None:
        reasons.append("authority_missing")
        return {"eligible": False, "reasons": reasons, "authority_ref": None, "remaining_uses": 0}
    state = authority_grant.get("state", "active")
    if state == "revoked":
        reasons.append("authority_revoked")
    elif state in {"consumed", "exhausted"} or int(authority_grant.get("uses", 0)) >= int(authority_grant["max_uses"]):
        reasons.append("authority_exhausted")
    if now > _parse_time(authority_grant["expires_at"]):
        reasons.append("authority_expired")
    if action not in authority_grant.get("scope", []):
        reasons.append("scope_mismatch")
    if target != authority_grant.get("target"):
        reasons.append("target_mismatch")
    if decision_receipt is not None and authority_grant.get("decision_id") != decision_receipt.get("decision_id"):
        reasons.append("decision_authority_mismatch")
    if decision_receipt is not None and decision_receipt.get("approval_id") != approval_request.get("approval_id"):
        reasons.append("approval_decision_mismatch")
    remaining = max(0, int(authority_grant["max_uses"]) - int(authority_grant.get("uses", 0)))
    return {"eligible": not reasons, "reasons": reasons, "authority_ref": authority_grant.get("authority_ref"), "remaining_uses": remaining}


class ApprovalQueue:
    def __init__(self) -> None:
        self._requests: dict[str, dict[str, Any]] = {}
        self._receipts: dict[str, dict[str, Any]] = {}
        self._grants: dict[str, dict[str, Any]] = {}

    def enqueue(self, approval_request: dict[str, Any]) -> None:
        approval_id = approval_request["approval_id"]
        if approval_id in self._requests:
            raise GovernanceError("duplicate approval_id")
        self._requests[approval_id] = deepcopy(approval_request)

    def pending(self) -> list[dict[str, Any]]:
        return [deepcopy(v) for v in self._requests.values() if v.get("status") == "pending"]

    def get_request(self, approval_id: str) -> dict[str, Any]:
        if approval_id not in self._requests:
            raise GovernanceError("unknown approval_id")
        return deepcopy(self._requests[approval_id])

    def get_receipt(self, decision_id: str) -> dict[str, Any]:
        if decision_id not in self._receipts:
            raise GovernanceError("unknown decision_id")
        return deepcopy(self._receipts[decision_id])

    def get_grant(self, authority_ref: str) -> dict[str, Any]:
        if authority_ref not in self._grants:
            raise GovernanceError("unknown authority_ref")
        return deepcopy(self._grants[authority_ref])

    def resolve(self, decision_receipt: dict[str, Any], authority_grant: dict[str, Any] | None = None) -> None:
        approval_id = decision_receipt["approval_id"]
        if approval_id not in self._requests:
            raise GovernanceError("unknown approval_id")
        req = self._requests[approval_id]
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
        req["status"] = {"approve": "approved", "deny": "denied", "modify": "modified", "defer": "deferred", "cancel": "cancelled"}[decision]
        self._receipts[decision_receipt["decision_id"]] = deepcopy(decision_receipt)
        if authority_grant is not None:
            self.add_grant(authority_grant)

    def expire_due(self, at: str) -> list[str]:
        now = _parse_time(at)
        expired: list[str] = []
        for approval_id, req in self._requests.items():
            if req.get("status") == "pending" and now >= _parse_time(req["expires_at"]):
                req["status"] = "expired"
                expired.append(approval_id)
        return expired

    def add_grant(self, authority_grant: dict[str, Any]) -> None:
        ref = authority_grant["authority_ref"]
        if ref in self._grants:
            raise GovernanceError("duplicate authority_ref")
        self._grants[ref] = deepcopy(authority_grant)

    def consume_authority(self, authority_ref: str, *, action: str, target: str, at: str) -> dict[str, Any]:
        if authority_ref not in self._grants:
            raise GovernanceError("unknown authority_ref")
        grant = self._grants[authority_ref]
        if grant.get("state") != "active":
            raise GovernanceError("authority is not active")
        if _parse_time(at) > _parse_time(grant["expires_at"]):
            grant["state"] = "expired"
            raise GovernanceError("authority expired")
        if action not in grant["scope"]:
            raise GovernanceError("scope mismatch")
        if target != grant["target"]:
            raise GovernanceError("target mismatch")
        grant["uses"] += 1
        if grant["uses"] >= grant["max_uses"]:
            grant["state"] = "consumed"
        return deepcopy(grant)

    def revoke_authority(self, authority_ref: str, *, reason: str) -> None:
        if authority_ref not in self._grants:
            raise GovernanceError("unknown authority_ref")
        grant = self._grants[authority_ref]
        if not grant.get("revocable", False):
            raise GovernanceError("authority is not revocable")
        grant["state"] = "revoked"
        grant["revocation_reason"] = reason


def demo_payload() -> dict[str, Any]:
    approval = make_approval_request(approval_id="approval:gov-001", run_id="run:gov-001", intent_id="intent:gov-001", trigger_event_id="evt_gov_001", requested_action="publish", target="demo://published/release", risk_class="medium", reason="external publish requires human authorization", options=["approve", "deny"], evidence_refs=["validation:gov-001"], authority_requested={"scope": ["publish"], "max_uses": 1}, requested_at="2026-08-20T08:00:00+00:00", expires_at="2026-08-20T09:00:00+00:00")
    receipt = make_decision_receipt(decision_id="decision:gov-001", approval_id=approval["approval_id"], run_id=approval["run_id"], principal="user:neo", decision="approve", selected_option="approve", decided_at="2026-08-20T08:10:00+00:00", human_active_ms=42000, human_governance_ms=42000, reason="approved after validator pass")
    authority = make_authority_grant(authority_ref="auth:gov-001", decision_id=receipt["decision_id"], principal=receipt["principal"], scope=["publish"], target=approval["target"], issued_at="2026-08-20T08:10:01+00:00", expires_at="2026-08-20T09:00:00+00:00", max_uses=1, revocable=True)
    eligibility = evaluate_resume_eligibility(approval, receipt, authority, action="publish", target=approval["target"], at="2026-08-20T08:11:00+00:00")
    return {"approval_request": approval, "decision_receipt": receipt, "authority_grant": authority, "resume_eligibility": eligibility}


def _main() -> None:
    import argparse, json
    parser = argparse.ArgumentParser(description="CTCL-ITR governance reference utilities")
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if args.command == "demo":
        print(json.dumps(demo_payload(), ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    _main()
