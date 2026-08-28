import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"


def load_json(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def load_schema(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_governance_reference_objects_validate_and_link():
    approval = load_json("governance_approval_request.json")
    decision = load_json("governance_decision_receipt.json")
    grant = load_json("governance_authority_grant.json")
    for obj, schema_name in [
        (approval, "approval-request.schema.json"),
        (decision, "decision-receipt.schema.json"),
        (grant, "authority-grant.schema.json"),
    ]:
        schema = load_schema(schema_name)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(obj)
    assert decision["approval_id"] == approval["approval_id"]
    assert grant["decision_id"] == decision["decision_id"]
    assert grant["scope"] == ["publish"]
    assert grant["max_uses"] == 1


def test_governance_reference_atl_events_form_auditable_handoff():
    events = [
        json.loads(line)
        for line in (EXAMPLES / "governance_checkpoint.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    types = [e["event_type"] for e in events]
    assert types == [
        "human.checkpoint.requested",
        "run.suspended",
        "human.checkpoint.resolved",
        "authority.checked",
        "run.resumed",
    ]
    assert events[0]["data"]["approval_id"] == "approval:gov-001"
    assert events[2]["data"]["decision_id"] == "decision:gov-001"
    assert events[3]["data"]["authority_ref"] == "auth:gov-001"
    assert events[4]["data"]["authority_ref"] == "auth:gov-001"
